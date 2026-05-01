from .base_agent import BaseAgent, AgentInput, AgentOutput
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed


# Simulated knowledge base — in production this would call a real search API or LLM
KNOWLEDGE_BASE = {
    "microservices": {
        "definition": "Microservices is an architectural style that structures an application as a collection of small, independently deployable services, each running in its own process and communicating via APIs.",
        "advantages": [
            "Independent deployment — update one service without touching others",
            "Technology flexibility — each service can use a different tech stack",
            "Fault isolation — one service failing doesn't bring down the whole system",
            "Scales horizontally — scale only the services that need it",
            "Easier for large teams — teams can own individual services",
        ],
        "disadvantages": [
            "Operational complexity — managing many services requires DevOps maturity",
            "Network latency — service-to-service calls add overhead",
            "Data consistency — distributed transactions are hard",
            "Testing complexity — integration testing across services is difficult",
            "Higher initial setup cost",
        ],
        "use_cases": ["Netflix", "Amazon", "Uber", "Spotify"],
    },
    "monolith": {
        "definition": "A monolithic architecture is a traditional unified model where all components of an application are interconnected and deployed as a single unit.",
        "advantages": [
            "Simple development — everything in one codebase",
            "Easy to test end-to-end",
            "No network latency between components",
            "Simpler deployment — one artifact to ship",
            "Easier debugging and tracing",
        ],
        "disadvantages": [
            "Scales as a whole — can't scale individual parts",
            "Technology lock-in — entire app uses one stack",
            "Deployment risk — any change requires full redeployment",
            "Codebase grows unwieldy over time",
            "Teams step on each other in large orgs",
        ],
        "use_cases": ["Early-stage startups", "Small teams", "Simple CRUD applications"],
    },
    "default": {
        "definition": "This topic involves multiple interconnected concepts that require careful analysis.",
        "advantages": ["Structured approach", "Clear boundaries", "Proven patterns"],
        "disadvantages": ["Complexity", "Learning curve", "Implementation overhead"],
        "use_cases": ["Enterprise systems", "Modern applications", "Scalable platforms"],
    }
}


class ResearcherAgent(BaseAgent):
    """
    Gathers information for each sub-task.
    Uses a simulated knowledge base — explicitly allowed by the assignment brief.
    In production: would call a search API, RAG pipeline, or LLM with tools.

    PARALLEL EXECUTION:
    Each sub-task is independent — no sub-task depends on another's result.
    We use ThreadPoolExecutor to run all sub-tasks concurrently instead of
    sequentially. This means 6 sub-tasks run in parallel rather than one by one.

    Why ThreadPoolExecutor and not asyncio.gather()?
    - _research_task() is a pure CPU/IO-bound function, not a coroutine
    - asyncio.to_thread() would also work but ThreadPoolExecutor is more
      explicit about the parallelism model
    - In production with real HTTP calls, asyncio.gather() would be preferred
    """

    def __init__(self):
        super().__init__("Researcher")
        self.max_workers = 4        # max concurrent sub-task threads

    def run(self, input: AgentInput) -> AgentOutput:
        try:
            sub_tasks: List[str] = input.content
            research_results = {}

            # Run all sub-tasks concurrently using thread pool
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all sub-tasks at once
                future_to_task = {
                    executor.submit(self._research_task, task): task
                    for task in sub_tasks
                }
                # Collect results as they complete
                for future in as_completed(future_to_task):
                    task_name = future_to_task[future]
                    try:
                        research_results[task_name] = future.result()
                    except Exception as e:
                        # Individual sub-task failure — log and continue
                        # Other sub-tasks are unaffected (fault isolation)
                        research_results[task_name] = {
                            "source_task": task_name,
                            "findings": [f"Research failed for this sub-task: {str(e)}"],
                            "error": True,
                        }

            return self._success(content=research_results)
        except Exception as e:
            return self._failure(f"Researcher failed: {str(e)}")

    def _research_task(self, task: str) -> dict:
        """
        Look up relevant info from knowledge base based on keywords in the task.
        This method is called concurrently for each sub-task.
        It is stateless — safe to run in parallel with no shared mutable state.
        """
        task_lower = task.lower()

        # Match against knowledge base keys
        matched_key = "default"
        for key in KNOWLEDGE_BASE:
            if key in task_lower:
                matched_key = key
                break

        data = KNOWLEDGE_BASE[matched_key]

        # Return relevant subset based on what the task is asking
        result = {"source_task": task, "findings": []}

        if any(w in task_lower for w in ["definition", "background", "what is", "how"]):
            result["findings"].append(f"Definition: {data['definition']}")

        if any(w in task_lower for w in ["advantage", "benefit", "pro", "strength"]):
            result["findings"].extend([f"Advantage: {a}" for a in data["advantages"][:3]])

        if any(w in task_lower for w in ["disadvantage", "drawback", "con", "challenge", "weakness"]):
            result["findings"].extend([f"Disadvantage: {d}" for d in data["disadvantages"][:3]])

        if any(w in task_lower for w in ["use case", "example", "real-world", "adoption"]):
            result["findings"].append(f"Real-world examples: {', '.join(data['use_cases'])}")

        if any(w in task_lower for w in ["comparison", "summary", "compile", "compare"]):
            result["findings"].append(f"Summary: {data['definition']}")
            result["findings"].extend([f"Key point: {a}" for a in data["advantages"][:2]])

        # Fallback — return definition if nothing matched
        if not result["findings"]:
            result["findings"].append(f"Overview: {data['definition']}")

        return result