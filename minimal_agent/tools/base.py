"""Base tool class and registry."""

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return tool name for identification."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return tool description for LLM."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """Return JSON Schema for tool parameters."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Execute tool with given arguments, return result as string."""
        pass

    async def check_permission(self, **kwargs) -> dict | None:
        """Check if execution requires user permission.

        Returns None if no permission needed, or a dict with:
        - title: str - dialog title
        - message: str - detailed message
        - severity: str - "info" | "warning" | "danger"

        This method is called by the executor before execute().
        """
        return None

    def get_schema(self) -> str:
        """Get tool schema as formatted text for system prompt.

        Returns a human-readable description of the tool including
        its name, description, and parameters.
        """
        lines = [f"### {self.name}", ""]
        lines.append(self.description)
        lines.append("")

        if self.parameters:
            lines.append("Parameters:")
            for param_name, param_def in self.parameters.items():
                desc = param_def.get("description", "")
                param_type = param_def.get("type", "any")
                default = param_def.get("default", None)

                param_line = f"  - {param_name} ({param_type})"
                if default is not None:
                    param_line += f", default: {default}"
                param_line += f": {desc}"
                lines.append(param_line)

        return "\n".join(lines)

    def to_definition(self) -> dict[str, Any]:
        """Convert to Anthropic tool definition format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.parameters.keys())
            }
        }


class ToolRegistry:
    """Registry for tools."""

    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool by its name."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Get tool by name, return None if not found."""
        return self._tools.get(name)

    def get_definitions(self) -> list[dict]:
        """Get all tool definitions for LLM API."""
        return [tool.to_definition() for tool in self._tools.values()]

    def get_tools_schema(self) -> str:
        """Get formatted schema for all tools for system prompt.

        Returns a human-readable description of all registered tools.
        """
        if not self._tools:
            return "No tools available."

        sections = []
        for tool in self._tools.values():
            sections.append(tool.get_schema())

        return "\n\n".join(sections)

    async def execute(self, tool_calls: list[dict]) -> list[dict]:
        """Execute tool calls sequentially (unused, kept for compatibility)."""
        results = []
        for call in tool_calls:
            tool = self.get(call["name"])
            if not tool:
                results.append({
                    "tool_call_id": call["id"],
                    "content": f"Error: Tool '{call['name']}' not found"
                })
                continue

            try:
                result = await tool.execute(**call["arguments"])
                results.append({
                    "tool_call_id": call["id"],
                    "content": result
                })
            except Exception as e:
                results.append({
                    "tool_call_id": call["id"],
                    "content": f"Error: {str(e)}"
                })

        return results
