"""Concurrent tool executor with explicit state management - now with yield-based events."""

import asyncio
from typing import Any

from .base import ToolRegistry
from .state_manager import (
    ToolStateManager, MutexGroup, ToolExecution,
    ToolStarted, ToolCompleted
)
from ..events import ToolPermissionRequiredEvent, AskUserQuestionEvent


# Default mutex groups for common tool interactions
DEFAULT_MUTEX_GROUPS = [
    MutexGroup("file_write", ["write", "bash"]),
    # File write and bash commands are mutually exclusive
    # to prevent concurrent modifications to the same file

    MutexGroup("system", ["bash"]),
    # Only one system command at a time for safety

    # Note: "read" is NOT in any mutex group - reads can happen concurrently
]


class ConcurrentToolExecutor:
    """Tool executor with explicit state management, mutex groups, and permission checks."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mutex_groups: list[MutexGroup] = None
    ):
        self.tool_registry = tool_registry
        self.state_manager = ToolStateManager(mutex_groups or DEFAULT_MUTEX_GROUPS)

        # Permission/question handling state
        self._permission_events: dict[str, asyncio.Event] = {}
        self._permission_results: dict[str, bool] = {}
        self._question_events: dict[str, asyncio.Event] = {}
        self._question_answers: dict[str, str] = {}

    async def _check_permission(self, execution: ToolExecution, event_queue: asyncio.Queue) -> bool:
        """Check if tool execution requires user permission.

        Returns True if execution should proceed, False if denied.
        Blocks until user responds if permission is required.
        """
        tool = self.tool_registry.get(execution.tool_name)
        if not tool:
            return True  # Tool not found, let execution fail naturally

        # Skip if tool doesn't have check_permission or it returns None
        if not hasattr(tool, 'check_permission'):
            return True

        permission_req = await tool.check_permission(**execution.arguments)
        if permission_req is None:
            return True  # No permission needed

        # Need user confirmation - create event and wait
        permission_event = asyncio.Event()
        self._permission_events[execution.id] = permission_event
        self._permission_results[execution.id] = False  # Default to deny

        # Send permission request event to REPL
        tool_use_id = execution.tool_use_id or execution.id
        await event_queue.put(ToolPermissionRequiredEvent(
            exec_id=execution.id,
            tool_call_id=tool_use_id,
            name=execution.tool_name,
            title=permission_req.get('title', 'Permission Required'),
            message=permission_req.get('message', ''),
            severity=permission_req.get('severity', 'warning')
        ))

        # Wait for user response
        await permission_event.wait()

        # Get result
        approved = self._permission_results.get(execution.id, False)

        # Cleanup
        del self._permission_events[execution.id]
        del self._permission_results[execution.id]

        return approved

    def resolve_permission(self, exec_id: str, approved: bool) -> bool:
        """Resolve a pending permission request.

        Called by REPL/Agent when user makes a choice.
        Returns True if the request was found and resolved, False otherwise.
        """
        if exec_id not in self._permission_events:
            return False

        self._permission_results[exec_id] = approved
        self._permission_events[exec_id].set()
        return True

    def resolve_question(self, exec_id: str, answer: str) -> bool:
        """Resolve a pending user question.

        Called by REPL/Agent when user provides an answer.
        Returns True if the request was found and resolved, False otherwise.
        """
        if exec_id not in self._question_events:
            return False

        self._question_answers[exec_id] = answer
        self._question_events[exec_id].set()
        return True

    async def submit_and_start(self, tool_use: dict, event_queue: asyncio.Queue):
        """Submit tool and immediately start execution if not blocked by mutex.

        Events are put into queue for consumption by caller.
        Tool execution starts right away (in background task) if not blocked.
        """
        execution, event = await self.state_manager.submit(tool_use)

        # Put initial event into queue
        await event_queue.put(event)

        if isinstance(event, ToolStarted):
            # Start tool execution in background task
            asyncio.create_task(self._run_tool(execution, event_queue))

    async def _run_tool(self, execution: ToolExecution, event_queue: asyncio.Queue):
        """Run a single tool and put completion event into queue.

        Also handles promotion of waiting tools when this tool completes.
        Includes permission check before execution.
        """
        # Special handling for ask_user tool
        if execution.tool_name == "ask_user":
            await self._run_ask_user(execution, event_queue)
            return

        # Check permission first
        approved = await self._check_permission(execution, event_queue)

        if not approved:
            # User denied permission - mark as completed with error
            tool_use_id = execution.tool_use_id or execution.id
            denied_event = ToolCompleted(
                exec_id=execution.id,
                tool_use_id=tool_use_id,
                tool_name=execution.tool_name,
                result=None,
                error="Permission denied by user"
            )
            await event_queue.put(denied_event)

            # Handle promotion of waiting tools
            promoted = await self._on_tool_completed(execution.id)
            for promoted_event in promoted:
                await event_queue.put(promoted_event)
                promoted_exec = self.state_manager.executions.get(promoted_event.exec_id)
                if promoted_exec:
                    asyncio.create_task(self._run_tool(promoted_exec, event_queue))
            return

        # Permission approved - run the tool
        async for completed_event in self._execute_tool(execution):
            await event_queue.put(completed_event)

            # Handle promotion of waiting tools
            if isinstance(completed_event, ToolCompleted):
                promoted = await self._on_tool_completed(execution.id)
                for promoted_event in promoted:
                    await event_queue.put(promoted_event)
                    promoted_exec = self.state_manager.executions.get(promoted_event.exec_id)
                    if promoted_exec:
                        asyncio.create_task(self._run_tool(promoted_exec, event_queue))

    async def _run_ask_user(self, execution: ToolExecution, event_queue: asyncio.Queue):
        """Run ask_user tool: send question event and wait for answer."""
        tool_use_id = execution.tool_use_id or execution.id
        args = execution.arguments

        # Create event to wait for user answer
        question_event = asyncio.Event()
        self._question_events[execution.id] = question_event
        self._question_answers[execution.id] = ""

        # Send question event to REPL
        await event_queue.put(AskUserQuestionEvent(
            exec_id=execution.id,
            tool_call_id=tool_use_id,
            question=args.get("question", ""),
            context=args.get("context", ""),
            options=args.get("options", [])
        ))

        # Wait for user answer
        await question_event.wait()

        # Get answer
        answer = self._question_answers.get(execution.id, "")

        # Cleanup
        del self._question_events[execution.id]
        del self._question_answers[execution.id]

        # Execute tool with answer
        tool = self.tool_registry.get(execution.tool_name)
        if tool:
            try:
                result = await tool.execute(**args, answer=answer)
                execution.result = result
                completed_event = ToolCompleted(
                    exec_id=execution.id,
                    tool_use_id=tool_use_id,
                    tool_name=execution.tool_name,
                    result=result,
                    error=None
                )
            except Exception as e:
                execution.error = str(e)
                completed_event = ToolCompleted(
                    exec_id=execution.id,
                    tool_use_id=tool_use_id,
                    tool_name=execution.tool_name,
                    result=None,
                    error=str(e)
                )
        else:
            execution.error = f"Tool '{execution.tool_name}' not found"
            completed_event = ToolCompleted(
                exec_id=execution.id,
                tool_use_id=tool_use_id,
                tool_name=execution.tool_name,
                result=None,
                error=f"Tool '{execution.tool_name}' not found"
            )

        await event_queue.put(completed_event)

        # Handle promotion of waiting tools
        promoted = await self._on_tool_completed(execution.id)
        for promoted_event in promoted:
            await event_queue.put(promoted_event)
            promoted_exec = self.state_manager.executions.get(promoted_event.exec_id)
            if promoted_exec:
                asyncio.create_task(self._run_tool(promoted_exec, event_queue))

    async def _on_tool_completed(self, exec_id: str) -> list[ToolStarted]:
        """Handle tool completion and promote waiting tools."""
        execution = self.state_manager.executions.get(exec_id)
        if not execution:
            return []

        promoted = await self.state_manager.on_completed(
            exec_id,
            result=execution.result,
            error=execution.error
        )
        return promoted

    async def _execute_tool(self, execution: ToolExecution):
        """Execute a single tool and yield completion event."""
        tool_name = execution.tool_name
        tool_input = execution.arguments

        tool = self.tool_registry.get(tool_name)
        tool_use_id = execution.tool_use_id or execution.id

        if not tool:
            execution.error = f"Tool '{tool_name}' not found"
            yield ToolCompleted(
                exec_id=execution.id,
                tool_use_id=tool_use_id,
                tool_name=tool_name,
                result=None,
                error=f"Tool '{tool_name}' not found"
            )
            return

        try:
            result = await tool.execute(**tool_input)
            execution.result = result

            yield ToolCompleted(
                exec_id=execution.id,
                tool_use_id=tool_use_id,
                tool_name=tool_name,
                result=result,
                error=None
            )

        except Exception as e:
            execution.error = str(e)
            yield ToolCompleted(
                exec_id=execution.id,
                tool_use_id=tool_use_id,
                tool_name=tool_name,
                result=None,
                error=str(e)
            )
