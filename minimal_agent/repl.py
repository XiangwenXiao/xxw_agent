"""Simple REPL interface with full conversation logging."""

import asyncio
from datetime import datetime
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from minimal_agent.events import (
    TokenEvent, ToolCallEvent, ToolWaitingEvent,
    ToolPromotedEvent, ToolResultEvent, CompleteEvent,
    ToolPermissionRequiredEvent, AskUserQuestionEvent
)
from minimal_agent.log import ConversationLogger


class REPL:
    """Simple REPL for agent interaction with full conversation logging."""

    def __init__(self, agent):
        self.agent = agent

        # Ensure logs directory exists for prompt history
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # Use prompt_toolkit history for command recall (stored in logs/)
        history_file = log_dir / ".prompt_history"
        self.session = PromptSession(history=FileHistory(str(history_file)))

        # Conversation logger for full session log
        self.logger = ConversationLogger()

    def _print_banner(self):
        """Print welcome banner."""
        banner = """
╭──────────────────────────────────────────────────────────────╮
│                                                              │
│   ██╗  ██╗██╗  ██╗██╗    ██╗   █████╗  ██████╗ ████████╗     │
│   ╚██╗██╔╝╚██╗██╔╝██║    ██║  ██╔══██╗██╔════╝ ╚══██╔══╝     │
│    ╚███╔╝  ╚███╔╝ ██║ █╗ ██║  ███████║██║  ███╗   ██║        │
│    ██╔██╗  ██╔██╗ ██║███╗██║  ██╔══██║██║   ██║   ██║        │
│   ██╔╝ ██╗██╔╝ ██╗╚███╔███╔╝  ██║  ██║╚██████╔╝   ██║        │
│   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝   ╚═╝  ╚═╝ ╚═════╝    ╚═╝        │
│                                                              │
│              Ready to help you with anything                 │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
        """
        print(banner)
        print("Type your message below (or 'exit' to quit)")
        print()

    def _format_severity(self, severity: str) -> str:
        """Format severity level with emoji."""
        return {
            "info": "ℹ️",
            "warning": "⚠️",
            "danger": "🚨"
        }.get(severity, "⚠️")

    async def _show_confirmation_dialog(self, title: str, message: str, severity: str) -> bool:
        """Show confirmation dialog and return True if user confirmed."""
        print(f"\n  {self._format_severity(severity)} [{severity.upper()}] {title}")
        print(f"  {'─' * 60}")
        for line in message.split('\n'):
            print(f"  {line}")
        print(f"  {'─' * 60}")

        # Get user choice
        while True:
            try:
                choice = await self.session.prompt_async("  Confirm? (yes/no): ")
                choice = choice.strip().lower()
                if choice in ('yes', 'y', '确认', '是'):
                    return True
                elif choice in ('no', 'n', '取消', '否'):
                    return False
                else:
                    print("  Please enter 'yes' or 'no'")
            except (KeyboardInterrupt, EOFError):
                return False

    async def _ask_user_question(self, question: str, context: str, options: list[str]) -> str:
        """Show question dialog and return user's answer."""
        print(f"\n  ❓ Agent has a question")
        print(f"  {'─' * 60}")

        if context:
            print(f"  Context: {context}")
            print()

        print(f"  Q: {question}")

        if options:
            print(f"\n  Options: {', '.join(options)}")

        print(f"  {'─' * 60}")

        # Get user answer
        try:
            answer = await self.session.prompt_async("  Your answer: ")
            return answer.strip()
        except (KeyboardInterrupt, EOFError):
            return "[cancelled]"

    async def run(self):
        """Run REPL loop - get user input, run agent, display results."""
        self._print_banner()

        while True:
            try:
                # Get user input
                user_input = await self.session.prompt_async("User: ")
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit"):
                    print("👋 Goodbye!")
                    break

                # Log user input
                self.logger.log_user(user_input)

                # Run agent with streaming and tool call logging
                print("\n🤖 ", end="")
                full_response = ""
                tool_calls_in_progress = {}  # Track tool calls by ID

                # Iterate over agent events
                async for event in self.agent.run_stream(user_input):
                    if isinstance(event, TokenEvent):
                        # Text token from LLM - print immediately
                        full_response += event.text
                        print(event.text, end="", flush=True)

                    elif isinstance(event, ToolWaitingEvent):
                        # Tool is waiting for mutex - log and display
                        self.logger.log_tool_call(
                            event.name,
                            event.tool_call_id,
                            event.input,
                            event.waiting_for
                        )
                        tool_calls_in_progress[event.tool_call_id] = event.name
                        print(f"\n  ⏳ {event.name} waiting for: {event.waiting_for}")

                    elif isinstance(event, ToolCallEvent):
                        # Tool started immediately - log it
                        self.logger.log_tool_call(event.name, event.tool_call_id, event.input)
                        tool_calls_in_progress[event.tool_call_id] = event.name

                    elif isinstance(event, ToolPromotedEvent):
                        # Tool promoted from waiting to running
                        self.logger.log_tool_promoted(event.name, event.tool_call_id)
                        print(f"\n  ▶️ {event.name} promoted to RUNNING")

                    elif isinstance(event, ToolPermissionRequiredEvent):
                        # Tool needs user permission - show dialog and resolve
                        tool_calls_in_progress[event.tool_call_id] = event.name
                        print(f"\n  ⚠️ {event.name} waiting for user confirmation")

                        approved = await self._show_confirmation_dialog(
                            event.title, event.message, event.severity
                        )

                        # Resolve permission via agent
                        self.agent.resolve_permission(event.exec_id, approved)

                    elif isinstance(event, AskUserQuestionEvent):
                        # Agent wants to ask user a question
                        tool_calls_in_progress[event.tool_call_id] = "ask_user"
                        print(f"\n  💬 Agent is asking a question")

                        answer = await self._ask_user_question(
                            event.question, event.context, event.options
                        )

                        # Resolve question via agent
                        self.agent.resolve_question(event.exec_id, answer)

                    elif isinstance(event, ToolResultEvent):
                        # Tool execution completed - log and display status
                        tool_name = tool_calls_in_progress.get(event.tool_call_id, event.name)
                        self.logger.log_tool_result(tool_name, event.tool_call_id, event.content)

                        if not event.success:
                            print(f"\n  ❌ {tool_name} failed: {event.content}")
                        else:
                            print(f"\n  ✅ {tool_name} completed")

                    elif isinstance(event, CompleteEvent):
                        # Final response complete
                        full_response = event.text

                print("\n")

                # Log assistant response
                self.logger.log_assistant_text(full_response)
                self.logger.log_separator()

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                print(f"❌ Error: {e}\n")
                self.logger._write_entry("Error", str(e))
