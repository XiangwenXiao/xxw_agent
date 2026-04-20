"""Agent with streaming tool use loop and explicit state management."""

import asyncio
from minimal_agent.llm_client import LLMClient
from minimal_agent.context import Context
from minimal_agent.tools.base import ToolRegistry
from minimal_agent.tools.concurrent_executor import ConcurrentToolExecutor
from minimal_agent.tools.state_manager import ToolWaiting, ToolStarted, ToolCompleted
from minimal_agent.events import (
    TokenEvent, ToolCallEvent, ToolWaitingEvent, ToolResultEvent, CompleteEvent,
    ToolPermissionRequiredEvent, AskUserQuestionEvent
)
from minimal_agent.memory import MemoryManager
from minimal_agent.config import get_config
from minimal_agent.tools.implementations.todoWrite import TodoWriteTool
from minimal_agent.logger import debug, info, warning, error


class Agent:
    """Agent with streaming tool loop - supports concurrent tool execution with state management."""

    def __init__(
        self,
        llm_client: LLMClient,
        context: Context,
        tools: ToolRegistry,
        enable_memory: bool = True
    ):
        """Initialize agent with LLM client, context manager, and tool registry."""
        self.llm = llm_client
        self.context = context
        self.tools = tools
        self.memory_manager = MemoryManager() if enable_memory else None
        self._current_executor: ConcurrentToolExecutor | None = None

        # Load configuration
        self.config = get_config()

        # Todo reminder system
        self.todo_list: list[dict] = []
        self.todo_reminder_counter: int = 0

        # Inject memory context into system prompt if memory is enabled
        if self.memory_manager:
            memory_context = self.memory_manager.get_memory_context()
            if memory_context:
                current_system = self.context.get_system_prompt()
                self.context.system_prompt = f"{current_system}\n\n{memory_context}"

    def resolve_permission(self, exec_id: str, approved: bool) -> bool:
        """Resolve a pending permission request from user.

        Called by REPL when user confirms or denies a permission request.
        Returns True if the request was found and resolved.
        """
        if self._current_executor is None:
            return False
        return self._current_executor.resolve_permission(exec_id, approved)

    def resolve_question(self, exec_id: str, answer: str) -> bool:
        """Resolve a pending user question.

        Called by REPL when user provides an answer to an agent question.
        Returns True if the question was found and resolved.
        """
        if self._current_executor is None:
            return False
        return self._current_executor.resolve_question(exec_id, answer)

    def _format_todo_reminder(self) -> str | None:
        """格式化 todo 提醒消息，如果没有待办事项则返回 None。"""
        return TodoWriteTool.format_todo_reminder()

    async def run_stream(self, user_input: str):
        """Run agent loop as async generator, yielding events for UI consumption.

        Yields TokenEvent, ToolWaitingEvent, ToolCallEvent, ToolResultEvent, CompleteEvent.
        Tools are launched during streaming but results are yielded after stream ends.
        """
        info(f"[AGENT] run_stream started with input: {user_input[:100]}...")
        debug(f"[AGENT] Full user input: {user_input}")

        # Add user message
        self.context.add_user(user_input)
        debug(f"[AGENT] User message added to context. Messages count: {len(self.context.messages)}")

        loop_count = 0
        while True:
            loop_count += 1
            info(f"[AGENT] === Starting loop iteration {loop_count} ===")
            debug(f"[AGENT] Context state - messages: {len(self.context.messages)}, "
                  f"todo_counter: {self.todo_reminder_counter}")
            # Check todo reminder interval
            self.todo_reminder_counter += 1
            debug(f"[AGENT] todo_counter: {self.todo_reminder_counter}/{self.config.todo_reminder_interval}")
            if self.todo_reminder_counter >= self.config.todo_reminder_interval:
                self.todo_reminder_counter = 0
                reminder = self._format_todo_reminder()
                if reminder:
                    info(f"[AGENT] Adding todo reminder to context")
                    debug(f"[AGENT] Reminder content: {reminder[:200]}...")
                    # Add reminder as a system-like user message
                    self.context.add_user(f"[系统提醒] {reminder}")

            # Apply three-layer compression before getting response
            info(f"[AGENT] Applying compression...")
            self.context.applyToolResultBudget()
            self.context.microcompact()
            self.context.autocompact()

            # Create executor (uses default mutex groups)
            executor = ConcurrentToolExecutor(self.tools)
            self._current_executor = executor  # Save for permission resolution
            debug(f"[AGENT] Executor created")

            # Track state
            current_tool_results = []
            assistant_content = []
            event_queue = asyncio.Queue()

            # Start LLM stream
            info(f"[AGENT] Starting LLM stream...")
            try:
                llm_stream = self.llm.complete_async_stream(
                    messages=self.context.get_messages(),
                    system=self.context.get_system_prompt(),
                    tools=self.tools.get_definitions()
                )
                debug(f"[AGENT] LLM stream created")
            except Exception as e:
                error(f"[AGENT] Failed to create LLM stream: {e}")
                raise

            full_text = ""
            chunk_count = 0
            tool_use_count = 0

            # Consume LLM stream
            debug(f"[AGENT] Consuming LLM stream...")
            async for chunk in llm_stream:
                chunk_count += 1

                if chunk["type"] == "text":
                    text = chunk["text"]
                    full_text += text
                    assistant_content.append({"type": "text", "text": text})
                    yield TokenEvent(text=text)
                    # 流式过程中只输出 text，不处理工具事件

                elif chunk["type"] == "tool_use":
                    tool_use_count += 1
                    tool_use = chunk["tool_use"]
                    info(f"[AGENT] Tool use detected: {tool_use['name']}")
                    debug(f"[AGENT] Tool input: {tool_use.get('input', {})}")
                    assistant_content.append({
                        "type": "tool_use",
                        "id": tool_use["id"],
                        "name": tool_use["name"],
                        "input": tool_use["input"]
                    })

                    # 立即提交并后台启动工具
                    await executor.submit_and_start(tool_use, event_queue)

            info(f"[AGENT] LLM stream ended: {chunk_count} chunks, {tool_use_count} tool uses, {len(full_text)} chars")

            # LLM 流结束
            # Add assistant message
            if assistant_content:
                self.context.add_assistant_content_blocks(assistant_content)
                debug(f"[AGENT] Assistant content added: {len(assistant_content)} blocks")

            # 消费所有工具事件（等待所有工具完成）
            info(f"[AGENT] Waiting for tool events...")
            tool_wait_iterations = 0
            while True:
                tool_wait_iterations += 1

                # 先消费队列中已有的事件
                while not event_queue.empty():
                    tool_event = event_queue.get_nowait()
                    debug(f"[AGENT] Processing tool event: {type(tool_event).__name__}")
                    async for agent_event in self._convert_event(tool_event, current_tool_results):
                        yield agent_event

                # 检查是否全部完成
                status = executor.state_manager.get_status()
                if status["running"] == 0 and status["waiting"] == 0 and event_queue.empty():
                    info(f"[AGENT] All tools completed after {tool_wait_iterations} iterations")
                    break

                if tool_wait_iterations % 100 == 0:
                    debug(f"[AGENT] Still waiting for tools... (iteration {tool_wait_iterations}, status: {status})")

                await asyncio.sleep(0.01)

            debug(f"[AGENT] Tool results: {len(current_tool_results)}")

            if not current_tool_results:
                # No tool calls - final response
                info(f"[AGENT] No tool calls, completing with {len(full_text)} chars")
                yield CompleteEvent(text=full_text)
                return

            # Add all tool results to context
            info(f"[AGENT] Adding {len(current_tool_results)} tool results to context")
            for result in current_tool_results:
                debug(f"[AGENT] Tool result: {result['tool_call_id'][:20]}... = {len(result['content'])} chars")
                self.context.add_tool_result(
                    result["tool_call_id"],
                    result["content"]
                )

            info(f"[AGENT] Loop {loop_count} completed, continuing to next iteration")
            # Continue to next iteration for tool results

    async def _convert_event(self, tool_event, current_tool_results):
        """Convert internal tool event to public agent event and track results."""
        if isinstance(tool_event, ToolWaiting):
            yield ToolWaitingEvent(
                tool_call_id=tool_event.tool_use_id,
                name=tool_event.tool_name,
                input=tool_event.input,
                waiting_for=tool_event.waiting_for
            )
        elif isinstance(tool_event, ToolStarted):
            yield ToolCallEvent(
                tool_call_id=tool_event.tool_use_id,
                name=tool_event.tool_name,
                input=tool_event.input
            )
        elif isinstance(tool_event, ToolCompleted):
            result_content = tool_event.result if tool_event.result else tool_event.error
            current_tool_results.append({
                "tool_call_id": tool_event.tool_use_id,
                "content": result_content
            })
            yield ToolResultEvent(
                tool_call_id=tool_event.tool_use_id,
                name=tool_event.tool_name,
                content=result_content or "",
                success=tool_event.error is None
            )
        elif isinstance(tool_event, ToolPermissionRequiredEvent):
            # Permission request from executor - pass through to REPL
            yield tool_event
        elif isinstance(tool_event, AskUserQuestionEvent):
            # User question from executor - pass through to REPL
            yield tool_event
