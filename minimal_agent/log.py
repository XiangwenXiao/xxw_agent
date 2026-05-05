"""Logging utilities for conversation history and agent diagnostics."""

import logging
from datetime import datetime
from pathlib import Path

# Module-level logger for agent diagnostics — writes to file only
_logger = logging.getLogger("minimal_agent")
_logger.setLevel(logging.DEBUG)
_log_dir = Path("logs")
_log_dir.mkdir(parents=True, exist_ok=True)
_file_handler = logging.FileHandler(str(_log_dir / "agent.log"), encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
_logger.addHandler(_file_handler)


class ConversationLogger:
    """Logger for full conversation history including tool calls."""

    LOG_DIR = "logs"

    def __init__(self):
        self.session_start = datetime.now()
        self.log_file = self._create_log_file()
        self._setup_logger()

    def _create_log_file(self) -> str:
        log_dir = Path(self.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = self.session_start.strftime("%Y%m%d_%H%M%S")
        return str(log_dir / f"session_{timestamp}.log")

    def _setup_logger(self):
        name = f"conversation.{self.session_start.strftime('%Y%m%d%H%M%S')}"
        self._conv_logger = logging.getLogger(name)
        self._conv_logger.setLevel(logging.DEBUG)
        self._conv_logger.propagate = False

        handler = logging.FileHandler(self.log_file, encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        self._conv_logger.addHandler(handler)

        # Write header
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"# Conversation History\n")
            f.write(f"# Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Format: [TIMESTAMP] ROLE: CONTENT\n")
            f.write("=" * 80 + "\n\n")

    def _write_entry(self, role: str, content: str, indent: int = 0):
        prefix = "  " * indent
        self._conv_logger.info(f"{prefix}{role}: {content}")

    def log_user(self, content: str):
        self._write_entry("User", content)

    def log_assistant_text(self, text: str):
        if text.strip():
            self._write_entry("Assistant", text)

    def log_tool_call(self, tool_name: str, tool_id: str, arguments: dict, waiting_for: list = None):
        args_str = str(arguments) if arguments else "()"
        if waiting_for:
            self._write_entry("ToolCall", f"[{tool_name}] id={tool_id} args={args_str} (WAITING for: {waiting_for})", indent=1)
        else:
            self._write_entry("ToolCall", f"[{tool_name}] id={tool_id} args={args_str}", indent=1)

    def log_tool_promoted(self, tool_name: str, tool_id: str):
        self._write_entry("ToolPromoted", f"[{tool_name}] id={tool_id} promoted to RUNNING", indent=1)

    def log_tool_result(self, tool_name: str, tool_id: str, result: str):
        if len(result) > 500:
            result = result[:500] + f"... [truncated, total {len(result)} chars]"
        self._write_entry("ToolResult", f"[{tool_name}] id={tool_id} result={result}", indent=1)

    def log_error(self, content: str):
        """Log error to conversation log."""
        self._write_entry("Error", content)

    def log_separator(self):
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write("\n" + "-" * 80 + "\n\n")

    def get_log_file_path(self) -> str:
        return self.log_file


def debug(msg: str):
    _logger.debug(msg)


def info(msg: str):
    _logger.info(msg)


def warning(msg: str):
    _logger.warning(msg)


def error(msg: str):
    _logger.error(msg)
