"""LLM client for Anthropic API."""

import os
from typing import Any, AsyncIterator
import anthropic


class LLMClient:
    """Simple LLM client with sync and async support."""

    def __init__(self, model: str = None):
        """Initialize LLM client with API key from environment variables."""
        # 从环境变量获取配置
        auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        base_url = os.getenv("ANTHROPIC_BASE_URL")

        # 使用提供的model参数或从环境变量获取
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

        # 优先使用 ANTHROPIC_AUTH_TOKEN，其次使用 ANTHROPIC_API_KEY
        key = auth_token or api_key

        if not key:
            raise ValueError("Either ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY must be set")

        # 创建 Anthropic 客户端（同步和异步）
        if base_url:
            self.client = anthropic.Anthropic(api_key=key, base_url=base_url)
            self.async_client = anthropic.AsyncAnthropic(api_key=key, base_url=base_url)
        else:
            self.client = anthropic.Anthropic(api_key=key)
            self.async_client = anthropic.AsyncAnthropic(api_key=key)

    def complete(
        self,
        messages: list[dict],
        system: str | None = None,
        tools: list[dict] | None = None,
    ) -> "LLMResponse":
        """Call LLM API (non-streaming).

        Returns LLMResponse for non-streaming.
        """
        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
            "tools": tools or []
        }
        if system:
            kwargs["system"] = system

        return self._complete_sync(**kwargs)

    def _complete_sync(self, **kwargs) -> "LLMResponse":
        """Non-streaming completion - returns full response."""
        response = self.client.messages.create(**kwargs)

        # Check for tool calls
        has_tool_calls = False
        tool_calls = []
        content = ""

        for block in response.content:
            if block.type == "tool_use":
                has_tool_calls = True
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input
                })
            elif block.type == "text":
                content += block.text

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            has_tool_calls=has_tool_calls
        )

    async def complete_async_stream(
        self,
        messages: list[dict],
        system: str | None = None,
        tools: list[dict] | None = None
    ) -> AsyncIterator[dict]:
        """Async streaming completion - truly non-blocking for concurrent execution."""
        import json

        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
            "tools": tools or []
        }
        if system:
            kwargs["system"] = system

        stream = await self.async_client.messages.create(**kwargs, stream=True)

        current_tool_use = None
        tool_input_json = ""

        async for event in stream:
            if event.type == "content_block_start":
                if event.content_block.type == "tool_use":
                    current_tool_use = {
                        "id": event.content_block.id,
                        "name": event.content_block.name,
                        "input": {}
                    }
                    tool_input_json = ""

            elif event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    yield {"type": "text", "text": event.delta.text}

                elif event.delta.type == "input_json_delta":
                    if current_tool_use is not None:
                        tool_input_json += event.delta.partial_json

            elif event.type == "content_block_stop":
                if current_tool_use is not None:
                    try:
                        current_tool_use["input"] = json.loads(tool_input_json)
                    except json.JSONDecodeError:
                        current_tool_use["input"] = {}

                    yield {"type": "tool_use", "tool_use": current_tool_use}
                    current_tool_use = None
                    tool_input_json = ""


class LLMResponse:
    """LLM response."""

    def __init__(
        self,
        content: str,
        tool_calls: list[dict],
        has_tool_calls: bool
    ):
        self.content = content
        self.tool_calls = tool_calls
        self.has_tool_calls = has_tool_calls


if __name__ == "__main__":
    """测试 LLMClient 初始化"""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    print("=" * 60)
    print("LLMClient 测试")
    print("=" * 60)

    # 测试环境变量检查
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")

    if auth_token or api_key:
        print(f"✓ API Key 已设置")
    else:
        print("✗ API Key 未设置 (需要 ANTHROPIC_AUTH_TOKEN 或 ANTHROPIC_API_KEY)")
        sys.exit(1)

    # 测试初始化
    try:
        client = LLMClient()
        print(f"✓ LLMClient 初始化成功")
        print(f"  - 模型: {client.model}")
        print(f"  - 客户端类型: {type(client.client).__name__}")
    except ValueError as e:
        print(f"✗ 初始化失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 未知错误: {e}")
        sys.exit(1)

    # 测试实际调用
    print("\n" + "-" * 60)
    print("测试 LLM 调用...")
    print("-" * 60)
    try:
        messages = [{"role": "user", "content": "Hello, can you respond with 'Test OK' in 3 words?"}]
        response = client.complete(messages=messages)
        print(f"✓ LLM 调用成功")
        print(f"  - 回复: {response.content[:100]}...")
        print(f"  - 是否有工具调用: {response.has_tool_calls}")
    except Exception as e:
        print(f"✗ LLM 调用失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n✅ 所有测试通过！")
