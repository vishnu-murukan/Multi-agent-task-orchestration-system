# Design Document — Multi-Agent Task Orchestration System

## Overview

This document describes the architectural decisions, trade-offs, and assumptions made while building the Multi-Agent Task Orchestration System. The system enables multiple AI agents to collaborate asynchronously to produce structured research reports, with a real-time UI that reflects pipeline progress.

---

## Architecture

### High-Level Design

```
User → Next.js Frontend → FastAPI Backend → Orchestrator → Agents
                       ←    SSE Stream   ←
```

The system follows a **pipeline architecture** with a feedback loop. Four agents operate in sequence: Planner → Researcher → Writer → Reviewer. The Reviewer can reject the draft and send it back to the Writer, creating a controlled revision loop.

### Backend

**Framework: FastAPI**

FastAPI was chosen over Flask or Django for three reasons:
1. **Async-native** — `asyncio` support is first-class, which is essential for running agent pipelines in the background while streaming SSE updates to the client.
2. **Pydantic models** — built-in request/response validation with minimal boilerplate.
3. **Auto-generated docs** — `/docs` endpoint is free, useful during development.

**Agent Abstraction**

All agents inherit from `BaseAgent`, which defines a single contract:

```python
def run(self, input: AgentInput) -> AgentOutput:
    ...
```

This keeps the Orchestrator fully decoupled from agent internals. To add a new agent (e.g., Fact Checker), you only need to:
1. Create a class inheriting `BaseAgent`
2. Register it in the Orchestrator

No other changes required. This is the Open/Closed Principle applied directly.

**State Machine**

Task state is modelled as an explicit enum:

```
PENDING → PLANNING → RESEARCHING → WRITING → REVIEWING → DONE
                                       ↑           |
                                       └── REVISION ┘
```

The `REVISION` state is the key differentiator — it distinguishes "Writer working on first draft" from "Writer revising based on Reviewer feedback", which enables the frontend to show meaningful state transitions.

**In-Memory Store**

Tasks are stored in a Python dict on the Orchestrator instance. This is intentional for this scope — no external dependencies, trivially testable, and sufficient for a single-process deployment.

**What I'd use in production:** Redis (for shared state across workers) + PostgreSQL (for persistence and task history queries).

---

## Key Trade-off: SSE vs WebSockets

**Decision: Server-Sent Events (SSE)**

| Dimension | SSE | WebSockets |
|---|---|---|
| Direction | Server → Client only | Bidirectional |
| Protocol | Plain HTTP | Upgrade handshake |
| Auto-reconnect | Built-in | Manual |
| Proxy/firewall support | Better | Can be blocked |
| Complexity | Low | Medium |

This system only needs server-to-client communication — the frontend has no need to push data to the server after task submission. SSE is strictly simpler and better suited to this use case. WebSockets would be the right call if we added collaborative features (multiple users watching the same pipeline, or users being able to intervene mid-pipeline).

---

## Key Trade-off: Polling vs SSE

**Decision: SSE over polling**

Polling (GET /tasks/:id every 2 seconds) is simple but wasteful — it hammers the server even when nothing has changed. SSE gives us push-based updates with minimal overhead and is supported natively by all modern browsers. The `EventSource` API handles reconnection automatically.

---

## Key Trade-off: Sync vs Async Agents

**Decision: Async orchestrator, sync agents**

The Orchestrator itself is async — it uses `asyncio` and `BackgroundTasks` to run the pipeline without blocking the HTTP response. Individual agents are synchronous (`run()` returns directly), which keeps them simple and easy to test in isolation.

This is an intentional boundary: agents don't need to know they're running in an async context. If an agent needed to make real HTTP calls (e.g., to a search API), we'd either use `asyncio.to_thread()` to run it without blocking, or refactor `run()` to be async.

---

## Reviewer Feedback Loop

The loop has a hard cap (`MAX_REVISIONS = 2`) to prevent infinite cycling. After the maximum is reached, the Reviewer auto-approves. This is a deliberate safety valve — in production, you'd want this to escalate to a human reviewer instead.

The loop logic lives entirely in the Orchestrator (`_run_writer_reviewer_loop`), not in any individual agent. This keeps agents stateless and the control flow readable in one place.

---

## Assumptions Made

1. **Simulated agents are acceptable** — The brief explicitly states "hardcoded or templated responses" are fine. Agents use a structured knowledge base rather than real LLM calls.
2. **Single-process deployment** — No distributed task queue (Celery, etc.) is needed at this scope.
3. **No authentication** — Out of scope for this assignment.
4. **No persistent storage** — Tasks are in-memory. A page refresh loses task history (noted as a stretch goal).
5. **CORS allows localhost:3000** — Assumes standard Next.js dev server port.

