<div align="center">

# 🤖 Minimal Agent

**A lightweight, Claude Code-inspired Agent implementation in Python**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Anthropic API](https://img.shields.io/badge/Anthropic-API-orange.svg)](https://www.anthropic.com/api)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

*Built with streaming responses · Concurrent tool execution · Smart context compression*

</div>

---

🌐 **English** | [中文](README-zh.md)

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [📖 Detailed Usage](#-detailed-usage)
- [🏗️ Architecture](#️-architecture)
- [🔧 Configuration](#-configuration)
- [🛠️ Tool System](#️-tool-system)
- [🧠 Context & Memory](#-context--memory)
- [📊 Comparison with Claude Code](#-comparison-with-claude-code)
- [🗺️ Roadmap](#️-roadmap)
- [🤝 Contributing](#-contributing)

---

## ✨ Features

### Core Capabilities

| Feature | Description | Status |
|---------|-------------|--------|
| 🔄 **Agent Loop** | Automatic LLM → Tool → Result iteration | ✅ Ready |
| ⚡ **Streaming** | Real-time token-by-token output | ✅ Ready |
| 🛠️ **Tools** | Bash, Read, Write, Web Search, Ask, Todo | ✅ Ready |
| 🏃 **Concurrency** | Parallel tool execution with mutex groups | ✅ Ready |
| 🌐 **Web Search** | Bing + DuckDuckGo, no API key needed | ✅ Ready |
| 📦 **Context Compression** | Three-layer smart compression | ✅ Ready |
| 💾 **Memory** | Persistent user/project/reference storage | ✅ Ready |
| 📋 **Todo Reminder** | Periodic task list reminders | ✅ Ready |
| 📝 **Logging** | Python logging module, file-only output | ✅ Ready |

### Code Quality

- 🎯 **Type Hints**: Full type annotation coverage
- 🧪 **Async/Await**: Modern async patterns throughout
- 📐 **Modular Design**: Clean separation of concerns
- 🔒 **Error Handling**: Graceful failure recovery

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- An Anthropic API key

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd minimal_agent

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Required: Set your API key
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"

# Optional: Choose model (default: claude-3-5-haiku-20241022)
export ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"
```

### Run

```bash
python -m minimal_agent
```

You'll see the welcome banner:

```
╭──────────────────────────────────────────────────────────────╮
│                                                              │
│   ██╗  ██╗██╗  ██╗██╗    ██╗   █████╗  ██████╗ ████████╗     │
│   ╚██╗██╔╝╚██╗██╔╝██║    ██║  ██╔══██╗██╔════╝ ╚══██╔══╝     │
│    ╚███╔╝  ╚███╔╝ ██║ █╗ ██║  ███████║██║  ███╗   ██║        │
│    ██╔██╗  ██╔██╗ ██║███╗██║  ██╔══██║██║   ██║   ██║        │
│   ██╔╝ ██╗██╔╝ ██╗╚███╔███╔╝  ██║  ██║╚██████╔╝   ██║        │
│   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝   ╚═╝  ╚═╝ ╚═════╝    ╚═╝        │
│                                                              │
│              Ready to help you with anything                 │
│                                                              │
╰──────────────────────────────────────────────────────────────╯

Type your message below (or 'exit' to quit)
```

---

## 📖 Detailed Usage

### Interactive Session

```
User: Read the README.md file

🤖 I'll read the README.md file for you.

  ✅ Read completed

The file contains documentation for a minimal Claude Code-style agent...

User: What files are in the current directory?

🤖 Let me check the directory structure.

  ✅ Bash completed

Files:
- README.md
- requirements.txt
- minimal_agent/
  - agent.py
  - llm_client.py
  - ...

User: exit

👋 Goodbye!
```

### Log Files

All logs are written to files in the `logs/` directory — nothing prints to the console:

| Log File | Source | Content |
|----------|--------|---------|
| `logs/agent.log` | Agent diagnostics (`debug/info/warning/error`) | Loop iterations, tool calls, stream events |
| `logs/session_*.log` | Conversation logger | Full dialogue history with tool results |

The session log filename includes a timestamp suffix, e.g. `session_20260505_174007.log`.

---

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER LAYER                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────┐  │
│  │   Input     │    │   Output    │    │   Interactive Dialogs       │  │
│  │   (Text)    │◀──▶│  (Stream)   │    │   (Confirm/Ask/Progress)    │  │
│  └─────────────┘    └─────────────┘    └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           AGENT CORE LAYER                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         Main Event Loop                         │   │
│  │                                                                 │   │
│  │   ┌──────────┐     ┌──────────┐     ┌──────────────────────┐   │   │
│  │   │  User    │────▶│  Context │────▶│  LLM.complete_       │   │   │
│  │   │  Message │     │  .add()  │     │  async_stream()      │   │   │
│  │   └──────────┘     └──────────┘     └──────────────────────┘   │   │
│  │                                                │                │   │
│  │                                                ▼                │   │
│  │                              ┌────────────────────────┐         │   │
│  │                              │    Stream Processor    │         │   │
│  │                              │  ┌──────────────────┐  │         │   │
│  │                              │  │ Text Chunks      │──┼──┬──────┘   │
│  │                              │  │  └─▶ TokenEvent  │  │  │          │
│  │                              │  │                  │  │  │          │
│  │                              │  │ Tool Use Blocks  │──┼──┤          │
│  │                              │  │  └─▶ Submit to   │  │  │          │
│  │                              │  │     Executor     │──┼──┤          │
│  │                              │  └──────────────────┘  │  │          │
│  │                              └────────────────────────┘  │          │
│  │                                                         │          │
│  │                              ┌────────────────────────┐  │          │
│  │                              │  Concurrent Executor   │◀─┘          │
│  │                              │  ┌──────────────────┐  │             │
│  │                              │  │ State Machine    │  │             │
│  │                              │  │ ┌──┐ ┌──┐ ┌──┐  │  │             │
│  │                              │  │ │W │─▶│R │─▶│C │  │  │             │
│  │                              │  │ │A │ │U │ │O │  │  │             │
│  │                              │  │ │I │ │N │ │M │  │  │             │
│  │                              │  │ │T │ │N │ │P │  │  │             │
│  │                              │  │ └──┘ │I │ │L │  │  │             │
│  │                              │  │      │N │ │E │  │  │             │
│  │                              │  │      │G │ │T │  │  │             │
│  │                              │  │      └──┘ │E │  │  │             │
│  │                              │  │           └──┘  │  │             │
│  │                              │  │   Mutex Groups   │  │             │
│  │                              │  │   (read/write)   │  │             │
│  │                              │  └──────────────────┘  │             │
│  │                              └────────────────────────┘             │
│  │                                         │                          │
│  │                                         ▼                          │
│  │   ◀───────────────────────────────────  Results                     │
│  │                                         │                          │
│  │                                         ▼                          │
│  │                              ┌────────────────────────┐             │
│  │                              │  Tool Result Handler   │             │
│  │                              │  ──▶ Context.add_tool  │             │
│  │                              └────────────────────────┘             │
│  │                                         │                          │
│  │                                         ▼                          │
│  │   ═══════════════════════════════════════════════════════════════  │
│  │                    Next Loop Iteration (if tools called)           │
│  │   ═══════════════════════════════════════════════════════════════  │
│  │                                         │                          │
│  │                                         ▼                          │
│  │                              ┌────────────────────────┐             │
│  │                              │   CompleteEvent        │────────────┼──▶ Final Output
│  │                              │   (No more tools)      │            │
│  │                              └────────────────────────┘            │
│  │                                                                    │
│  └────────────────────────────────────────────────────────────────────┘
│
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │   Config    │  │    Todo     │  │   Logger    │  │   Events    │   │
│  │   Module    │  │  Reminder   │  │   System    │  │   Queue     │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SERVICE LAYER                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │    LLM      │  │   Context   │  │    Tool     │  │   Memory    │    │
│  │   Client    │  │   Manager   │  │   Registry  │  │   Manager   │    │
│  │             │  │             │  │             │  │             │    │
│  │ • Stream    │  │ • Messages  │  │ • Execution │  │ • Load/Save │    │
│  │ • Non-stream│  │ • Compress  │  │ • Registry  │  │ • Index     │    │
│  │ • Async     │  │ • 3 Layers  │  │ • Schemas   │  │ • Search    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Anthropic Messages API                       │   │
│  │         (Claude 3.5 Haiku / Sonnet / Opus Models)               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Agent Core (`agent.py`)

The heart of the system. Manages the conversation loop and coordinates all components.

```python
async def run_stream(self, user_input: str):
    """Main event loop with streaming support."""
    self.context.add_user(user_input)

    while True:
        # 1. Check todo reminder
        # 2. Apply context compression (3 layers)
        # 3. Start LLM stream
        # 4. Process stream (text + tool_use)
        # 5. Wait for tool completion
        # 6. If tools were called, loop again
        # 7. If no tools, return CompleteEvent
```

**Key Features:**
- **Streaming**: Yields `TokenEvent` for real-time display
- **Concurrency**: Tools run in parallel with mutex group coordination
- **Iteration**: Automatically loops when tool results need processing
- **State**: Tracks executor for permission/question resolution

#### 2. Context Manager (`context.py`)

Manages conversation history with intelligent compression.

**Three-Layer Compression:**

| Layer | Trigger | Action |
|-------|---------|--------|
| **Layer 1** | Individual result > 100KB | Offload to file (`.agent_context/offload/`) |
| **Layer 2** | Total tool results > 500KB | Summarize old results with LLM |
| **Layer 3** | Total context > 93% of limit | Global summarization, keep last 4 messages |

```
Context Flow:

User Message ──▶ Messages List ──▶ Compression ──▶ LLM API
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
              ┌─────────┐          ┌─────────────┐        ┌─────────────┐
              │ Layer 1 │          │   Layer 2   │        │   Layer 3   │
              │ offload │          │ microcompact│        │  autocompact│
              │ (100KB) │          │  (500KB)    │        │   (93%)     │
              └─────────┘          └─────────────┘        └─────────────┘
```

#### 3. Concurrent Executor (`concurrent_executor.py`)

Manages parallel tool execution with state machine.

**States:**
```
┌────────┐    ┌────────┐    ┌────────┐
│ WAITING│───▶│ RUNNING│───▶│COMPLETE│
└────────┘    └────────┘    └────────┘
     │                              │
     └────────▶ FAILED ◀────────────┘
```

**Mutex Groups:**
- `read` group: Multiple reads can run concurrently
- `write` group: Writes are exclusive
- `bash` group: Reads wait for writes to complete

#### 4. Tool System (`tools/`)

Extensible tool framework with base class.

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    async def execute(self, **kwargs) -> str: ...

    async def check_permission(self, **kwargs) -> dict | None: ...
```

**Built-in Tools:**

| Tool | Purpose | Mutex Group |
|------|---------|-------------|
| `bash` | Execute shell commands | bash |
| `read` | Read file contents | read |
| `write` | Write/modify files | write |
| `web_search` | Search the web (Bing + DuckDuckGo) | - |
| `ask_user` | Ask user questions | - |
| `todo_write` | Manage task lists | - |

#### 5. Memory System (`memory/`)

Persistent storage for cross-conversation context.

**Memory Types:**

| Type | File | Use Case |
|------|------|----------|
| `user` | USER.md | User preferences, role, knowledge |
| `feedback` | FEEDBACK.md | Guidance on what to do/avoid |
| `project` | PROJECT.md | Deadlines, constraints, ongoing work |
| `reference` | REFERENCE.md | External resource pointers |

**Storage:**
- Directory: `.xxw_memory/`
- Format: Markdown with YAML frontmatter
- Index: `MEMORY.md` (auto-generated)

#### 6. Todo Reminder System

Integrated with `todo_write` tool to periodically remind about tasks.

```
Every 3 conversation rounds (configurable):

┌─────────────┐
│  Counter    │──────▶ Counter == 3? ──▶ Yes ──▶ Format todo list
│  Increment  │                              │        (filter completed)
└─────────────┘                              ▼
                                      ┌─────────────┐
                                      │ Add reminder│──▶ Context.add_user()
                                      │ to context  │
                                      └─────────────┘
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | - | ✅ Yes |
| `ANTHROPIC_AUTH_TOKEN` | Alternative auth token | - | ❌ No |
| `ANTHROPIC_BASE_URL` | API base URL (for proxies) | - | ❌ No |
| `ANTHROPIC_MODEL` | Model identifier | `claude-3-5-haiku-20241022` | ❌ No |

### Config Module (`config.py`)

```python
@dataclass
class AgentConfig:
    todo_reminder_interval: int = 3        # Rounds between reminders
    context_threshold_ratio: float = 0.93   # Compression trigger
    offload_threshold: int = 100000         # Bytes
    tool_results_total_limit: int = 500000  # Bytes
    max_tokens: int = 8000                  # Context limit
```

---

## 🛠️ Tool System

### Tool Execution Flow

```
┌─────────────┐
│  Tool Use   │
│   Block     │
│  in Stream  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ check_permission│──▶ Needs permission? ──▶ Yes ──▶ Show dialog
│   (async)       │                              │
└──────┬──────────┘                              ▼
       │                                ┌─────────────────┐
       │ No                             │ Wait for user │
       │                                │   response    │
       ▼                                └───────┬─────────┘
┌─────────────────┐                            │
│    execute()    │◀───────────────────────────┘
│    (async)      │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Return Result  │
│   or Error      │
└─────────────────┘
```

### Tool Implementation Example

```python
from minimal_agent.tools.base import Tool

class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Does something useful"

    @property
    def parameters(self) -> dict:
        return {
            "arg1": {
                "type": "string",
                "description": "First argument"
            }
        }

    async def execute(self, **kwargs) -> str:
        arg1 = kwargs.get("arg1", "")
        return f"Processed: {arg1}"
```

### Registering Tools

```python
# In __main__.py
tools.register(MyTool())
```

---

## 🧠 Context & Memory

### Context Compression Details

**Layer 1: Big Content Offloading**

```python
if len(tool_content) > 100_000:  # 100KB
    save_to_file(f"{tool_call_id}.json", content)
    replace_with = f"[Content saved to {path}, {len} chars]"
```

**Layer 2: Tool Result Budget**

```python
if total_tool_results > 500_000:  # 500KB
    for old_result in oldest_results_except_last_4:
        summary = llm_summarize(old_result, max_words=50)
        replace_with = f"[Summary] {summary}"
```

**Layer 3: Global Auto-compact**

```python
if total_context > 0.93 * model_limit:
    summary = llm_summarize(all_conversation)
    system_prompt += f"\n\n=== History Summary ===\n{summary}"
    messages = messages[-4:]  # Keep last 2 exchanges
```

### Memory System Usage

```python
# Automatically loaded at agent startup
memory_manager = MemoryManager()
memory_context = memory_manager.get_memory_context()
# Injected into system prompt
```

Memory files (`.xxw_memory/`):

```markdown
---
name: User Preferences
description: User likes terse responses
type: user
---

Prefer short, direct answers without unnecessary explanations.
```

---

## 📊 Comparison with Claude Code

### Similarities ✅

| Aspect | This Agent | Claude Code |
|--------|-----------|-------------|
| **Architecture** | Agent loop with tool use | ✅ Same |
| **LLM Provider** | Anthropic API | ✅ Same |
| **Streaming** | Real-time token output | ✅ Same |
| **Tool Pattern** | LLM chooses → Agent executes | ✅ Same |
| **Context Window** | Smart compression | ✅ Similar |
| **Async Design** | Concurrent tool execution | ✅ Same |
| **State Machine** | WAITING → RUNNING → COMPLETE | ✅ Same |

### Differences ⚠️

| Aspect | This Agent | Claude Code |
|--------|-----------|-------------|
| **Interface** | Terminal REPL | Deep IDE integration |
| **Tool Count** | 6 basic tools | 15+ advanced tools |
| **Git Support** | Via bash only | Native PR/diff/branch |
| **Web Search** | ✅ Bing + DuckDuckGo | ✅ Built-in |
| **Code Index** | ❌ Not implemented | ✅ Project-wide symbols |
| **MCP** | ❌ Not implemented | ✅ MCP servers |
| **Shortcuts** | ❌ None | ✅ Rich keybindings |
| **Testing** | ❌ No built-in tests | ✅ Test runner |
| **Multi-file** | Basic | Advanced multi-file edits |

### Architecture Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE (Reference)                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    VSCode Extension                      │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │   │
│  │  │   Editor   │  │   Panel    │  │   Inline Diff      │ │   │
│  │  │   Widgets  │  │   Chat     │  │   Decorations      │ │   │
│  │  └────────────┘  └────────────┘  └────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               Claude Code CLI / Daemon                   │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │         Enhanced Tool System                      │  │   │
│  │  │  ┌───────┐ ┌───────┐ ┌────────┐ ┌──────────┐     │  │   │
│  │  │  │  Git  │ │  Web  │ │ Search │ │ Terminal │     │  │   │
│  │  │  │ Tools │ │ Tools │ │ Tools  │ │  Tools   │     │  │   │
│  │  │  └───────┘ └───────┘ └────────┘ └──────────┘     │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Model Context Protocol (MCP)                │   │
│  │         ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐         │   │
│  │         │Server1│ │Server2│ │Server3│ │Server4│         │   │
│  │         └───────┘ └───────┘ └───────┘ └───────┘         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  THIS AGENT (Implementation)                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Terminal REPL                          │   │
│  │  ┌────────────────────┐  ┌────────────────────────────┐ │   │
│  │  │   Simple Input     │  │   Stream Output            │ │   │
│  │  │   (prompt_toolkit) │  │   (print)                  │ │   │
│  │  └────────────────────┘  └────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Minimal Agent Core                       │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │         Basic Tool System                         │  │   │
│  │  │  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐         │  │   │
│  │  │  │  Read │ │ Write │ │  Bash │ │  Todo │         │  │   │
│  │  │  └───────┘ └───────┘ └───────┘ └───────┘         │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │       Context Compression + Memory                │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Direct Anthropic API Call                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗺️ Roadmap

### Phase 1: Core Stability ✅
- [x] Basic agent loop
- [x] Streaming support
- [x] Tool system
- [x] Context compression
- [x] Concurrent execution

### Phase 2: Enhanced Tools 🚧
- [ ] Git integration (status, diff, commit)
- [x] Web search tool
- [ ] Multi-file editing
- [ ] Code search/index

### Phase 3: Advanced Features 📋
- [ ] MCP (Model Context Protocol) support
- [ ] Test runner integration
- [ ] Code analysis/linting
- [ ] Project scaffolding

### Phase 4: IDE Integration 📋
- [ ] VSCode extension
- [ ] Language server protocol
- [ ] Inline suggestions
- [ ] Rich UI components

---

## 🤝 Contributing

### Project Structure

```
minimal_agent/
├── __init__.py              # Package exports
├── __main__.py              # Entry point
├── agent.py                 # Core agent loop ⭐
├── config.py                # Global configuration
├── context.py               # Context & compression ⭐
├── events.py                # Event types
├── llm_client.py            # Anthropic API client
├── log.py                   # Logging (agent + conversation)
├── repl.py                  # REPL interface ⭐
├── check_installation.py    # Setup verification
│
├── memory/                  # Persistence layer
│   ├── __init__.py
│   ├── manager.py           # Memory management
│   └── types.py             # Type definitions
│
├── tools/                   # Tool system
│   ├── __init__.py
│   ├── base.py              # Tool base class ⭐
│   ├── concurrent_executor.py  # Parallel execution ⭐
│   ├── state_manager.py     # Execution state machine
│   └── implementations/     # Concrete tools
│       ├── ask_user.py
│       ├── bash.py
│       ├── confirm.py
│       ├── read.py
│       ├── todoWrite.py     ⭐
│       ├── web_search.py    ⭐
│       └── write.py
│
└── .xxw_memory/             # Created at runtime
    ├── MEMORY.md            # Auto-generated index
    ├── USER.md              # User memories
    ├── FEEDBACK.md          # Feedback memories
    ├── PROJECT.md           # Project memories
    └── REFERENCE.md         # Reference memories
```

### Key Files for Understanding

1. **`agent.py`** - Start here for the main loop
2. **`context.py`** - Context compression logic
3. **`tools/base.py`** - Tool interface
4. **`tools/concurrent_executor.py`** - Concurrency model

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ using Python and Anthropic API**

</div>
