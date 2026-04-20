"""Logging utilities for conversation history."""

import os
from datetime import datetime
from pathlib import Path


class ConversationLogger:
    """Logger for full conversation history including tool calls.

    Logs are written to logs/ folder with timestamp-based filenames.
    Each session gets its own log file.
    """

    LOG_DIR = "logs"

    def __init__(self):
        """Initialize logger with session-specific log file."""
        self.session_start = datetime.now()
        self.log_file = self._create_log_file()
        self._ensure_file()

    def _create_log_file(self) -> str:
        """Create log filename with timestamp."""
        # Ensure logs directory exists
        log_dir = Path(self.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Filename: session_YYYYMMDD_HHMMSS.log
        timestamp = self.session_start.strftime("%Y%m%d_%H%M%S")
        return str(log_dir / f"session_{timestamp}.log")

    def _ensure_file(self):
        """Ensure log file exists with header."""
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                pass
        except FileNotFoundError:
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write(f"# Conversation History\n")
                f.write(f"# Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Format: [TIMESTAMP] ROLE: CONTENT\n")
                f.write("=" * 80 + "\n\n")

    def _write_entry(self, role: str, content: str, indent: int = 0):
        """Write an entry to log file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = "  " * indent
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {prefix}{role}: {content}\n")

    def log_user(self, content: str):
        """Log user message."""
        self._write_entry("User", content)

    def log_assistant_text(self, text: str):
        """Log assistant text response."""
        if text.strip():
            self._write_entry("Assistant", text)

    def log_tool_call(self, tool_name: str, tool_id: str, arguments: dict, waiting_for: list = None):
        """Log tool call with arguments."""
        args_str = str(arguments) if arguments else "()"
        if waiting_for:
            self._write_entry("ToolCall", f"[{tool_name}] id={tool_id} args={args_str} (WAITING for: {waiting_for})", indent=1)
        else:
            self._write_entry("ToolCall", f"[{tool_name}] id={tool_id} args={args_str}", indent=1)

    def log_tool_promoted(self, tool_name: str, tool_id: str):
        """Log tool promoted from waiting to running."""
        self._write_entry("ToolPromoted", f"[{tool_name}] id={tool_id} promoted to RUNNING", indent=1)

    def log_tool_result(self, tool_name: str, tool_id: str, result: str):
        """Log tool execution result."""
        # Truncate long results
        if len(result) > 500:
            result = result[:500] + f"... [truncated, total {len(result)} chars]"
        self._write_entry("ToolResult", f"[{tool_name}] id={tool_id} result={result}", indent=1)

    def log_separator(self):
        """Log a separator line."""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write("\n" + "-" * 80 + "\n\n")

    def get_log_file_path(self) -> str:
        """Get current session log file path."""
        return self.log_file
