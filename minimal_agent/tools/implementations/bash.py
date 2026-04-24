"""Bash tool for executing shell commands with safety checks."""

import asyncio
import re
import shlex
from pathlib import Path
from ..base import Tool


class BashTool(Tool):
    """Tool for executing bash commands asynchronously with timeout and safety checks."""

    # Dangerous command patterns that modify files
    DANGEROUS_PATTERNS = [
        # Redirections (write/append)
        r'[12]?[\>\<]',  # > file, >> file, < file
        # Destructive commands
        r'\brm\b',          # remove
        r'\bmv\b',          # move/rename
        r'\bcp\b',          # copy (can overwrite)
        r'\bchmod\b',       # change permissions
        r'\bchown\b',       # change owner
        r'\bdd\b',          # disk write
        r'\bmkfs\b',        # format filesystem
    ]

    @property
    def name(self) -> str:
        """Return tool identifier."""
        return "bash"

    @property
    def description(self) -> str:
        """Return tool description for LLM."""
        return "Execute a bash command in the shell. Commands that modify files (rm, mv, >, etc.) will prompt for confirmation before execution."

    @property
    def parameters(self) -> dict:
        """Return JSON Schema for command and timeout parameters."""
        return {
            "command": {
                "type": "string",
                "description": "The bash command to execute"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 60)",
                "default": 60
            }
        }

    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command involves file modifications."""
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        return False

    def _extract_paths_from_command(self, command: str) -> list[Path]:
        """Extract potential file paths from a command."""
        paths = []

        # Pattern 1: Redirections (> file, >> file)
        redirect_pattern = r'[12]?>[>]?\s*(\S+)'
        for match in re.finditer(redirect_pattern, command):
            path_str = match.group(1)
            # Skip /dev/null and similar
            if not path_str.startswith('/dev/'):
                paths.append(Path(path_str))

        # Pattern 2: Arguments to dangerous commands (rm, mv, cp)
        try:
            tokens = shlex.split(command)
            dangerous_cmds = {'rm', 'mv', 'cp', 'chmod', 'chown'}

            i = 0
            while i < len(tokens):
                token = tokens[i]
                if token in dangerous_cmds or any(cmd in token for cmd in dangerous_cmds):
                    i += 1
                    while i < len(tokens):
                        arg = tokens[i]
                        if arg.startswith('-'):
                            i += 1
                            continue
                        if not arg.startswith('/dev/'):
                            paths.append(Path(arg))
                        i += 1
                    break
                i += 1
        except ValueError:
            pass

        return paths

    def _is_within_working_dir(self, path: Path) -> bool:
        """Check if path is within current working directory."""
        try:
            cwd = Path.cwd().resolve()
            target = path.resolve()
            target.relative_to(cwd)
            return True
        except (ValueError, FileNotFoundError):
            return False

    async def check_permission(self, **kwargs) -> dict | None:
        """Check if bash command requires user permission.

        Returns None if no permission needed, or a dict with permission request details.
        """
        command = kwargs.get("command", "")
        if not command:
            return None

        # Check 0: Is this a dangerous command?
        if not self._is_dangerous_command(command):
            return None  # Safe command, no permission needed

        # Dangerous command - check paths
        paths = self._extract_paths_from_command(command)
        warnings = []

        for path in paths:
            if path.exists():
                warnings.append(f"File '{path}' already exists and may be modified")
            if not self._is_within_working_dir(path):
                cwd = Path.cwd().resolve()
                warnings.append(f"Path '{path}' is outside working directory '{cwd}'")

        if warnings:
            return {
                "title": "Dangerous Command Warning",
                "message": f"This command may modify files:\n\n`{command}`\n\nWarnings:\n" + "\n".join(f"- {w}" for w in warnings) + "\n\nDo you want to proceed?",
                "severity": "danger"
            }

        # Dangerous but no specific path warnings
        return {
            "title": "Command Confirmation",
            "message": f"This command may modify files:\n\n`{command}`\n\nDo you want to proceed?",
            "severity": "warning"
        }

    async def execute(self, **kwargs) -> str:
        """Execute bash command with timeout, return stdout/stderr."""
        command = kwargs.get("command")
        timeout = kwargs.get("timeout", 60)

        if not command:
            return "Error: No command provided"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            result = []
            if stdout_str:
                result.append(f"STDOUT:\n{stdout_str}")
            if stderr_str:
                result.append(f"STDERR:\n{stderr_str}")
            if not result:
                result.append(f"Command completed with exit code: {process.returncode}")

            # Ensure transport is closed on Windows to avoid __del__ errors
            try:
                if process._transport and hasattr(process._transport, 'close'):
                    process._transport.close()
            except:
                pass

            return "\n\n".join(result)

        except asyncio.TimeoutError:
            try:
                process.kill()
                await process.wait()
            except:
                pass
            finally:
                # Ensure transport is closed on Windows
                try:
                    if process._transport and hasattr(process._transport, 'close'):
                        process._transport.close()
                except:
                    pass
            return f"Error: Command timed out after {timeout} seconds"

        except Exception as e:
            return f"Error executing command: {str(e)}"
