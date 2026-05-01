import asyncio
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from orchestrator import Orchestrator

app = FastAPI(title="Multi-Agent Orchestration API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],   # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()


# ─── Request / Response Models ────────────────────────────────────────────────

class CreateTaskRequest(BaseModel):
    request: str

    class Config:
        json_schema_extra = {
            "example": {
                "request": "Research the pros and cons of microservices vs monoliths and produce a summary report."
            }
        }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tasks", status_code=201)
async def create_task(body: CreateTaskRequest, background_tasks: BackgroundTasks):
    """
    Submit a new task. Returns the task ID immediately.
    Pipeline runs asynchronously in the background.
    Frontend should then connect to /tasks/{id}/stream for real-time updates.
    """
    if not body.request.strip():
        raise HTTPException(status_code=400, detail="Request cannot be empty.")

    task = orchestrator.create_task(body.request.strip())

    # Run pipeline in background — don't block the HTTP response
    background_tasks.add_task(orchestrator.run_pipeline, task.id)

    return {"task_id": task.id, "status": task.status.value}


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    """
    Poll for current task state and results.
    Also useful as a fallback if SSE connection drops.
    """
    task = orchestrator.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task.to_dict()


@app.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    """
    SSE endpoint — pushes real-time task updates to the frontend.

    Why SSE over WebSockets:
    - We only need server → client communication (unidirectional)
    - SSE is simpler: built on HTTP, auto-reconnects, no upgrade handshake
    - WebSockets would be overkill here — no client→server streaming needed
    """
    task = orchestrator.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    async def event_generator():
        async for state in orchestrator.subscribe(task_id):
            # SSE format: data: <json>\n\n
            yield f"data: {json.dumps(state)}\n\n"
            if state.get("status") in ("done", "failed"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",       # disable nginx buffering
        },
    )


@app.get("/tasks")
def list_tasks():
    """List all tasks — useful for debugging and the stretch goal of task history."""
    return [task.to_dict() for task in orchestrator.tasks.values()]
