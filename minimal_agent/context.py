"""Context management with three-layer compression."""

import json
from datetime import datetime
from pathlib import Path
from .llm_client import LLMClient
from .tools.base import ToolRegistry


# Model context length mapping
MODEL_CONTEXT_LIMITS = {
    "claude-3-5-haiku": 200000,
    "claude-3-5-sonnet": 200000,
    "claude-3-opus": 200000,
    "claude-3-haiku": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-5-haiku-20241022": 200000,
    "claude-3-5-sonnet-20241022": 200000,
    "claude-3-opus-20240229": 200000,
}


# Base system prompt template - 7 sections
BASE_SYSTEM_PROMPT_TEMPLATE = """# 1. 角色与功能

你是一个帮助用户处理软件工程任务的交互式 Agent。你可以使用工具来读取代码、执行命令、修改文件，协助用户完成编程相关的工作。

# 2. 基本行为准则

当前工作目录: {cwd}
所有文件操作都基于此目录，使用相对路径时都是相对于此目录。
- 先理解用户需求，再采取行动。如果需求不明确，使用 ask_user 工具询问澄清
- 在修改代码前，先读取相关文件，理解现有逻辑
- 遇到困难或不确定时，主动向用户求助，不要猜测
- 尊重用户的选择，如果用户拒绝某个操作，接受并寻找替代方案
- 不要提议超出任务范围的"改进"或重构


# 3. 执行任务时应当遵循的规则

- **先读取，后修改**：在编辑文件前，务必先读取并理解其内容
- **增量修改**：一次只做一个逻辑变更，验证后再继续
- **保持简洁**：只做任务需要的修改，不要过度设计
- **安全第一**：避免引入安全漏洞（命令注入、XSS、SQL 注入等）
- **信任但验证**：内部代码可以信任，但用户输入和外部 API 需要验证
- **避免重复**：如果一种方法失败，先诊断原因再切换策略，不要盲目重试


# 4. 操作时的注意事项

- **覆盖文件警告**：当写入已存在的文件时，系统会请求用户确认
- **路径安全警告**：当写入工作目录外的文件时，系统会请求用户确认
- **危险命令警告**：bash 命令涉及删除、移动、重定向等操作时，系统会请求用户确认
- **谨慎对待破坏性操作**：删除文件、删除分支、强制推送等操作前与用户确认
- **遇到意外状态**：如不熟悉的文件或分支，先调查再操作，不要直接覆盖


# 5. 工具使用指南

{tools_schema}


# 6. 语气风格

- 简洁直接，直奔主题
- 除非用户要求，否则不使用表情符号
- 解释时只包含用户理解所需的内容
- 优先使用短句，避免长篇解释
- 引用代码时包含文件路径和行号，如 file.py:42


# 7. 与用户高效沟通

**需要输出时：**
- 需要用户做决策的节点
- 任务完成或遇到里程碑时的状态更新
- 发生错误或阻碍，需要改变计划时

**不需要输出时：**
- 正在执行的操作（工具调用已显示）
- 成功的结果（工具结果已显示）
- 内部思考过程

**简洁原则：**
- 如果可以用一句话表达，不用三句
- 先给出答案或行动，再简要说明原因（如需要）
- 不要重述用户说过的话
"""


