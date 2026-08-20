from __future__ import annotations

import sys
from pathlib import Path

from hearth.memory import filter_for_prompt
from hearth.skills import catalog_for_prompt


def _platform_name() -> str:
	if sys.platform == "win32":
		return "Windows"
	if sys.platform == "darwin":
		return "macOS"
	return "Linux"


def assemble_system_prompt(workspace: Path) -> str:
	parts = [
		"You are a coding agent living in a harness called Hearth.\n"
		f"Workspace: {workspace}\n"
		f"Platform: {_platform_name()}. Trust the bash tool's description for which shell it uses.\n"
		"Use tools to inspect and change files. Prefer acting over explaining.\n"
		"When you run a verification command, put the command and its result in the "
		"conversation so a later goal evaluator can check evidence.\n"
		"MCP, workflow, and teams may still be unwired."
	]
	memory = filter_for_prompt(workspace)
	if memory:
		parts.append(memory)
	catalog = catalog_for_prompt(workspace)
	if catalog:
		parts.append(catalog)
	return "\n".join(parts)
