from __future__ import annotations

import locale
import os
import subprocess
import sys
from pathlib import Path

from hearth.permission import resolve_in_workspace

# Git Bash shares the Windows filesystem and ships ls/cat/grep, so it is the
# closest thing to the "bash" this tool advertises on Windows. cmd.exe is only
# a fallback when Git is not installed.
GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def _shell() -> tuple[list[str], str]:
	"""Return (argv_prefix, text_encoding) for the platform's shell."""
	if sys.platform == "win32":
		if GIT_BASH.is_file():
			return [str(GIT_BASH), "-c"], "utf-8"
		return [os.environ.get("COMSPEC", "cmd.exe"), "/c"], locale.getpreferredencoding(False)
	return ["/bin/bash", "-c"], "utf-8"


def _bash_description() -> str:
	if sys.platform == "win32" and not GIT_BASH.is_file():
		return (
			"Run a shell command via cmd.exe (Windows). Use Windows syntax: "
			"dir, type, findstr instead of ls, cat, grep."
		)
	return "Run a bash command in the workspace. Prefer this for git, tests, and one-off scripts."


def bash_tool() -> dict:
	return {
		"name": "bash",
		"description": _bash_description(),
		"input_schema": {
			"type": "object",
			"properties": {
				"command": {"type": "string"},
				"run_in_background": {"type": "boolean"},
			},
			"required": ["command"],
		},
	}


def run_bash(args: dict, workspace: Path) -> str:
	command = args.get("command", "")
	if not isinstance(command, str) or not command.strip():
		return "Error: command must be a non-empty string"
	shell, encoding = _shell()
	try:
		result = subprocess.run(
			[*shell, command],
			cwd=resolve_in_workspace(workspace, "."),
			capture_output=True,
			text=True,
			encoding=encoding,
			errors="replace",
			timeout=120,
		)
	except subprocess.TimeoutExpired:
		return "Error: Timeout (120s)"
	except OSError as error:
		return f"Error: {error}"
	output = (result.stdout + result.stderr).strip()
	if not output:
		output = "(no output)"
	return f"{output[:50000]}\n(exit {result.returncode})"
