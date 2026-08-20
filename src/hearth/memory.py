from __future__ import annotations

from pathlib import Path

from hearth.permission import resolve_in_workspace

MEMORY_DIR = ".memory"
PROMPT_CHAR_BUDGET = 4000
STORE_CHAR_BUDGET = 20000

MEMORY_TOOL = {
	"name": "memory_write",
	"description": (
		"Write a memory record under .memory/. "
		"Use relative paths like notes.md. mode is replace or append."
	),
	"input_schema": {
		"type": "object",
		"properties": {
			"path": {"type": "string"},
			"content": {"type": "string"},
			"mode": {"type": "string"},
		},
		"required": ["path", "content"],
	},
}


def filter_for_prompt(workspace: Path) -> str:
	root = workspace / MEMORY_DIR
	if not root.is_dir():
		return ""
	chunks: list[str] = []
	used = 0
	for path in sorted(root.rglob("*")):
		if not path.is_file():
			continue
		text = path.read_text(encoding="utf-8")
		label = path.relative_to(root).as_posix()
		piece = f"### {label}\n{text}".strip()
		if used + len(piece) > PROMPT_CHAR_BUDGET:
			remain = PROMPT_CHAR_BUDGET - used
			if remain <= 0:
				break
			piece = piece[:remain] + "\n[memory truncated]"
		chunks.append(piece)
		used += len(piece)
		if used >= PROMPT_CHAR_BUDGET:
			break
	if not chunks:
		return ""
	return "Memory (filtered into this turn):\n" + "\n\n".join(chunks)


def write_memory(args: dict, workspace: Path) -> str:
	rel = args.get("path", "")
	content = args.get("content", "")
	mode = str(args.get("mode") or "replace")
	if not isinstance(rel, str) or not rel.strip():
		return "Error: path must be a non-empty string"
	if not isinstance(content, str):
		return "Error: content must be a string"
	if mode not in {"replace", "append"}:
		return "Error: mode must be replace or append"
	try:
		path = _memory_file(workspace, rel.strip())
	except ValueError as error:
		return f"Error: {error}"
	path.parent.mkdir(parents=True, exist_ok=True)
	if mode == "append" and path.is_file():
		existing = path.read_text(encoding="utf-8")
		path.write_text(existing + content, encoding="utf-8")
	else:
		path.write_text(content, encoding="utf-8")
	consolidate(workspace)
	return f"Wrote {path.relative_to(workspace).as_posix()}"


def consolidate(workspace: Path) -> None:
	root = workspace / MEMORY_DIR
	if not root.is_dir():
		return
	files = [path for path in sorted(root.rglob("*")) if path.is_file()]
	total = sum(path.stat().st_size for path in files)
	for path in files:
		if total <= STORE_CHAR_BUDGET:
			return
		text = path.read_text(encoding="utf-8")
		if len(text) <= 200:
			continue
		kept = text[:200] + "\n[memory consolidated]"
		path.write_text(kept, encoding="utf-8")
		total -= len(text) - len(kept)


def extract_after_turn(workspace: Path, messages: list) -> None:
	"""Stop-hook seam. Records are written via memory_write during the loop."""
	del messages
	consolidate(workspace)


def _memory_file(workspace: Path, rel: str) -> Path:
	relative = Path(rel)
	if relative.is_absolute() or ".." in relative.parts:
		raise ValueError("memory path must stay under .memory/")
	return resolve_in_workspace(workspace, str(Path(MEMORY_DIR) / relative))