class Context:
    """Context with three-layer compression mechanism."""

    def __init__(
        self,
        tools: ToolRegistry,
        max_tokens: int = 8000,
        llm_client: LLMClient | None = None,
        model_name: str | None = None,
        system_prompt: str | None = None
    ):
        """Initialize context with system prompt.

        Args:
            tools: Tool registry for building tool schema
            max_tokens: Maximum context length
            llm_client: LLM client for compression
            model_name: Model name for context limit lookup
            system_prompt: Custom system prompt (optional, uses default if not provided)
        """
        # Build system prompt with current working directory and tools
        self.system_prompt = system_prompt or self._build_default_system_prompt(tools)
        self.max_tokens = max_tokens
        self.llm_client = llm_client
        self.model_name = model_name
        self.messages: list[dict] = []

        # Layer 1: Big content offloading
        self.offload_dir = Path(".agent_context/offload")
        self.offload_threshold = 100000  # 100KB

        # Layer 2: Tool results total length control
        self.tool_results_total_limit = 500000  # 500K characters
        self.tool_result_keep_recent = 4  # Keep recent 4 tool results

        # Layer 3: Global context compression
        self.context_threshold_ratio = 0.93  # 93% of model limit
        self._model_context_limit = self._get_model_context_limit()

        # Ensure offload directory exists
        self._ensure_offload_dir()

    @staticmethod
    def _build_default_system_prompt(tools: ToolRegistry) -> str:
        """Build default system prompt with current working directory and tools."""
        cwd = Path.cwd().resolve()
        tools_schema = tools.get_tools_schema()
        return BASE_SYSTEM_PROMPT_TEMPLATE.format(cwd=str(cwd), tools_schema=tools_schema)

    def _ensure_offload_dir(self) -> None:
        """Ensure offload directory exists."""
        self.offload_dir.mkdir(parents=True, exist_ok=True)

    def _get_model_context_limit(self) -> int:
        """Get model context limit based on model name or config."""
        # Priority: explicit max_tokens > model name lookup > default
        if self.max_tokens and self.max_tokens >= 1000:
            return self.max_tokens

        if self.model_name:
            for model_key, limit in MODEL_CONTEXT_LIMITS.items():
                if model_key in self.model_name.lower():
                    return limit

        return 200000  # Default 200K

    def _estimate_tokens(self, text: str) -> int:
        """Simple token estimation: characters / 4."""
        return len(text) // 2

    def _get_message_content_text(self, message: dict) -> str:
        """Extract text content from message (handle content blocks)."""
        content = message.get("content", "")

        if isinstance(content, list):
            texts = []
            for block in content:
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    texts.append(f"[tool_use: {block.get('name', '')}]")
                elif block.get("type") == "tool_result":
                    tool_content = block.get("content", "")
                    if isinstance(tool_content, list):
                        tool_content = str(tool_content)
                    texts.append(f"[tool_result: {tool_content[:100]}...]")
            return " ".join(texts)

        return str(content)

    def _calculate_total_length(self) -> int:
        """Calculate total context length (system + messages)."""
        total = len(self.system_prompt)
        for msg in self.messages:
            total += len(self._get_message_content_text(msg))
        return total

    def _calculate_tool_results_length(self) -> int:
        """Calculate total length of all tool results."""
        total = 0
        for msg in self.messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_result":
                        tool_content = block.get("content", "")
                        total += len(str(tool_content))
        return total

    def _summarize_with_llm(self, content: str, max_words: int = 50) -> str:
        """Use LLM to generate summary."""
        if not self.llm_client:
            return content[:200] + "... [truncated]"

        try:
            prompt = f"请将以下内容摘要为{max_words}字以内，保留关键信息：\n\n{content[:5000]}"
            response = self.llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            return response.content[:max_words * 4]  # Approximate word count
        except Exception:
            return content[:200] + "... [truncated]"

    def _offload_large_content(self, tool_call_id: str, content: str) -> str:
        """Layer 1: Offload large content to file."""
        timestamp = datetime.now().isoformat()
        offload_data = {
            "tool_use_id": tool_call_id,
            "content": content,
            "timestamp": timestamp,
            "size": len(content)
        }

        # Save to file
        file_path = self.offload_dir / f"{tool_call_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(offload_data, f, ensure_ascii=False, indent=2)

        # Return reference message
        return f"[内容已保存至 {file_path}，共{len(content)}字符]"

    def applyToolResultBudget(self) -> None:
        """Layer 1: Check and offload large individual tool results."""
        for msg in self.messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_result":
                        tool_content = block.get("content", "")
                        if len(str(tool_content)) > self.offload_threshold:
                            # Offload this large content
                            tool_call_id = block.get("tool_use_id", "unknown")
                            reference = self._offload_large_content(
                                tool_call_id, str(tool_content)
                            )
                            # Replace content with reference
                            block["content"] = reference

    def microcompact(self) -> None:
        """Layer 2: Summarize tool results if total length exceeds threshold."""
        total_length = self._calculate_tool_results_length()

        if total_length <= self.tool_results_total_limit:
            return

        # Collect all tool results with their positions
        tool_results_info = []
        for msg_idx, msg in enumerate(self.messages):
            content = msg.get("content", "")
            if isinstance(content, list):
                for block_idx, block in enumerate(content):
                    if block.get("type") == "tool_result":
                        tool_content = block.get("content", "")
                        tool_results_info.append({
                            "msg_idx": msg_idx,
                            "block_idx": block_idx,
                            "tool_call_id": block.get("tool_use_id", "unknown"),
                            "content": str(tool_content),
                            "length": len(str(tool_content))
                        })

        if len(tool_results_info) <= self.tool_result_keep_recent:
            return

        # Sort by length (descending) for those that can be summarized
        recent_tool_ids = set()
        for info in tool_results_info[-self.tool_result_keep_recent:]:
            recent_tool_ids.add(info["tool_call_id"])

        to_summarize = [info for info in tool_results_info
                       if info["tool_call_id"] not in recent_tool_ids]
        to_summarize.sort(key=lambda x: x["length"], reverse=True)

        # Summarize until under threshold
        for info in to_summarize:
            current_total = self._calculate_tool_results_length()
            if current_total <= self.tool_results_total_limit:
                break

            # Generate summary
            summary = self._summarize_with_llm(info["content"], max_words=50)
            new_content = f"[摘要] 原内容{info['length']}字符，摘要：{summary}"

            # Update the message
            msg = self.messages[info["msg_idx"]]
            content_blocks = msg["content"]
            content_blocks[info["block_idx"]]["content"] = new_content

    def _build_global_summary_prompt(self) -> str:
        """Build prompt for global context summarization."""
        # Extract conversation text
        conversation_parts = []
        for msg in self.messages:
            role = msg.get("role", "unknown")
            text = self._get_message_content_text(msg)
            conversation_parts.append(f"{role}: {text}")

        conversation_text = "\n".join(conversation_parts)

        prompt = f"""请将以下对话历史摘要为结构化格式。保持用户核心意图、已完成的操作和关键信息。

对话历史：
{conversation_text[:10000]}... [如有更多内容已截断]

请按以下格式输出摘要：

## 对话摘要

### 用户核心意图
[一句话概括用户想要什么]

### 已完成的操作
- [操作1]: [结果简述]
- [操作2]: [结果简述]

### 当前状态
- 正在处理: [当前任务]
- 待解决问题: [如有]

### 关键信息
[列出重要的技术细节、文件路径、关键数据等]

### 原始对话统计
- 总轮数: {len(self.messages)}
- 摘要时间: {datetime.now().isoformat()}
"""
        return prompt

    def autocompact(self) -> None:
        """Layer 3: Global context compression when approaching limit."""
        total_length = self._calculate_total_length()
        threshold = int(self._model_context_limit * self.context_threshold_ratio)

        if total_length <= threshold:
            return

        if not self.llm_client:
            # Fallback: simple truncation
            self._simple_truncate()
            return

        try:
            # Generate global summary
            prompt = self._build_global_summary_prompt()
            response = self.llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )

            # Update system prompt with summary and clear messages
            summary = response.content
            self.system_prompt = f"{self.system_prompt}\n\n=== 历史对话摘要 ===\n{summary}"

            # Keep only the last 2 exchanges (user + assistant)
            if len(self.messages) > 4:
                self.messages = self.messages[-4:]

        except Exception:
            # Fallback to simple truncation
            self._simple_truncate()

    def _simple_truncate(self) -> None:
        """Fallback: Simple truncation when LLM is not available."""
        # Keep last 4 messages and add truncation notice
        if len(self.messages) > 4:
            kept_count = len(self.messages) - 4
            self.system_prompt = (
                f"{self.system_prompt}\n\n"
                f"[注：之前{kept_count}条消息已因长度限制被摘要]"
            )
            self.messages = self.messages[-4:]

    def add_user(self, content: str) -> None:
        """Add user message."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str, tool_calls: list[dict] | None = None) -> None:
        """Add assistant message."""
        # Simple text-only message
        if not tool_calls:
            self.messages.append({"role": "assistant", "content": content})
            return

        # Message with tool calls - use content blocks format
        message_content: list[dict] = []

        # Add text content if present
        if content:
            message_content.append({"type": "text", "text": content})

        # Add tool_use blocks
        for call in tool_calls:
            message_content.append({
                "type": "tool_use",
                "id": call["id"],
                "name": call["name"],
                "input": call["arguments"]
            })

        self.messages.append({"role": "assistant", "content": message_content})

    def add_assistant_content_blocks(self, content_blocks: list[dict]) -> None:
        """Add assistant message with content blocks.

        Args:
            content_blocks: List of content blocks (text and tool_use)
        """
        if not content_blocks:
            return

        # Filter out empty text blocks
        filtered_blocks = []
        for block in content_blocks:
            if block.get("type") == "text" and not block.get("text", "").strip():
                continue
            filtered_blocks.append(block)

        if not filtered_blocks:
            return

        # If only one text block, use simple format
        if len(filtered_blocks) == 1 and filtered_blocks[0].get("type") == "text":
            self.messages.append({
                "role": "assistant",
                "content": filtered_blocks[0]["text"]
            })
        else:
            # Multiple blocks or tool_use - use content blocks format
            self.messages.append({
                "role": "assistant",
                "content": filtered_blocks
            })

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        """Add tool result as a user message."""
        self.messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": content
                }
            ]
        })

    def get_messages(self) -> list[dict]:
        """Get all messages (without system prompt)."""
        return self.messages

    def get_system_prompt(self) -> str:
        """Get system prompt."""
        return self.system_prompt

    # Legacy methods for backward compatibility
    def _check_compression(self) -> None:
        """Legacy: No-op, compression handled by three-layer system."""
        pass

    def _compress_old_messages(self) -> None:
        """Legacy: No-op, replaced by three-layer system."""
        pass
