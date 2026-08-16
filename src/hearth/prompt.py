from __future__ import annotations

import sys
from pathlib import Path


def _platform_name() -> str:
	if sys.platform == "win32":
		return "Windows"
	if sys.platform == "darwin":
		return "macOS"
	return "Linux"


def assemble_system_prompt(workspace: Path) -> str:
	return (
		"You are a coding agent living in a harness called Hearth.\n"
		f"Workspace: {workspace}\n"
		f"Platform: {_platform_name()}. Trust the bash tool's description for which shell it uses.\n"
		"Use tools to inspect and change files. Prefer acting over explaining.\n"
		"When you run a verification command, put the command and its result in the "
		"conversation so a later goal evaluator can check evidence.\n"
		"Skills, memory, MCP, workflow, and teams are not wired in this MVP."
	)
