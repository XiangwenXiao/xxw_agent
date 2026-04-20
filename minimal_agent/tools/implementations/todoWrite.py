"""Todo task management tool for tracking progress."""

from ..base import Tool


class TodoWriteTool(Tool):
    """Tool for creating and managing a structured task list."""

    # 类级别变量存储 todo 列表
    _todo_list: list[dict] = []

    @classmethod
    def get_todo_list(cls) -> list[dict]:
        """获取当前 todo 列表。"""
        return cls._todo_list

    @classmethod
    def format_todo_reminder(cls) -> str | None:
        """格式化 todo 提醒消息，如果没有待办事项则返回 None。"""
        if not cls._todo_list:
            return None

        # 过滤掉已完成的 tasks
        active_todos = [t for t in cls._todo_list if t.get("status") != "completed"]
        if not active_todos:
            return None

        lines = ["📋 当前待办事项提醒:"]
        for todo in active_todos:
            status = todo.get("status", "pending")
            content = todo.get("content", "")
            active_form = todo.get("activeForm", "")

            if status == "in_progress":
                lines.append(f"  🔧 {active_form}")
            else:
                lines.append(f"  ⏳ {content}")

        lines.append("\n请围绕上述待办事项继续工作。")
        return "\n".join(lines)

    @property
    def name(self) -> str:
        """Return tool identifier."""
        return "todo_write"

    @property
    def description(self) -> str:
        """Return tool description for LLM."""
        return """Create and manage a structured todo list for your current task.

Use this tool proactively for:
1. Complex multi-step tasks (3+ distinct steps)
2. Non-trivial tasks requiring planning
3. When user explicitly requests a todo list
4. When user provides multiple tasks (numbered or comma-separated)
5. When starting work on a task - mark it in_progress FIRST
6. After completing a task - mark it completed immediately

Task States:
- pending: Task not yet started
- in_progress: Currently working on (limit to ONE at a time)
- completed: Task finished successfully

Task descriptions must have two forms:
- content: Imperative form (e.g., "Run tests", "Build project")
- activeForm: Present continuous (e.g., "Running tests", "Building project")

When in doubt, use this tool. Being proactive demonstrates attentiveness."""

    @property
    def parameters(self) -> dict:
        """Return JSON Schema for todo parameters."""
        return {
            "todos": {
                "type": "array",
                "description": "List of tasks to track. Can update existing todos by providing them with the same content field.",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Task description in imperative form (e.g., 'Run tests', 'Build project')"
                        },
                        "activeForm": {
                            "type": "string",
                            "description": "Task description in present continuous form (e.g., 'Running tests', 'Building project')"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                            "description": "Task state"
                        }
                    },
                    "required": ["content", "activeForm", "status"]
                }
            }
        }

    async def execute(self, **kwargs) -> str:
        """Update todo list.

        The actual tracking is done by the tool registry or agent.
        This tool simply returns success to indicate the todo was processed.
        """
        todos = kwargs.get("todos", [])

        # 更新类级别的 todo 列表
        if todos:
            TodoWriteTool._todo_list = todos

        if not todos:
            return "Todo list updated (empty)"

        lines = ["Todo list updated:"]

        for todo in todos:
            status = todo.get("status", "pending")
            content = todo.get("content", "")
            active_form = todo.get("activeForm", "")

            status_emoji = {
                "pending": "⏳",
                "in_progress": "🔧",
                "completed": "✅"
            }.get(status, "❓")

            if status == "in_progress":
                lines.append(f"  {status_emoji} {active_form}")
            else:
                lines.append(f"  {status_emoji} {content}")

        return "\n".join(lines)
