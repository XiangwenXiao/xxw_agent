"""Read tool for reading files."""

from pathlib import Path
from ..base import Tool


class ReadTool(Tool):
    """Tool for reading file contents with optional line limit."""

    @property
    def name(self) -> str:
        """Return tool identifier."""
        return "read"

    @property
    def description(self) -> str:
        """Return tool description for LLM."""
        return "Read the contents of a file."

    @property
    def parameters(self) -> dict:
        """Return JSON Schema for file path and line limit."""
        return {
            "file_path": {
                "type": "string",
                "description": "The absolute path to the file to read"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read (default: read all)",
                "default": None
            }
        }

    async def execute(self, **kwargs) -> str:
        """Read file and return content (with optional line limit)."""
        file_path = kwargs.get("file_path")
        limit = kwargs.get("limit")

        if not file_path:
            return "Error: No file_path provided"

        try:
            path = Path(file_path)

            if not path.exists():
                return f"Error: File not found: {file_path}"

            if not path.is_file():
                return f"Error: Path is not a file: {file_path}"

            # Read file content
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                if limit:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= limit:
                            lines.append(f"\n... ({limit} lines shown, file continues)")
                            break
                        lines.append(line.rstrip('\n'))
                    content = '\n'.join(lines)
                else:
                    content = f.read()

            return content

        except Exception as e:
            return f"Error reading file: {str(e)}"
