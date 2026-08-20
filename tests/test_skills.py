from __future__ import annotations

from pathlib import Path

from hearth.prompt import assemble_system_prompt
from hearth.skills import load_skill
from hearth.tools.pool import assemble_tool_pool
from hearth.tools.todo import TodoList


def test_catalog_lists_skills_and_load_skill_returns_body(tmp_path: Path) -> None:
	skill_dir = tmp_path / ".skills" / "review"
	skill_dir.mkdir(parents=True)
	(skill_dir / "SKILL.md").write_text(
		"---\ndescription: Review a diff carefully.\n---\n# Review\nCheck tests.\n",
		encoding="utf-8",
	)
	prompt = assemble_system_prompt(tmp_path)
	assert "load_skill" in prompt
	assert "review: Review a diff carefully." in prompt

	schemas, handlers = assemble_tool_pool(tmp_path, TodoList())
	assert any(tool["name"] == "load_skill" for tool in schemas)
	body = handlers["load_skill"]({"name": "review"})
	assert "Check tests." in body
	assert "description:" not in body


def test_unknown_skill_returns_error(tmp_path: Path) -> None:
	(tmp_path / ".skills").mkdir()
	assert "unknown skill" in load_skill({"name": "missing"}, tmp_path)
