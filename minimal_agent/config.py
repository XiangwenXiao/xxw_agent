"""Global configuration for the agent."""

from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Agent global configuration."""

    # Todo reminder settings
    todo_reminder_interval: int = 3  # 每隔 N 轮对话提醒一次

    # Context compression settings
    context_threshold_ratio: float = 0.93  # 上下文压缩阈值比例
    offload_threshold: int = 100000  # 大内容卸载阈值（字符）
    tool_results_total_limit: int = 500000  # 工具结果总长度限制
    tool_result_keep_recent: int = 4  # 保留最近 N 个工具结果

    # LLM settings
    max_tokens: int = 8000  # 默认最大 token 数


def get_config() -> AgentConfig:
    """Get agent configuration."""
    return AgentConfig()
