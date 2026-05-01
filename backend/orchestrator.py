import asyncio
from typing import Dict, Callable, Optional
from state import Task, TaskStatus
from agents import (
    AgentInput, PlannerAgent, ResearcherAgent, WriterAgent, ReviewerAgent
)

MAX_RETRIES = 2          # max retry attempts per agent
RETRY_DELAY = 1.0        # seconds between retries


class Orchestrator:
    """
    Manages the full agent pipeline for a task.

    Pipeline:
        PENDING → PLANNING → RESEARCHING → WRITING → REVIEWING → DONE
                                                ↑           |
                                                └── REVISION ┘ (if rejected)

    RETRY LOGIC:
        If any agent fails (raises exception or returns success=False),
        the orchestrator retries up to MAX_RETRIES times with a delay.
        If all retries fail, the task is marked FAILED with a clear error message.
        This prevents a single transient failure from killing the whole pipeline.

    SSE:
        Every state transition calls self._emit(task) so the frontend
        gets real-time updates without polling.
    """

    def __init__(self):
        self.tasks: Dict[str, Task] = {}   # in-memory store — would be Redis/DB in prod
        self.planner    = PlannerAgent()
        self.researcher = ResearcherAgent()
        self.writer     = WriterAgent()
        self.reviewer   = ReviewerAgent()

        # SSE subscribers: task_id → list of async queues
        self._subscribers: Dict[str, list] = {}

    # ─── Public API ──────────────────────────────────────────────────────────

    def create_task(self, user_request: str) -> Task:
        task = Task(user_request=user_request)
        self.tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    async def run_pipeline(self, task_id: str):
        """Entry point — runs the full agent pipeline asynchronously."""
        task = self.tasks.get(task_id)
        if not task:
            return

        try:
            await self._run_planner(task)
            await self._run_researcher(task)
            await self._run_writer_reviewer_loop(task)
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.add_step(
                agent="Orchestrator",
                status="failed",
                input_summary="Pipeline execution",
                output_summary=f"Pipeline failed: {str(e)}",
            )
            await self._emit(task)

    # ─── Retry wrapper ───────────────────────────────────────────────────────

    async def _run_with_retry(self, agent_fn, task: Task, agent_name: str):
        """
        Wraps any agent call with retry logic.

        If the agent fails:
        - Waits RETRY_DELAY seconds
        - Retries up to MAX_RETRIES times
        - If all retries fail → raises exception to mark task FAILED

        Why retry matters:
        In production with real LLM calls, transient failures (rate limits,
        network timeouts) are common. Retrying automatically makes the system
        resilient without human intervention.
        """
        last_error = None

        for attempt in range(1, MAX_RETRIES + 2):   # +2 = initial attempt + retries
            try:
                output = await agent_fn()

                if not output.success:
                    raise Exception(output.error or f"{agent_name} returned failure")

                return output

            except Exception as e:
                last_error = e

                if attempt <= MAX_RETRIES:
                    # Log the retry attempt in task steps
                    task.add_step(
                        agent=agent_name,
                        status="failed",
                        input_summary=f"Attempt {attempt}",
                        output_summary=f"Failed: {str(e)}. Retrying ({attempt}/{MAX_RETRIES})...",
                    )
                    await self._emit(task)
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    # All retries exhausted
                    raise Exception(
                        f"{agent_name} failed after {MAX_RETRIES} retries. "
                        f"Last error: {str(last_error)}"
                    )

    # ─── SSE subscription ────────────────────────────────────────────────────

    async def subscribe(self, task_id: str):
        """Yields SSE events for a task. Used by the /stream endpoint."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(task_id, []).append(queue)
        try:
            # Send current state immediately on connect
            task = self.tasks.get(task_id)
            if task:
                await queue.put(task.to_dict())
            while True:
                data = await queue.get()
                yield data
                if data.get("status") in (TaskStatus.DONE, TaskStatus.FAILED):
                    break
        finally:
            self._subscribers[task_id].remove(queue)

    async def _emit(self, task: Task):
        """Push task state to all SSE subscribers."""
        for queue in self._subscribers.get(task.id, []):
            await queue.put(task.to_dict())
        await asyncio.sleep(0)     # yield control so queues are processed

    # ─── Agent runners ───────────────────────────────────────────────────────

    async def _run_planner(self, task: Task):
        task.status = TaskStatus.PLANNING
        await self._emit(task)
        await asyncio.sleep(1)

        output = await self._run_with_retry(
            lambda: asyncio.to_thread(
                self.planner.run,
                AgentInput(task_id=task.id, content=task.user_request)
            ),
            task,
            "Planner"
        )

        task.sub_tasks = output.content
        task.add_step(
            agent="Planner",
            status="done",
            input_summary=f"User request: {task.user_request[:80]}",
            output_summary=f"Generated {len(task.sub_tasks)} sub-tasks",
        )
        await self._emit(task)

    async def _run_researcher(self, task: Task):
        task.status = TaskStatus.RESEARCHING
        await self._emit(task)
        await asyncio.sleep(1.5)

        output = await self._run_with_retry(
            lambda: asyncio.to_thread(
                self.researcher.run,
                AgentInput(task_id=task.id, content=task.sub_tasks)
            ),
            task,
            "Researcher"
        )

        task.research_data = output.content
        task.add_step(
            agent="Researcher",
            status="done",
            input_summary=f"Researching {len(task.sub_tasks)} sub-tasks (parallel)",
            output_summary=f"Gathered findings for all sub-tasks",
        )
        await self._emit(task)

    async def _run_writer_reviewer_loop(self, task: Task):
        """
        The core feedback loop:
        Writer produces draft → Reviewer evaluates → if rejected, Writer revises.
        Loops until approved or MAX_REVISIONS reached.
        Both Writer and Reviewer have retry logic via _run_with_retry.
        """
        feedback = None

        while True:
            # ── Writer ──────────────────────────────────────────────────────
            task.status = TaskStatus.WRITING if task.revision_count == 0 else TaskStatus.REVISION
            await self._emit(task)
            await asyncio.sleep(1.5)

            writer_output = await self._run_with_retry(
                lambda: asyncio.to_thread(
                    self.writer.run,
                    AgentInput(
                        task_id=task.id,
                        content={"research": task.research_data, "feedback": feedback},
                        metadata={
                            "revision_count": task.revision_count,
                            "user_request": task.user_request,
                        }
                    )
                ),
                task,
                "Writer"
            )

            task.draft_report = writer_output.content
            task.add_step(
                agent="Writer",
                status="done",
                input_summary=f"Research data + feedback: {str(feedback)[:60] if feedback else 'None'}",
                output_summary=f"Draft v{task.revision_count + 1} written ({len(task.draft_report.split())} words)",
            )
            await self._emit(task)

            # ── Reviewer ─────────────────────────────────────────────────────
            task.status = TaskStatus.REVIEWING
            await self._emit(task)
            await asyncio.sleep(1)

            reviewer_output = await self._run_with_retry(
                lambda: asyncio.to_thread(
                    self.reviewer.run,
                    AgentInput(
                        task_id=task.id,
                        content=task.draft_report,
                        metadata={"revision_count": task.revision_count}
                    )
                ),
                task,
                "Reviewer"
            )

            decision = reviewer_output.content.get("decision")
            reviewer_feedback = reviewer_output.feedback

            task.add_step(
                agent="Reviewer",
                status="done",
                input_summary=f"Reviewing draft v{task.revision_count + 1}",
                output_summary=f"Decision: {decision.upper()} — {reviewer_output.content.get('reason', '')}",
            )

            if decision == "approved":
                task.final_report = task.draft_report
                task.reviewer_feedback = None
                task.status = TaskStatus.DONE
                await self._emit(task)
                return
            else:
                feedback = reviewer_feedback
                task.reviewer_feedback = reviewer_feedback
                task.revision_count += 1
                await self._emit(task)