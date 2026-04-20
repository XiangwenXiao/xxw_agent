"""Tool state management with mutex groups and explicit status tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, AsyncGenerator
import asyncio


class ToolStatus(Enum):
    """Tool execution status."""
    WAITING = auto()    # Waiting for mutex tools to complete
    RUNNING = auto()    # Currently executing
    COMPLETED = auto()  # Execution completed (success or failure)


@dataclass
class ToolExecution:
    """Represents a single tool execution with its state."""
    id: str
    tool_name: str
    arguments: dict
    status: ToolStatus
    tool_use_id: str = None  # Original tool_use id from LLM
    result: Any = None
    error: str = None
    start_time: datetime = None
    end_time: datetime = None
    waiting_for: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "id": self.id,
            "tool": self.tool_name,
            "status": self.status.name,
            "waiting_for": self.waiting_for if self.waiting_for else None,
            "duration": self._get_duration(),
            "result": self._truncate_result()
        }

    def _get_duration(self) -> str:
        """Calculate execution duration."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return f"{delta.total_seconds():.2f}s"
        elif self.start_time:
            delta = datetime.now() - self.start_time
            return f"{delta.total_seconds():.2f}s (running)"
        return "N/A"

    def _truncate_result(self, max_len: int = 100) -> str:
        """Truncate result for display."""
        if self.error:
            return f"ERROR: {self.error[:max_len]}"
        if self.result:
            result_str = str(self.result)
            if len(result_str) > max_len:
                return result_str[:max_len] + f"... ({len(result_str)} chars)"
            return result_str
        return None


@dataclass
class MutexGroup:
    """Defines a group of mutually exclusive tools."""
    name: str
    tools: list[str]  # Tool names that are mutually exclusive


# Event types for yield-based state management
@dataclass
class ToolWaiting:
    """Event: Tool is waiting for mutex."""
    exec_id: str
    tool_use_id: str
    tool_name: str
    input: dict
    waiting_for: list[str]


@dataclass
class ToolStarted:
    """Event: Tool started executing."""
    exec_id: str
    tool_use_id: str
    tool_name: str
    input: dict


@dataclass
class ToolCompleted:
    """Event: Tool execution completed."""
    exec_id: str
    tool_use_id: str
    tool_name: str
    result: Any
    error: str = None


