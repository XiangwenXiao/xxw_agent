"""Logging configuration for the agent."""

import os
import logging
from datetime import datetime
from typing import Optional


# Default log level (can be overridden by AGENT_LOG_LEVEL env var)
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%H:%M:%S"


def get_log_level() -> int:
    """Get log level from environment variable."""
    level_name = os.getenv("AGENT_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    return getattr(logging, level_name, logging.INFO)


def setup_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """Setup a logger with the given name.

    Args:
        name: Logger name (typically __name__)
        log_file: Optional file to write logs to (in addition to console)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(get_log_level())

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(get_log_level())
    console_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # File always gets DEBUG level
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# Global agent logger
_agent_logger: Optional[logging.Logger] = None


def get_agent_logger() -> logging.Logger:
    """Get the global agent logger."""
    global _agent_logger
    if _agent_logger is None:
        _agent_logger = setup_logger("agent", log_file=".agent_debug.log")
    return _agent_logger


# Convenience functions for common log levels
def debug(msg: str) -> None:
    """Log debug message."""
    get_agent_logger().debug(msg)


def info(msg: str) -> None:
    """Log info message."""
    get_agent_logger().info(msg)


def warning(msg: str) -> None:
    """Log warning message."""
    get_agent_logger().warning(msg)


def error(msg: str) -> None:
    """Log error message."""
    get_agent_logger().error(msg)
