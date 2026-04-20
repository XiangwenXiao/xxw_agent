"""Ask user question tool for agent to ask user when confused."""

from ..base import Tool


class AskUserQuestionTool(Tool):
    """Tool for asking user a question when agent needs clarification."""

    @property
    def name(self) -> str:
        """Return tool identifier."""
        return "ask_user"

    @property
    def description(self) -> str:
        """Return tool description for LLM."""
        return "Ask the user a question when you're confused, need clarification, or stuck. Use this when you need more information to proceed or when multiple approaches are possible."

    @property
    def parameters(self) -> dict:
        """Return JSON Schema for question parameters."""
        return {
            "question": {
                "type": "string",
                "description": "The question to ask the user. Be specific about what you need to know."
            },
            "context": {
                "type": "string",
                "description": "Optional context explaining why you're asking and what you've tried",
                "default": ""
            },
            "options": {
                "type": "array",
                "description": "Optional list of predefined options for the user to choose from",
                "items": {"type": "string"},
                "default": []
            }
        }

    async def execute(self, **kwargs) -> str:
        """Execute - actual interaction is handled by executor/REPL layer.

        This method is only called after user has provided an answer.
        The answer is passed via kwargs by the executor.
        """
        answer = kwargs.get("answer", "")
        if answer:
            return f"User answered: {answer}"
        return "No answer provided"
