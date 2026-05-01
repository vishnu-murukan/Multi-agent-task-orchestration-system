from .base_agent import BaseAgent, AgentInput, AgentOutput
import re
 
 
class PlannerAgent(BaseAgent):
    """
    Breaks the user's raw request into discrete sub-tasks.
    In production this would call an LLM. Here we use smart pattern matching
    + sensible defaults so the system still feels dynamic.
    """
 
    def __init__(self):
        super().__init__("Planner")
 
    def run(self, input: AgentInput) -> AgentOutput:
        try:
            request = str(input.content).lower()
            sub_tasks = self._generate_sub_tasks(request)
            return self._success(
                content=sub_tasks,
            )
        except Exception as e:
            return self._failure(f"Planner failed: {str(e)}")
 
    def _generate_sub_tasks(self, request: str) -> list:
        """
        Generates contextual sub-tasks based on the user request.
        Detects comparison requests, research topics, and report types.
        """
 
        # Detect if it's a comparison request (vs, compare, difference)
        is_comparison = any(w in request for w in ["vs", "versus", "compare", "difference", "contrast"])
 
        # Detect if it's asking for pros/cons
        is_pros_cons = any(w in request for w in ["pros", "cons", "advantages", "disadvantages", "benefits", "drawbacks"])
 
        # Extract key topics (simple noun extraction)
        topics = self._extract_topics(request)
 
        sub_tasks = []
 
        if is_comparison and len(topics) >= 2:
            sub_tasks = [
                f"Research background and definition of {topics[0]}",
                f"Research background and definition of {topics[1]}",
                f"Identify advantages of {topics[0]} over {topics[1]}",
                f"Identify advantages of {topics[1]} over {topics[0]}",
                f"Research real-world use cases for both {topics[0]} and {topics[1]}",
                f"Compile comparison summary and recommendations",
            ]
        elif is_pros_cons and topics:
            topic = topics[0]
            sub_tasks = [
                f"Research what {topic} is and how it works",
                f"Identify key advantages of {topic}",
                f"Identify key disadvantages and challenges of {topic}",
                f"Research real-world adoption and case studies of {topic}",
                f"Compile findings into a structured pros/cons report",
            ]
        else:
            # Generic research task
            sub_tasks = [
                f"Research background and context of the topic",
                f"Gather key facts, data, and expert opinions",
                f"Identify major themes and patterns",
                f"Research real-world examples and case studies",
                f"Compile all findings into a coherent report",
            ]
 
        return sub_tasks
 
    def _extract_topics(self, request: str) -> list:
        """Extracts the main subject topics from the request string."""
        # Remove common filler words
        stop_words = {
            "the", "a", "an", "and", "or", "of", "in", "on", "for",
            "to", "is", "are", "was", "were", "be", "been", "being",
            "research", "compare", "comparison", "pros", "cons", "report",
            "summary", "write", "produce", "generate", "create", "make",
            "advantages", "disadvantages", "between", "difference", "differences",
            "me", "my", "i", "we", "our", "us", "you", "your",
        }
 
        # Split on common separators including "vs"
        parts = re.split(r'\bvs\.?\b|\bversus\b|\band\b|,', request)
        topics = []
        for part in parts:
            words = [w.strip() for w in part.split() if w.strip().lower() not in stop_words and len(w.strip()) > 2]
            if words:
                topics.append(" ".join(words[:3]))  # max 3 words per topic
 
        return [t for t in topics if t][:3]  # return max 3 topics