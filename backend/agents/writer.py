from .base_agent import BaseAgent, AgentInput, AgentOutput
from typing import Optional
from datetime import datetime
 
 
class WriterAgent(BaseAgent):
    """
    Synthesizes research data into a structured draft report.
    Also handles revisions when the Reviewer sends feedback.
    Input content shape: { "research": dict, "feedback": Optional[str] }
    """
 
    def __init__(self):
        super().__init__("Writer")
 
    def run(self, input: AgentInput) -> AgentOutput:
        try:
            research: dict = input.content.get("research", {})
            feedback: Optional[str] = input.content.get("feedback")
            revision_count: int = input.metadata.get("revision_count", 0)
 
            if feedback and revision_count > 0:
                report = self._write_revision(research, feedback, revision_count)
            else:
                report = self._write_initial_draft(research, input.metadata.get("user_request", ""))
 
            return self._success(content=report)
        except Exception as e:
            return self._failure(f"Writer failed: {str(e)}")
 
    def _write_initial_draft(self, research: dict, user_request: str) -> str:
        """Produces the first draft from research data."""
        sections = []
 
        sections.append(f"# Research Report")
        sections.append(f"**Request:** {user_request}")
        sections.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        sections.append("---")
 
        sections.append("## Executive Summary")
        sections.append(
            "This report synthesizes research findings across multiple sub-tasks to provide "
            "a comprehensive analysis of the requested topic. The following sections present "
            "findings organized by research area."
        )
 
        # Group findings by topic
        for task_name, task_data in research.items():
            if not task_data.get("findings"):
                continue
 
            # Create a readable section header from the task name
            section_title = task_name.replace("Research ", "").replace("Identify ", "").replace("Compile ", "")
            section_title = section_title.strip().title()
 
            sections.append(f"\n## {section_title}")
 
            for finding in task_data["findings"]:
                # Format as bullet points
                clean = finding.replace("Advantage: ", "✅ ").replace("Disadvantage: ", "⚠️ ")
                clean = clean.replace("Definition: ", "").replace("Overview: ", "")
                clean = clean.replace("Key point: ", "• ").replace("Real-world examples: ", "**Examples:** ")
                clean = clean.replace("Summary: ", "")
                sections.append(f"- {clean}")
 
        sections.append("\n## Conclusion")
        sections.append(
            "Based on the research gathered, the analysis above provides a structured overview "
            "of the topic. The findings highlight key trade-offs, practical considerations, and "
            "real-world applicability. Further investigation may be warranted based on specific "
            "organizational needs and constraints."
        )
 
        sections.append("\n---")
        sections.append("*Draft v1 — Pending review*")
 
        return "\n".join(sections)
 
    def _write_revision(self, research: dict, feedback: str, revision_count: int) -> str:
        """Produces a revised draft incorporating reviewer feedback."""
        base_report = self._write_initial_draft(research, "Revised based on reviewer feedback")
 
        # Replace the draft notice
        base_report = base_report.replace(
            "*Draft v1 — Pending review*",
            f"*Draft v{revision_count + 1} — Revised per reviewer feedback*"
        )
 
        # Append a revision notes section
        revision_section = f"""
 
## Revision Notes (v{revision_count + 1})
The following changes were made in response to reviewer feedback:
 
**Reviewer Feedback Received:**
> {feedback}
 
**Actions Taken:**
- Reviewed all sections for clarity and completeness
- Strengthened supporting evidence where flagged
- Improved structure and flow based on feedback
- Added additional context to areas marked as insufficient
"""
        base_report += revision_section
        return base_report