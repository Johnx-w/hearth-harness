from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from hearth.types import ToolUse

DENY_SUBSTRINGS = ("rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if=")
FILE_TOOLS = ("read_file", "write_file", "edit_file")


class Permission:
	"""PreToolUse policy. Ask is injected so tests never call input()."""

	def __init__(
		self,
		workspace: Path,
		ask: Callable[[str], bool] | None = None,
		*,
		auto_allow_shell: bool = False,
	) -> None:
		self.workspace = workspace.resolve()
		self.ask = ask
		self.auto_allow_shell = auto_allow_shell

	def __call__(self, block: ToolUse) -> str | None:
		if block.name == "bash":
			return self._bash(block.input.get("command", ""))
		if block.name in FILE_TOOLS:
			path = block.input.get("path", "")
			if not isinstance(path, str):
				return "Permission denied: path must be a string"
			return self._path_inside(path)
		if block.name == "grep":
			path = block.input.get("path", ".")
			if not isinstance(path, str):
				return "Permission denied: path must be a string"
			return self._path_inside(path)
		return None

	def _bash(self, command: object) -> str | None:
		if not isinstance(command, str):
			return "Permission denied: shell command must be a string"
		for pattern in DENY_SUBSTRINGS:
			if pattern in command:
				return f"Permission denied: '{pattern}' is on the deny list"
		if self.auto_allow_shell:
			return None
		if self.ask is None:
			return "Permission denied: interactive shell approval is unavailable"
		prompt = f"Allow shell command?\n  {command}\n[y/N] "
		if not self.ask(prompt):
			return "Permission denied by user"
		return None

	def _path_inside(self, path: str) -> str | None:
		try:
			resolve_in_workspace(self.workspace, path)
		except ValueError as error:
			return f"Permission denied: {error}"
		return None


def resolve_in_workspace(workspace: Path, path: str) -> Path:
	base = workspace.resolve()
	resolved = (base / path).resolve()
	if not resolved.is_relative_to(base):
		raise ValueError(f"path escapes workspace: {path}")
	return resolved
