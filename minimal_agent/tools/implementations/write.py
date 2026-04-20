"""Write tool for writing files with safety checks."""

from pathlib import Path
from ..base import Tool


class WriteTool(Tool):
    """Tool for writing files with auto-created parent directories and safety checks."""

    @property
    def name(self) -> str:
        """Return tool identifier."""
        return "write"

    @property
    def description(self) -> str:
        """Return tool description for LLM."""
        return "Write content to a file. Creates parent directories if needed. Will prompt for confirmation when overwriting existing files or writing outside the working directory."

    @property
    def parameters(self) -> dict:
        """Return JSON Schema for file path and content."""
        return {
            "file_path": {
                "type": "string",
                "description": "The absolute or relative path to the file to write"
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file"
            }
        }

    def _is_within_working_dir(self, path: Path) -> bool:
        """Check if path is within current working directory."""
        try:
            cwd = Path.cwd().resolve()
            target = path.resolve()
            target.relative_to(cwd)
            return True
        except ValueError:
            return False

    async def check_permission(self, **kwargs) -> dict | None:
        """Check if write operation requires user permission.

        Returns None if no permission needed, or a dict with permission request details.
        """
        file_path = kwargs.get("file_path")
        if not file_path:
            return None

        path = Path(file_path)
        warnings = []
        severity = "warning"

        # Check 1: File already exists
        if path.exists():
            warnings.append(f"File '{file_path}' already exists ({path.stat().st_size} bytes). Overwriting may lose data.")

        # Check 2: Path outside working directory
        if not self._is_within_working_dir(path):
            cwd = Path.cwd().resolve()
            warnings.append(f"Target path '{file_path}' is outside the working directory '{cwd}'. This could affect system files or other projects.")
            severity = "danger"

        if warnings:
            return {
                "title": "File Write Warning",
                "message": "This write operation has the following warnings:\n\n" + "\n".join(f"- {w}" for w in warnings) + "\n\nDo you want to proceed?",
                "severity": severity
            }

        return None  # No permission needed

    async def execute(self, **kwargs) -> str:
        """Write content to file, creating parent directories if needed."""
        file_path = kwargs.get("file_path")
        content = kwargs.get("content", "")

        if not file_path:
            return "Error: No file_path provided"

        try:
            path = Path(file_path)

            # Check if parent directory exists, create if needed
            parent = path.parent
            if not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            return f"File written successfully: {file_path} ({len(content)} characters)"

        except Exception as e:
            return f"Error writing file: {str(e)}"
