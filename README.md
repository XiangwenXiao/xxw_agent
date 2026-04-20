# 最小化 Claude Code 风格 Agent

一个基于 Python 的轻量级 Agent 实现，具有与 Claude Code 类似的架构和功能。

---

## 目录

1. [使用方法](#使用方法)
2. [整体架构](#整体架构)
3. [与 Claude Code 的对比](#与-claude-code-的对比)

---

## 使用方法

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 设置环境变量

```bash
# API Key (必需)
export ANTHROPIC_API_KEY="your-api-key"

# 可选配置
export ANTHROPIC_MODEL="claude-3-5-haiku-20241022"  # 默认模型
export AGENT_LOG_LEVEL="INFO"                          # 日志级别: DEBUG/INFO/WARNING/ERROR
```

### 3. 运行 Agent

```bash
python -m minimal_agent
```

### 4. 交互示例

```
🤖 Agent 准备就绪（输入 'exit' 退出）

User: 读取 README.md 文件

🤖 Agent 思考中...
Agent: 我将为您读取 README.md 文件。

(read 工具被调用)

内容：
# 最小化 Claude Code 风格 Agent
...

User: exit
👋 再见！
```

### 5. 日志调试

如需详细调试信息，设置日志级别：

```bash
# Windows PowerShell
$env:AGENT_LOG_LEVEL="DEBUG"
python -m minimal_agent

# Linux/Mac
AGENT_LOG_LEVEL=DEBUG python -m minimal_agent
```

日志会同时输出到控制台和 `.agent_debug.log` 文件。

---

## 整体架构

### 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                           REPL Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ User Input  │  │   Output    │  │   Permission Dialogs    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Agent Core                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     run_stream() Loop                      ││
│  │  ┌─────────┐    ┌─────────┐    ┌─────────────────────────┐ ││
│  │  │  LLM    │───▶│  Parse  │───▶│   Tool Execution        │ ││
│  │  │ Stream  │    │ Stream  │    │   (Concurrent)          │ ││
│  │  └─────────┘    └─────────┘    └─────────────────────────┘ ││
│  │                                           │                ││
│  │                                           ▼                ││
│  │  ◀──────────────────────────  Tool Results                 ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Services Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   LLM       │  │   Context   │  │       Tools             │  │
│  │  Client     │  │  Manager    │  │  (Bash/Read/Write/...)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Memory    │  │    Todo     │  │   Concurrent Executor   │  │
│  │  Manager    │  │  Reminder   │  │   & State Machine       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件说明

| 组件 | 文件 | 职责 |
|------|------|------|
| **REPL** | `repl.py` | 用户交互界面，处理输入输出 |
| **Agent** | `agent.py` | 核心循环，协调 LLM 调用和工具执行 |
| **LLM Client** | `llm_client.py` | 封装 Anthropic API，支持流式响应 |
| **Context** | `context.py` | 对话历史管理，三层压缩机制 |
| **Tools** | `tools/` | 工具实现：Bash、Read、Write、Todo 等 |
| **Executor** | `concurrent_executor.py` | 并发工具执行，支持互斥组 |
| **Memory** | `memory/` | 持久化记忆系统 |

### 数据流

```
User Input
    │
    ▼
REPL ────────────────────────────┐
    │                            │
    ▼                            │
Agent.run_stream()               │
    │                            │
    ├──▶ Context.add_user()    │
    │                            │
    ├──▶ LLM.complete_async_stream()
    │         │                │
    │         ▼                │
    │    Stream Chunks         │
    │    ├── Text ─────────────┼──▶ REPL Display
    │    └── Tool Use          │
    │         │                │
    │         ▼                │
    │    Executor.submit()     │
    │         │                │
    │         ▼                │
    │    Tool Execution        │
    │         │                │
    │         ▼                │
    │    Results ──────────────┼──▶ Context
    │                            │
    └──▶ CompleteEvent ────────┼──▶ REPL Display
```

---

## 与 Claude Code 的对比

### 相似之处

| 特性 | 本 Agent | Claude Code |
|------|----------|-------------|
| **架构** | 基于 Anthropic API 的 Agent 循环 | 相同 |
| **工具系统** | Bash、Read、Write、Ask、Todo 等 | 相似工具集 |
| **流式响应** | 支持实时输出 Token | 相同 |
| **上下文压缩** | 三层压缩机制 | 相似机制 |
| **并发工具** | 支持互斥组和并发执行 | 相同 |
| **持久化记忆** | 文件系统存储记忆 | 相似 |

### 已实现功能

1. **核心 Agent 循环** - LLM 调用 → 解析 → 工具执行 → 结果反馈
2. **工具系统**
   - Bash: 执行 shell 命令
   - Read: 读取文件
   - Write: 写入文件
   - Ask: 向用户提问
   - Todo: 任务管理
   - Confirm: 权限确认
3. **上下文管理** - 三层压缩：大内容卸载、工具结果摘要、全局压缩
4. **并发执行** - 支持工具互斥组和并发执行
5. **REPL 界面** - 交互式命令行界面
6. **记忆系统** - 持久化存储用户偏好和项目信息
7. **Todo 提醒** - 每隔 N 轮对话提醒待办事项
8. **日志系统** - 分级日志，支持 DEBUG/INFO/WARNING/ERROR

### 尚未开发的功能

| 功能 | Claude Code | 本 Agent | 优先级 |
|------|-------------|----------|--------|
| **IDE 集成** | 深度 VSCode/JetBrains 集成 | 仅命令行 | 高 |
| **Web 搜索** | 内置网页搜索工具 | 未实现 | 中 |
| **代码索引** | 项目级符号索引 | 未实现 | 中 |
| **MCP 支持** | Model Context Protocol | 未实现 | 中 |
| **Git 集成** | PR 创建、diff 查看 | 仅基础 bash | 中 |
| **多模态** | 图像输入支持 | 未实现 | 低 |
| **快捷键** | 丰富的键盘快捷键 | 无 | 低 |

### 架构差异对比

```
Claude Code Architecture:
┌─────────────────────────────────────────┐
│           VSCode Extension              │
│  ┌─────────────┐    ┌─────────────┐    │
│  │   Editor    │    │   Sidebar   │    │
│  │   Integration     │   Chat      │    │
│  └─────────────┘    └─────────────┘    │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│        Claude Code CLI Agent           │
│  ┌─────────────────────────────────┐   │
│  │     Enhanced Tool System        │   │
│  │  (Git, Web, Code Index, etc.)   │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│           MCP Servers                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │  Files  │ │  Git    │ │ Browser │  │
│  │  System │ │  Tools  │ │  Tools  │  │
│  └─────────┘ └─────────┘ └─────────┘  │
└─────────────────────────────────────────┘

This Agent Architecture:
┌─────────────────────────────────────────┐
│           REPL Interface                │
│  ┌─────────────┐    ┌─────────────┐    │
│  │  Terminal   │    │  Simple     │    │
│  │  Input      │    │  Output     │    │
│  └─────────────┘    └─────────────┘    │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│        Minimal Agent Core                │
│  ┌─────────────────────────────────┐   │
│  │     Basic Tool System           │   │
│  │  (Bash, Read, Write, Todo)      │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │     Context Compression         │   │
│  │     Memory System               │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│         Anthropic API                  │
│        (LLM Provider)                  │
└─────────────────────────────────────────┘
```

---

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 配置

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### 运行

```bash
python -m minimal_agent
```

---

## 许可证

MIT
