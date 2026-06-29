#!/usr/bin/env python3
"""Safety utilities for Humitron - path validation and command filtering."""

import re
from pathlib import Path
from typing import Tuple, List
from humitron.config.loader import get_config

# Patterns that are NEVER allowed - these can destroy systems
DANGEROUS_PATTERNS: List[str] = [
    r"rm\s+-rf\s+/",           # rm -rf /
    r"rm\s+-rf\s+\*",          # rm -rf *
    r"sudo\s+",                # sudo anything
    r"chmod\s+777",            # chmod 777
    r"dd\s+if=",               # dd if= (disk destroyer)
    r"mkfs\s+",                # mkfs (format filesystem)
    r":\(\)\s*\{\s*:\|\:&\s*\}\s*;\s*:",  # fork bomb :(){ :|:& };:
    r"shutdown",               # shutdown
    r"reboot",                 # reboot
    r"halt",                   # halt
    r"poweroff",               # poweroff
    r">\s*/dev/",              # redirect to device
    r"chown\s+-R\s+root",      # chown -R root
    r"chgrp\s+-R\s+root",      # chgrp -R root
]

# Commands that are allowed but with restrictions
ALLOWED_COMMANDS: List[str] = [
    "ls", "cat", "head", "tail", "grep", "find", "wc", "echo",
    "pwd", "mkdir", "touch", "cp", "mv", "rm",  # rm without -rf /
    "python", "python3", "pip", "npm", "node",
    "git", "curl", "wget", "tar", "gzip", "gunzip",
    "cd", "which", "whereis", "man", "info",
]

# Compile dangerous patterns for performance
DANGEROUS_REGEX = [re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS]


def is_path_in_workspace(path: Path) -> bool:
    """Check if a path is within the workspace directory.

    Args:
        path: Path to check.

    Returns:
        True if path is within workspace, False otherwise.
    """
    try:
        workspace = Path(get_config().workspace_path).resolve()
        resolved = path.resolve()
        return str(resolved).startswith(str(workspace))
    except Exception:
        return False


def is_command_dangerous(command: str) -> Tuple[bool, str]:
    """Check if a command contains dangerous patterns.

    Args:
        command: Command string to check.

    Returns:
        Tuple of (is_dangerous, reason). Reason is empty if not dangerous.
    """
    command = command.strip()

    # Check each dangerous pattern
    for pattern in DANGEROUS_REGEX:
        if pattern.search(command):
            return True, "Command blocked for security reasons: matches dangerous pattern"

    # Additional check: rm -rf on root or home
    if re.search(r"rm\s+-rf\s+(/|~|\$HOME|\.)", command):
        return True, "Command blocked for security reasons: rm -rf on sensitive paths"

    # Check for command chaining that could hide dangerous commands
    if "&&" in command or "||" in command or ";" in command:
        # Split and check each part
        parts = re.split(r"[;&|]", command)
        for part in parts:
            dangerous, reason = is_command_dangerous(part.strip())
            if dangerous:
                return True, reason

    return False, ""