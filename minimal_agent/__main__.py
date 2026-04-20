"""Main entry point with pre-flight checks."""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use absolute import from minimal_agent package
try:
    from minimal_agent.check_installation import run_preflight_checks
except ImportError:
    # Fallback: import directly if running as script
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "check_installation",
        os.path.join(os.path.dirname(__file__), "check_installation.py")
    )
    check_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check_mod)
    run_preflight_checks = check_mod.run_preflight_checks


async def main():
    """Main entry point."""
    from dotenv import load_dotenv
    from minimal_agent.agent import Agent
    from minimal_agent.llm_client import LLMClient
    from minimal_agent.context import Context
    from minimal_agent.repl import REPL
    from minimal_agent.tools.base import ToolRegistry
    from minimal_agent.tools.implementations.bash import BashTool
    from minimal_agent.tools.implementations.read import ReadTool
    from minimal_agent.tools.implementations.write import WriteTool
    from minimal_agent.tools.implementations.ask_user import AskUserQuestionTool
    from minimal_agent.tools.implementations.todoWrite import TodoWriteTool

    # Load environment
    load_dotenv()

    # Run pre-flight checks
    if not run_preflight_checks():
        return 1

    # Show configuration
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    model = os.getenv("ANTHROPIC_MODEL")

    print("Configuration:")
    if auth_token:
        print(f"  - Auth: ANTHROPIC_AUTH_TOKEN (***{auth_token[-4:]})")
    else:
        print(f"  - Auth: ANTHROPIC_API_KEY (***{api_key[-4:]})")
    if base_url:
        print(f"  - Base URL: {base_url}")
    if model:
        print(f"  - Model: {model}")
    print()

    try:
        # Initialize components
        llm_client = LLMClient()
        print("✓ LLM client initialized")

        # Register tools
        tools = ToolRegistry()
        tools.register(BashTool())
        tools.register(ReadTool())
        tools.register(WriteTool())
        tools.register(AskUserQuestionTool())
        tools.register(TodoWriteTool())
        print("✓ Tools registered")

        # Create context
        context = Context(
            tools=tools,
            llm_client=llm_client,
            model_name=llm_client.model
        )
        print("✓ Context initialized")

        # Create agent
        agent = Agent(
            llm_client=llm_client,
            context=context,
            tools=tools
        )
        print("✓ Agent initialized")
        print()

        # Run REPL
        repl = REPL(agent)
        await repl.run()

    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
