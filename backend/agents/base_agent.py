from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime
 
 
@dataclass
class AgentInput:
    task_id: str
    content: Any                        # flexible — each agent defines what it expects
    metadata: dict = field(default_factory=dict)
 
 
@dataclass
class AgentOutput:
    agent_name: str
    success: bool
    content: Any                        # flexible — each agent defines what it returns
    feedback: Optional[str] = None      # used by Reviewer to send back notes
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
 
 
class BaseAgent(ABC):
    """
    Every agent in the pipeline inherits from this.
    Contract: receive AgentInput, return AgentOutput. That's it.
    This keeps the orchestrator completely decoupled from agent internals.
    """
 
    def __init__(self, name: str):
        self.name = name
 
    @abstractmethod
    def run(self, input: AgentInput) -> AgentOutput:
        """Core execution method — every agent must implement this."""
        pass
 
    def _success(self, content: Any, feedback: Optional[str] = None) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            success=True,
            content=content,
            feedback=feedback,
        )
 
    def _failure(self, error: str) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            success=False,
            content=None,
            error=error,
        )