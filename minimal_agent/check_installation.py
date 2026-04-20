#!/usr/bin/env python3
"""Check if the agent is properly set up."""

import sys
import os


def check_python_version():
    """Check Python version."""
    print(f"✓ Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    if sys.version_info < (3, 10):
        print("✗ Python 3.10+ required")
        return False
    return True


def check_dependencies():
    """Check if dependencies are installed."""
    dependencies = [
        ("anthropic", "anthropic>=0.21.0", "pip install anthropic>=0.21.0"),
        ("prompt_toolkit", "prompt-toolkit>=3.0.0", "pip install prompt-toolkit>=3.0.0"),
        ("dotenv", "python-dotenv>=1.0.0", "pip install python-dotenv>=1.0.0"),
    ]

    all_ok = True
    for module, package, install_cmd in dependencies:
        try:
            __import__(module)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} not installed")
            print(f"  Run: {install_cmd}")
            all_ok = False

    return all_ok


def check_api_credentials():
    """Check if API credentials are set."""
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if auth_token:
        print(f"✓ ANTHROPIC_AUTH_TOKEN is set (starts with: {auth_token[:8]}...)")
        return True
    elif api_key:
        print(f"✓ ANTHROPIC_API_KEY is set (starts with: {api_key[:8]}...)")
        return True
    else:
        print("✗ No API credentials found")
        print("  Set one of the following:")
        print("    export ANTHROPIC_API_KEY='your-key'")
        print("    export ANTHROPIC_AUTH_TOKEN='your-token'")
        print("  Or create a .env file with these variables")
        return False


def check_env_file():
    """Check if .env file exists."""
    if os.path.exists(".env"):
        print("✓ .env file found")
        # Try to load it
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✓ .env file loaded successfully")
            return True
        except Exception as e:
            print(f"⚠ .env file exists but could not be loaded: {e}")
            return True  # Still return True as it's not fatal
    else:
        print("⚠ .env file not found (optional, you can create one for API credentials)")
        return True


def check_core_files():
    """Check if all required core files exist."""
    required_files = [
        # Core agent files
        "minimal_agent/__init__.py",
        "minimal_agent/__main__.py",
        "minimal_agent/agent.py",
        "minimal_agent/llm_client.py",
        "minimal_agent/context.py",
        "minimal_agent/repl.py",
        "minimal_agent/events.py",

        # Tools base
        "minimal_agent/tools/__init__.py",
        "minimal_agent/tools/base.py",
        "minimal_agent/tools/state_manager.py",
        "minimal_agent/tools/concurrent_executor.py",

        # Tool implementations
        "minimal_agent/tools/implementations/__init__.py",
        "minimal_agent/tools/implementations/bash.py",
        "minimal_agent/tools/implementations/read.py",
        "minimal_agent/tools/implementations/write.py",
        "minimal_agent/tools/implementations/ask_user.py",
        "minimal_agent/tools/implementations/todoWrite.py",
        "minimal_agent/tools/implementations/confirm.py",

        # Memory system
        "minimal_agent/memory/__init__.py",
        "minimal_agent/memory/manager.py",
        "minimal_agent/memory/types.py",
    ]

    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file}")
        else:
            print(f"✗ {file} missing")
            all_exist = False

    return all_exist


def check_module_imports():
    """Check if core modules can be imported."""
    modules_to_check = [
        "minimal_agent",
        "minimal_agent.agent",
        "minimal_agent.llm_client",
        "minimal_agent.context",
        "minimal_agent.repl",
        "minimal_agent.events",
        "minimal_agent.tools.base",
        "minimal_agent.tools.state_manager",
        "minimal_agent.tools.concurrent_executor",
    ]

    all_ok = True
    for module in modules_to_check:
        try:
            __import__(module)
            print(f"✓ {module}")
        except Exception as e:
            print(f"✗ {module} import failed: {e}")
            all_ok = False

    return all_ok


def check_working_directory():
    """Check working directory."""
    cwd = os.getcwd()
    print(f"✓ Working directory: {cwd}")

    # Check if we're in the right place
    if os.path.exists("minimal_agent/__main__.py"):
        print("✓ Project structure looks correct")
        return True
    else:
        print("⚠ Warning: minimal_agent/__main__.py not found in current directory")
        print("  Make sure you're running this from the project root")
        return True  # Warning only, not fatal


def run_preflight_checks(silent=False):
    """Run minimal pre-flight checks before starting the agent.

    Args:
        silent: If True, only print errors. If False, print all check results.

    Returns:
        True if all critical checks passed, False otherwise.
    """
    import sys
    import os
    from pathlib import Path

    all_passed = True
    errors = []

    # Check Python version
    if sys.version_info < (3, 10):
        errors.append("Python 3.10+ required")
        all_passed = False
    elif not silent:
        print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    # Check dependencies
    deps = ["anthropic", "prompt_toolkit", "dotenv"]
    for dep in deps:
        try:
            __import__(dep)
            if not silent:
                print(f"✓ {dep}")
        except ImportError:
            errors.append(f"{dep} not installed. Run: pip install -r requirements.txt")
            all_passed = False

    # Check API credentials
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not auth_token and not api_key:
        errors.append("No API credentials found. Set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN")
        all_passed = False
    elif not silent:
        if auth_token:
            print(f"✓ ANTHROPIC_AUTH_TOKEN (***{auth_token[-4:]})")
        else:
            print(f"✓ ANTHROPIC_API_KEY (***{api_key[-4:]})")

    # Check core files exist
    critical_files = [
        "minimal_agent/__main__.py",
        "minimal_agent/agent.py",
        "minimal_agent/llm_client.py",
        "minimal_agent/context.py",
    ]
    for file in critical_files:
        if not Path(file).exists():
            errors.append(f"Critical file missing: {file}")
            all_passed = False
        elif not silent:
            print(f"✓ {file}")

    # Print errors if any
    if errors:
        print("\n".join(errors))

    return all_passed


def main():
    """Run all checks."""
    print("=" * 60)
    print("Checking Agent Installation")
    print("=" * 60)
    print()

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Working Directory", check_working_directory),
        (".env File", check_env_file),
        ("API Credentials", check_api_credentials),
        ("Core Files", check_core_files),
        ("Module Imports", check_module_imports),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        print("-" * 60)
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print("✓ All checks passed! You can run the agent with:")
        print("  python -m minimal_agent")
        print()
        print("Or use the check script for diagnostics:")
        print("  python check_installation.py")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        print()
        print("Common fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Set API credentials in .env file or environment variables")
        print("  3. Make sure you're running from the project root directory")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