---

## Agent Simulation vs Real LLM

All four agents use simulated responses — a structured knowledge base and string templating — rather than real LLM calls. This is explicitly permitted by the assignment brief.

The `BaseAgent` interface was intentionally designed so real LLM calls can be plugged in without touching the orchestrator or API layer. To integrate Gemini or Claude:

```python
# Current (simulated):
class ReviewerAgent(BaseAgent):
    def run(self, input: AgentInput) -> AgentOutput:
        issues = self._evaluate(input.content)   # string checks
        ...

# With real LLM (same interface, different internals):
class ReviewerAgent(BaseAgent):
    def run(self, input: AgentInput) -> AgentOutput:
        response = gemini.generate(f"Review this report: {input.content}")
        decision = parse_json(response)
        ...
```

Zero changes to the orchestrator, state machine, or API endpoints.

## Parallel Researcher

Sub-tasks produced by the Planner are independent of each other — no sub-task needs another's result. The Researcher runs them concurrently using `ThreadPoolExecutor`:

```python
with ThreadPoolExecutor(max_workers=4) as executor:
    future_to_task = {executor.submit(self._research_task, t): t for t in sub_tasks}
    for future in as_completed(future_to_task):
        results[future_to_task[future]] = future.result()
```

`ThreadPoolExecutor` was chosen over `asyncio.gather()` because `_research_task` is a synchronous function (dictionary lookup). With real HTTP-based research calls, `asyncio.gather()` would be the better choice.

Individual sub-task failures are isolated — one failing sub-task does not stop others.

## Retry / Error Handling

The orchestrator wraps every agent call in `_run_with_retry()`:

```
Attempt 1 → fails → wait 1s → Attempt 2 → fails → wait 1s → Attempt 3 → FAILED
```

After `MAX_RETRIES` (2) exhausted, the task is marked `FAILED` with a clear error message. The UI shows which step failed in the chain view.

In production this would use exponential backoff and escalate to a human reviewer rather than silently failing.

## Testing

Unit tests cover all four agents, the state model, and orchestrator logic including:
- Agent input/output contracts
- The reviewer rejection loop
- Retry logic via monkey-patching
- Full pipeline end-to-end

Run with: `pytest tests.py -v`

## What I Would Add With More Time

### High Priority
- **Real LLM integration** — Replace stubbed agents with Claude/Gemini calls. `BaseAgent.run()` interface stays identical — swap internals only.
- **Persistent storage** — PostgreSQL + SQLAlchemy so task history survives restarts.
- **Exponential backoff** — Replace fixed retry delay with exponential backoff + jitter.

### Medium Priority
- **Fact Checker agent** — Sits between Writer and Reviewer. Validates factual claims before quality review. Already mentioned in assignment brief as a stretch goal.
- **Agent configuration UI** — Let users skip the review step or add custom agents via toggle.
- **Streaming agent output** — Stream LLM output token by token instead of waiting for full response.

### Lower Priority
- **Task history UI** — Sidebar listing past tasks using persisted storage.
- **Distributed execution** — Replace in-memory dict with Redis + Celery for multi-worker deployments.

---

## File Structure

```
backend/
├── main.py           # FastAPI app, endpoints, SSE
├── orchestrator.py   # Pipeline logic, state management, SSE emission
├── state.py          # Task model, TaskStatus enum, AgentStep
├── tests.py          # Unit tests — agents, orchestrator, state model
├── requirements.txt
└── agents/
    ├── __init__.py   # Agent exports
    ├── base_agent.py # Abstract base — AgentInput/Output contract
    ├── planner.py    # Breaks request into sub-tasks
    ├── researcher.py # Parallel knowledge lookup per sub-task
    ├── writer.py     # Synthesizes research into draft + handles revisions
    └── reviewer.py   # Quality evaluation + approve/reject decision

frontend/
├── app/
│   ├── globals.css   # Global styles — moved here to fix SSR hydration
│   ├── layout.tsx    # Root layout — imports globals.css
│   └── page.tsx      # Main page — form, pipeline visualizer, results
├── hooks/
│   └── useSSE.ts     # EventSource hook + API calls
├── types/
│   └── index.ts      # TypeScript types shared across components
├── next.config.js
├── tsconfig.json
└── package.json
```