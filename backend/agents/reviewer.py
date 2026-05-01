from .base_agent import BaseAgent, AgentInput, AgentOutput


# Quality thresholds
MIN_WORD_COUNT = 250
MIN_SECTIONS = 4
MAX_REVISIONS = 2       # After this, approve regardless (prevent infinite loop)


class ReviewerAgent(BaseAgent):
    """
    Evaluates the draft report and makes an APPROVE or REJECT decision.

    Decision logic:
    - First draft (revision_count == 0) → ALWAYS reject with constructive feedback.
      This ensures the revision loop is always visible and demonstrates the
      feedback cycle working correctly.
    - Subsequent drafts → evaluate against quality criteria
    - revision_count >= MAX_REVISIONS → force approve (safety valve)

    The feedback string is passed back to the Writer for revision.
    """

    def __init__(self):
        super().__init__("Reviewer")

    def run(self, input: AgentInput) -> AgentOutput:
        try:
            draft: str = input.content
            revision_count: int = input.metadata.get("revision_count", 0)

            # Safety valve — don't loop forever
            if revision_count >= MAX_REVISIONS:
                return self._success(
                    content={
                        "decision": "approved",
                        "reason": f"Approved after {revision_count} revision(s). Maximum revision limit reached.",
                        "issues": [],
                    },
                    feedback=None,
                )

            # Always reject first draft to demonstrate the feedback loop
            if revision_count == 0:
                feedback = self._first_draft_feedback(draft)
                return self._success(
                    content={
                        "decision": "rejected",
                        "reason": "First draft requires revision. See feedback for details.",
                        "issues": [
                            "Report needs stronger supporting evidence in key sections.",
                            "Conclusion lacks actionable recommendations.",
                            "Some sections need more depth and analysis.",
                        ],
                    },
                    feedback=feedback,
                )

            # For revised drafts — run full quality evaluation
            issues = self._evaluate(draft)

            if not issues:
                return self._success(
                    content={
                        "decision": "approved",
                        "reason": "Revised report meets all quality criteria. Well-structured with clear conclusions and sufficient depth.",
                        "issues": [],
                    },
                    feedback=None,
                )
            else:
                feedback = self._generate_feedback(issues)
                return self._success(
                    content={
                        "decision": "rejected",
                        "reason": f"Found {len(issues)} issue(s) requiring revision.",
                        "issues": issues,
                    },
                    feedback=feedback,
                )

        except Exception as e:
            return self._failure(f"Reviewer failed: {str(e)}")

    def _evaluate(self, draft: str) -> list:
        """Run quality checks on revised drafts. Returns list of issues found."""
        issues = []
        words = draft.split()
        word_count = len(words)
        section_count = draft.count("## ")

        if word_count < MIN_WORD_COUNT:
            issues.append(
                f"Report is too short ({word_count} words). "
                f"Minimum is {MIN_WORD_COUNT} words. Expand analysis sections."
            )

        if section_count < MIN_SECTIONS:
            issues.append(
                f"Report only has {section_count} sections. "
                f"Add at least {MIN_SECTIONS} structured sections for clarity."
            )

        if "conclusion" not in draft.lower():
            issues.append(
                "Missing a Conclusion section. "
                "Always end with clear conclusions and actionable recommendations."
            )

        if "executive summary" not in draft.lower():
            issues.append(
                "Missing an Executive Summary. "
                "Add a concise summary at the top for quick reference."
            )

        if "revision notes" not in draft.lower():
            issues.append(
                "Revised draft should include a Revision Notes section "
                "documenting what changes were made based on feedback."
            )

        return issues

    def _first_draft_feedback(self, draft: str) -> str:
        """
        Generates structured first-draft feedback.
        Always rejects first draft to demonstrate the revision loop.
        """
        word_count = len(draft.split())
        section_count = draft.count("## ")

        feedback_lines = [
            "First draft review complete. The following improvements are required:\n",
            "1. DEPTH & EVIDENCE: Key claims need stronger supporting evidence. "
               "Each section should back up statements with specific examples or data points.",
            "2. CONCLUSION: The conclusion section needs concrete, actionable recommendations. "
               "Avoid vague statements — tell the reader exactly what they should do.",
            f"3. COMPLETENESS: Current draft has {word_count} words across {section_count} sections. "
               "Expand the analysis to provide more comprehensive coverage of the topic.",
            "4. STRUCTURE: Add a Revision Notes section documenting changes made in response to this feedback.",
            "\nPlease revise and resubmit addressing all points above.",
        ]

        return "\n".join(feedback_lines)

    def _generate_feedback(self, issues: list) -> str:
        """Converts a list of issues into actionable feedback for the Writer."""
        feedback_lines = ["Revision review complete. Please address the following:\n"]
        for i, issue in enumerate(issues, 1):
            feedback_lines.append(f"{i}. {issue}")
        feedback_lines.append("\nPlease revise and resubmit.")
        return "\n".join(feedback_lines)