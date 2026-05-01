from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, List
from datetime import datetime
import uuid


class TaskStatus(str, Enum):
    PENDING     = "pending"
    PLANNING    = "planning"
    RESEARCHING = "researching"
    WRITING     = "writing"
    REVIEWING   = "reviewing"
    REVISION    = "revision"      # Writer is revising based on Reviewer feedback
    DONE        = "done"
    FAILED      = "failed"


@dataclass
class AgentStep:
    """Records what each agent did — forms the audit trail shown in the UI."""
    agent: str
    status: str                         # "running" | "done" | "failed"
    input_summary: str
    output_summary: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_request: str = ""
    status: TaskStatus = TaskStatus.PENDING
    steps: List[AgentStep] = field(default_factory=list)

    # Intermediate outputs passed between agents
    sub_tasks: List[str] = field(default_factory=list)
    research_data: dict = field(default_factory=dict)
    draft_report: Optional[str] = None
    reviewer_feedback: Optional[str] = None
    revision_count: int = 0

    # Final output
    final_report: Optional[str] = None
    error: Optional[str] = None

    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def add_step(self, agent: str, status: str, input_summary: str, output_summary: str):
        self.steps.append(AgentStep(
            agent=agent,
            status=status,
            input_summary=input_summary,
            output_summary=output_summary,
        ))
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_request": self.user_request,
            "status": self.status.value,
            "steps": [
                {
                    "agent": s.agent,
                    "status": s.status,
                    "input_summary": s.input_summary,
                    "output_summary": s.output_summary,
                    "timestamp": s.timestamp,
                }
                for s in self.steps
            ],
            "sub_tasks": self.sub_tasks,
            "draft_report": self.draft_report,
            "reviewer_feedback": self.reviewer_feedback,
            "revision_count": self.revision_count,
            "final_report": self.final_report,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
