from langchain_core.tools import tool
import os
from pathlib import Path
from config.settings import settings
import sys
import subprocess
import shlex
import json
from datetime import datetime, timezone
import time



def _append_shell_audit(record: dict) -> None:
    try:
        settings.shellAuditLogPath.parent.mkdir(parents=True, exist_ok=True)
        with open(settings.shellAuditLogPath, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # Audit logging should never crash the tool call.
        pass


def _extract_primary_command(command: str) -> str:
    try:
        tokens = shlex.split(command, posix=False)
        if not tokens:
            return ""
        return tokens[0].strip().strip('"').strip("'")
    except Exception:
        return (command or "").strip().split(" ")[0].strip().strip('"').strip("'")


def _contains_denied_pattern(command: str) -> str:
    normalized = f" {(command or '').lower()} "
    for pattern in settings.shellDeniedPatterns:
        if pattern.lower() in normalized:
            return pattern
    return ""


def _resolve_cwd(working_directory: str) -> Path:
    if not working_directory:
        return settings.shellSandboxRoot

    candidate = Path(working_directory)
    if not candidate.is_absolute():
        candidate = settings.shellSandboxRoot / candidate
    return candidate.resolve()


def _is_inside_sandbox(path: Path, sandbox_root: Path) -> bool:
    try:
        path.resolve().relative_to(sandbox_root.resolve())
        return True
    except Exception:
        return False


@tool
def readFile(filePath: str) -> str:
    '''
    This function reads a file and returns the content of the file.
    You can use it to read the content of a file. 

    Args:
        filePath (str): The path to the file to read.
    Returns:
        str: The content of the file.
    '''
    try:
        with open(filePath, 'r') as file:
            return file.read()
    except Exception as e:
        return f"Error happens in reading the file: {str(e)}"


@tool
def writeFile(filePath: str, content: str) -> str:
    '''
    Write text content to a file at the specified path.

    CRITICAL NOTES:
    1. This operation will OVERWRITE any existing file at `filePath`.
    2. Ensure the path is correct.
    3. If the file is written successfully, DO NOT write it again unless you need to correct errors.

    Args:
        filePath (str): The path to the file to write to.
        content (str): The content to write to the file.
    Returns:
        str: A confirmation message if the file is written successfully, or an error message otherwise.
    '''
    try:
        with open(filePath, 'w') as file:
            file.write(content)
        return f"The file '{filePath}' was written successfully."
    except Exception as e:
        return f"Error happens in writing the file: {str(e)}"


@tool
def runShellCommand(command: str, workingDirectory: str = "") -> str:
    '''
    This function runs a shell command and returns the output of the command.

    Security hardening in this tool:
    - command allowlist (configurable)
    - command denylist patterns (configurable)
    - sandboxed working directory (configurable)
    - audit logging for approved/blocked commands

    Human approval flow is unchanged and still handled by middleware at the agent layer.

    Args:
        command (str): The command to run.
        workingDirectory (str): Optional working directory (relative to sandbox root if not absolute).
    Returns:
        str: The output of the command.
    '''
    start = time.perf_counter()
    now = datetime.now(timezone.utc).isoformat()

    if not command or not command.strip():
        return "Error: command cannot be empty."

    sandbox_root = settings.shellSandboxRoot
    cwd = _resolve_cwd(workingDirectory)
    primary = _extract_primary_command(command)

    audit = {
        "timestamp_utc": now,
        "command": command,
        "primary_command": primary,
        "working_directory": str(cwd),
        "sandbox_root": str(sandbox_root),
        "allowed": False,
        "reason": "",
        "returncode": None,
        "duration_ms": None,
    }

    denied = _contains_denied_pattern(command)
    if denied:
        audit["reason"] = f"Blocked by denylist pattern: {denied}"
        audit["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        _append_shell_audit(audit)
        return f"Error: command blocked by denylist pattern '{denied}'."

    if settings.shellRequireAllowlist:
        allowed = {item.lower() for item in settings.shellAllowedCommands}
        if not primary or primary.lower() not in allowed:
            audit["reason"] = f"Primary command '{primary}' is not in allowlist."
            audit["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
            _append_shell_audit(audit)
            return (
                f"Error: command '{primary}' is not allowlisted. "
                "Update SHELL_ALLOWED_COMMANDS in .env if this command is needed."
            )

    if settings.shellEnforceSandbox:
        if not _is_inside_sandbox(cwd, sandbox_root):
            audit["reason"] = "Working directory escapes sandbox root."
            audit["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
            _append_shell_audit(audit)
            return "Error: working directory is outside the configured sandbox root."

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=30,
        )

        audit["allowed"] = True
        audit["returncode"] = result.returncode
        audit["reason"] = "executed"
        audit["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        _append_shell_audit(audit)

        output = f"The command '{command}' was executed"
        if result.returncode == 0:
            output += f" successfully with output:\n{result.stdout}"
        else:
            output += f" with error:\n{result.stderr}"
        return output
    except Exception as e:
        audit["reason"] = f"execution exception: {str(e)}"
        audit["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        _append_shell_audit(audit)
        return f"Error happens in running the command: {str(e)}"


@tool
def systemInfo() -> str:
    '''
    This function returns the system information.
    You can use it to get the system information.
    Args:
        None
    Returns:
        str: The system information.
    '''
    try:
        return f"The system information is: {sys.platform}"
    except Exception as e:
        return f"Error happens in getting the system information: {str(e)}"
