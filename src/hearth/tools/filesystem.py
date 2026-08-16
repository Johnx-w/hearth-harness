from __future__ import annotations

from pathlib import Path

from hearth.permission import resolve_in_workspace

FILE_TOOLS = [
	{
		"name": "read_file",
		"description": "Read a UTF-8 text file. Optional offset/limit are 1-based line numbers.",
		"input_schema": {
			"type": "object",
			"properties": {
				"path": {"type": "string"},
				"offset": {"type": "integer"},
				"limit": {"type": "integer"},
			},
			"required": ["path"],
		},
	},
	{
		"name": "write_file",
		"description": "Write UTF-8 text to a file, creating parents as needed. Overwrites.",
		"input_schema": {
			"type": "object",
			"properties": {
				"path": {"type": "string"},
				"content": {"type": "string"},
			},
			"required": ["path", "content"],
		},
	},
	{
		"name": "edit_file",
		"description": "Replace exactly one occurrence of old_text with new_text.",
		"input_schema": {
			"type": "object",
			"properties": {
				"path": {"type": "string"},
				"old_text": {"type": "string"},
				"new_text": {"type": "string"},
			},
			"required": ["path", "old_text", "new_text"],
		},
	},
	{
		"name": "glob",
		"description": "List files matching a glob pattern under the workspace.",
		"input_schema": {
			"type": "object",
			"properties": {
				"pattern": {"type": "string"},
			},
			"required": ["pattern"],
		},
	},
	{
		"name": "grep",
		"description": "Search file contents for a substring. Optional path limits the walk.",
		"input_schema": {
			"type": "object",
			"properties": {
				"pattern": {"type": "string"},
				"path": {"type": "string"},
			},
			"required": ["pattern"],
		},
	},
]

SKIP_DIR_NAMES = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}


class WorkspaceFS:
	def __init__(self, workspace: Path) -> None:
		self.workspace = workspace.resolve()

	def read_file(self, args: dict) -> str:
		path = resolve_in_workspace(self.workspace, str(args["path"]))
		if not path.is_file():
			return f"Error: not a file: {path}"
		lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
		offset = int(args.get("offset") or 1)
		limit = args.get("limit")
		start = max(offset - 1, 0)
		end = start + int(limit) if limit is not None else len(lines)
		sliced = lines[start:end]
		numbered = [f"{i + start + 1:>4}|{line}" for i, line in enumerate(sliced)]
		return "\n".join(numbered) if numbered else "(empty)"

	def write_file(self, args: dict) -> str:
		path = resolve_in_workspace(self.workspace, str(args["path"]))
		path.parent.mkdir(parents=True, exist_ok=True)
		content = str(args.get("content", ""))
		path.write_text(content, encoding="utf-8")
		return f"Wrote {path} ({len(content)} bytes)"

	def edit_file(self, args: dict) -> str:
		path = resolve_in_workspace(self.workspace, str(args["path"]))
		if not path.is_file():
			return f"Error: not a file: {path}"
		old = str(args.get("old_text", ""))
		new = str(args.get("new_text", ""))
		text = path.read_text(encoding="utf-8")
		count = text.count(old)
		if count == 0:
			return "Error: old_text not found"
		if count > 1:
			return f"Error: old_text found {count} times; it must be unique"
		path.write_text(text.replace(old, new, 1), encoding="utf-8")
		return f"Edited {path}"

	def glob(self, args: dict) -> str:
		pattern = str(args.get("pattern", ""))
		matches = sorted(
			p.relative_to(self.workspace).as_posix()
			for p in self.workspace.glob(pattern)
			if p.is_file()
		)
		return "\n".join(matches[:200]) if matches else "(no matches)"

	def grep(self, args: dict) -> str:
		pattern = str(args.get("pattern", ""))
		rel = str(args.get("path") or ".")
		root = resolve_in_workspace(self.workspace, rel)
		hits: list[str] = []
		files = [root] if root.is_file() else root.rglob("*")
		for path in files:
			if path.is_dir() or not path.is_file():
				continue
			if any(part in SKIP_DIR_NAMES for part in path.parts):
				continue
			try:
				text = path.read_text(encoding="utf-8")
			except (UnicodeDecodeError, OSError):
				continue
			rel_path = path.relative_to(self.workspace).as_posix()
			for i, line in enumerate(text.splitlines(), 1):
				if pattern in line:
					hits.append(f"{rel_path}:{i}:{line}")
					if len(hits) >= 50:
						return "\n".join(hits)
		return "\n".join(hits) if hits else "(no matches)"
