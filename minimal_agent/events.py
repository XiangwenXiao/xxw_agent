"""Agent events for streaming mode."""

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentEvent:
    """Base class for all agent events."""
    pass


# ============ LLM Events ============

@dataclass
class TokenEvent(AgentEvent):
    """Emitted when a text token is received from LLM."""
    text: str


@dataclass
class CompleteEvent(AgentEvent):
    """Emitted when the agent completes with the final response."""
    text: str


# ============ Tool Events (mirrors state_manager events) ============

@dataclass
class ToolWaitingEvent(AgentEvent):
    """Emitted when a tool is waiting for mutex."""
    tool_call_id: str
    name: str
    input: dict
    waiting_for: list[str]


@dataclass
class ToolCallEvent(AgentEvent):
    """Emitted when a tool call starts executing."""
    tool_call_id: str
    name: str
    input: dict


@dataclass
class ToolPromotedEvent(AgentEvent):
    """Emitted when a waiting tool is promoted to running."""
    tool_call_id: str
    name: str


@dataclass
class ToolResultEvent(AgentEvent):
    """Emitted when a tool execution completes."""
    tool_call_id: str
    name: str
    content: str
    success: bool


@dataclass
class ToolPermissionRequiredEvent(AgentEvent):
    """Emitted when a tool requires user permission before execution."""
    exec_id: str
    tool_call_id: str
    name: str
    title: str
    message: str
    severity: str


@dataclass
class AskUserQuestionEvent(AgentEvent):
    """Emitted when a tool needs to ask user a question."""
    exec_id: str
    tool_call_id: str
    question: str
    context: str
    options: list[str]


# Union type for all events
AgentEventType = TokenEvent | ToolWaitingEvent | ToolCallEvent | ToolPromotedEvent | ToolResultEvent | ToolPermissionRequiredEvent | AskUserQuestionEvent | CompleteEvent
