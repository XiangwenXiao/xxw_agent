"""Alert/Confirm tool for user interaction."""

from ..base import Tool


class ConfirmTool(Tool):
    """Tool for displaying alerts and getting user confirmation."""

    @property
    def name(self) -> str:
        return "confirm"

    @property
    def description(self) -> str:
        return "Display an alert/confirmation dialog to the user and wait for their choice. Use this when a potentially dangerous operation is detected (overwriting files, deleting data, executing risky commands, etc.)."

    @property
    def parameters(self) -> dict:
        return {
            "title": {
                "type": "string",
                "description": "Short title of the alert (e.g., 'File Overwrite Warning')"
            },
            "message": {
                "type": "string",
                "description": "Detailed message explaining the situation and risks"
            },
            "severity": {
                "type": "string",
                "description": "Severity level: info, warning, danger",
                "enum": ["info", "warning", "danger"],
                "default": "warning"
            },
            "options": {
                "type": "array",
                "description": "Available options for user to choose. Default: ['Continue', 'Cancel']",
                "items": {"type": "string"},
                "default": ["Continue", "Cancel"]
            },
            "default_option": {
                "type": "string",
                "description": "The default/safe option (should be one of the options). Default: 'Cancel'",
                "default": "Cancel"
            }
        }

    async def execute(self, **kwargs) -> str:
        """Display confirmation dialog and return user choice.

        Note: This is a special tool that requires REPL integration.
        The actual implementation will be handled by the REPL layer.
        """
        # This tool is special - it doesn't execute directly
        # Instead, it signals to the REPL that user input is needed
        # The REPL will handle the actual display and input
        return "__NEED_CONFIRMATION__"


class AlertResult:
    """Result of a confirmation dialog."""

    def __init__(self, confirmed: bool, choice: str, original_action: dict = None):
        self.confirmed = confirmed
        self.choice = choice
        self.original_action = original_action  # The action that triggered the alert

    def to_dict(self) -> dict:
        return {
            "confirmed": self.confirmed,
            "choice": self.choice,
            "original_action": self.original_action
        }
