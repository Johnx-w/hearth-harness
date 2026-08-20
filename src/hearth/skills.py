from __future__ import annotations

from pathlib import Path

from hearth.permission import resolve_in_workspace

SKILLS_DIR = ".skills"

SKILL_TOOL = {
	"name": "load_skill",
	"description": "Load the full text of a skill by name from .skills/.",
	"input_schema": {
		"type": "object",
		"properties": {
			"name": {"type": "string"},
		},
		"required": ["name"],
	},
}


def catalog_for_prompt(workspace: Path) -> str:
	entries = list_skills(workspace)
	if not entries:
		return ""
	lines = ["Skills (load full text with the load_skill tool):"]
	for name, description in entries:
		if description:
			lines.append(f"- {name}: {description}")
		else:
			lines.append(f"- {name}")
	return "\n".join(lines)


def list_skills(workspace: Path) -> list[tuple[str, str]]:
	root = workspace / SKILLS_DIR
	if not root.is_dir():
		return []
	found: list[tuple[str, str]] = []
	for path in sorted(root.rglob("*.md")):
		name = _skill_name(root, path)
		if not name:
			continue
		description, _body = _parse_skill(path.read_text(encoding="utf-8"))
		found.append((name, description))
	return found


def load_skill(args: dict, workspace: Path) -> str:
	name = args.get("name", "")
	if not isinstance(name, str) or not name.strip():
		return "Error: name must be a non-empty string"
	path = _resolve_skill_path(workspace, name.strip())
	if path is None:
		return f"Error: unknown skill {name.strip()}"
	_description, body = _parse_skill(path.read_text(encoding="utf-8"))
	return body.strip() or path.read_text(encoding="utf-8")


def _skill_name(root: Path, path: Path) -> str:
	relative = path.relative_to(root)
	if path.name.lower() == "skill.md" and len(relative.parts) >= 2:
		return relative.parts[0]
	if path.suffix.lower() == ".md" and len(relative.parts) == 1:
		return path.stem
	return ""


def _resolve_skill_path(workspace: Path, name: str) -> Path | None:
	root = workspace / SKILLS_DIR
	candidates = [
		root / name / "SKILL.md",
		root / name / "skill.md",
		root / f"{name}.md",
	]
	for candidate in candidates:
		try:
			resolved = resolve_in_workspace(workspace, str(candidate.relative_to(workspace)))
		except ValueError:
			continue
		if resolved.is_file():
			return resolved
	return None


def _parse_skill(text: str) -> tuple[str, str]:
	description = ""
	body = text
	if text.startswith("---"):
		end = text.find("\n---", 3)
		if end != -1:
			front = text[3:end]
			body = text[end + 4 :].lstrip("\n")
			for line in front.splitlines():
				stripped = line.strip()
				if stripped.startswith("description:"):
					description = stripped.split(":", 1)[1].strip().strip("\"'")
	if not description:
		for line in body.splitlines():
			if line.startswith("# "):
				description = line[2:].strip()
				break
	return description, body