class ToolStateManager:
    """Manages tool execution states and mutex relationships with yield-based events."""

    def __init__(self, mutex_groups: list[MutexGroup] = None):
        self.mutex_groups = mutex_groups or []
        self.executions: dict[str, ToolExecution] = {}
        self._running: set[str] = set()
        self._waiting: set[str] = set()
        self._lock = asyncio.Lock()
        self._execution_counter = 0
        self._event_queue: asyncio.Queue = asyncio.Queue()

    def _generate_id(self) -> str:
        """Generate unique execution ID."""
        self._execution_counter += 1
        return f"exec_{self._execution_counter:04d}"

    def _is_mutex(self, tool_name1: str, tool_name2: str) -> bool:
        """Check if two tools are mutually exclusive (same tool or same mutex group)."""
        if tool_name1 == tool_name2:
            return True
        for group in self.mutex_groups:
            tools_in_group = set(group.tools)
            if tool_name1 in tools_in_group and tool_name2 in tools_in_group:
                return True
        return False

    def _get_blocking_executions(self, tool_name: str) -> list[str]:
        """Get IDs of running executions that block this tool due to mutex."""
        blocking = []
        for exec_id in self._running:
            execution = self.executions[exec_id]
            if self._is_mutex(tool_name, execution.tool_name):
                blocking.append(exec_id)
        return blocking

    async def submit(self, tool_use: dict) -> tuple[ToolExecution, ToolWaiting | ToolStarted | None]:
        """Submit a tool for execution, determine if it can run or must wait.

        Returns (execution, event) where event is ToolWaiting or ToolStarted.
        """
        async with self._lock:
            exec_id = self._generate_id()
            tool_name = tool_use.get("name", "unknown")
            arguments = tool_use.get("input", {})
            tool_use_id = tool_use.get("id")

            blocking = self._get_blocking_executions(tool_name)

            if blocking:
                execution = ToolExecution(
                    id=exec_id,
                    tool_name=tool_name,
                    arguments=arguments,
                    status=ToolStatus.WAITING,
                    tool_use_id=tool_use_id,
                    waiting_for=blocking.copy()
                )
                self._waiting.add(exec_id)
                event = ToolWaiting(
                    exec_id=exec_id,
                    tool_use_id=tool_use_id or exec_id,
                    tool_name=tool_name,
                    input=arguments,
                    waiting_for=blocking.copy()
                )
            else:
                execution = ToolExecution(
                    id=exec_id,
                    tool_name=tool_name,
                    arguments=arguments,
                    status=ToolStatus.RUNNING,
                    tool_use_id=tool_use_id,
                    start_time=datetime.now()
                )
                self._running.add(exec_id)
                event = ToolStarted(
                    exec_id=exec_id,
                    tool_use_id=tool_use_id or exec_id,
                    tool_name=tool_name,
                    input=arguments
                )

            self.executions[exec_id] = execution
            return execution, event

    async def on_completed(self, exec_id: str, result: Any = None, error: str = None) -> list[ToolStarted]:
        """Mark execution as completed and promote waiting tools that are no longer blocked.

        Returns list of ToolStarted events for promoted tools.
        """
        async with self._lock:
            if exec_id not in self.executions:
                return []

            execution = self.executions[exec_id]
            execution.status = ToolStatus.COMPLETED
            execution.end_time = datetime.now()
            execution.result = result
            execution.error = error

            self._running.discard(exec_id)

            # Promote waiting tools
            promoted_events = await self._promote_waiting_tools(exec_id)
            return promoted_events

    async def _promote_waiting_tools(self, completed_exec_id: str) -> list[ToolStarted]:
        """Promote waiting tools when their blocking dependencies complete."""
        promoted = []

        for exec_id in list(self._waiting):
            execution = self.executions[exec_id]

            if completed_exec_id in execution.waiting_for:
                execution.waiting_for.remove(completed_exec_id)

            if not execution.waiting_for:
                execution.status = ToolStatus.RUNNING
                execution.start_time = datetime.now()
                self._waiting.discard(exec_id)
                self._running.add(exec_id)
                promoted.append(ToolStarted(
                    exec_id=exec_id,
                    tool_use_id=execution.tool_use_id or exec_id,
                    tool_name=execution.tool_name,
                    input=execution.arguments
                ))

        return promoted

    def get_status(self) -> dict:
        """Return summary of execution status (running/waiting/completed/total counts)."""
        return {
            "running": len(self._running),
            "waiting": len(self._waiting),
            "completed": len([e for e in self.executions.values()
                            if e.status == ToolStatus.COMPLETED]),
            "total": len(self.executions)
        }

    def get_running(self) -> list[ToolExecution]:
        """Return list of currently running executions."""
        return [self.executions[eid] for eid in self._running]

    def get_waiting(self) -> list[ToolExecution]:
        """Return list of currently waiting executions."""
        return [self.executions[eid] for eid in self._waiting]

    def print_status(self):
        """Print execution status table to console (for debugging)."""
        print("\n=== Tool Execution Status ===")

        if self._running:
            print(f"\n🔵 RUNNING ({len(self._running)}):")
            for exec_id in self._running:
                e = self.executions[exec_id]
                duration = (datetime.now() - e.start_time).total_seconds()
                print(f"  [{e.id}] {e.tool_name} ({duration:.1f}s)")

        if self._waiting:
            print(f"\n⏳ WAITING ({len(self._waiting)}):")
            for exec_id in self._waiting:
                e = self.executions[exec_id]
                waiting_names = [self.executions[wid].tool_name for wid in e.waiting_for]
                print(f"  [{e.id}] {e.tool_name} (waiting for: {', '.join(waiting_names)})")

        completed = [e for e in self.executions.values()
                    if e.status == ToolStatus.COMPLETED]
        if completed:
            print(f"\n✅ COMPLETED ({len(completed)}):")
            for e in completed[-5:]:
                status_icon = "✓" if not e.error else "✗"
                print(f"  [{status_icon}] {e.tool_name} ({e._get_duration()})")

        print("-" * 40)
