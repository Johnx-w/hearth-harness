from __future__ import annotations

from pathlib import Path

from hearth.memory import STORE_CHAR_BUDGET, write_memory
from hearth.prompt import assemble_system_prompt
from hearth.tools.pool import assemble_tool_pool
from hearth.tools.todo import TodoList


def test_memory_filters_into_prompt_and_write_stays_in_dir(tmp_path: Path) -> None:
	mem = tmp_path / ".memory"
	mem.mkdir()
	(mem / "notes.md").write_text("Prefer tabs.\n", encoding="utf-8")
	prompt = assemble_system_prompt(tmp_path)
	assert "Prefer tabs." in prompt
	assert "Memory (filtered into this turn)" in prompt

	schemas, handlers = assemble_tool_pool(tmp_path, TodoList())
	assert any(tool["name"] == "memory_write" for tool in schemas)
	out = handlers["memory_write"](
		{"path": "prefs.md", "content": "no spaces", "mode": "replace"}
	)
	assert "Wrote" in out
	assert (mem / "prefs.md").read_text(encoding="utf-8") == "no spaces"


def test_memory_write_rejects_escape(tmp_path: Path) -> None:
	(tmp_path / ".memory").mkdir()
	out = write_memory(
		{"path": "../secret.md", "content": "x"},
		tmp_path,
	)
	assert "Error:" in out
	assert not (tmp_path / "secret.md").exists()


def test_memory_consolidates_when_store_is_huge(tmp_path: Path) -> None:
	mem = tmp_path / ".memory"
	mem.mkdir()
	huge = "n" * (STORE_CHAR_BUDGET + 1000)
	out = write_memory({"path": "big.md", "content": huge}, tmp_path)
	assert "Wrote" in out
	text = (mem / "big.md").read_text(encoding="utf-8")
	assert len(text) < len(huge)
	assert "[memory consolidated]" in text
