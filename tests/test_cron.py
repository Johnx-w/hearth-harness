from __future__ import annotations

from pathlib import Path

from hearth.background import inject_inbound
from hearth.cron import CronBook
from hearth.tools.pool import assemble_tool_pool
from hearth.tools.todo import TodoList


def test_cron_delivers_due_prompt_at_least_once(tmp_path: Path) -> None:
	book = CronBook(tmp_path)
	assert "Scheduled wake" in book.schedule("wake up", delay_seconds=0, job_id="wake")
	inbound: list[dict] = []
	assert book.flush_due(inbound, now=book.jobs[0].due_at) == 1
	assert inbound[0]["content"] == "[Cron] wake up"
	assert book.jobs[0].delivered is True
	assert book.flush_due(inbound, now=book.jobs[0].due_at + 10) == 0
	assert (tmp_path / ".cron" / "jobs.json").is_file()


def test_inject_inbound_flushes_cron(tmp_path: Path) -> None:
	book = CronBook(tmp_path)
	book.schedule("tick", delay_seconds=0, job_id="tick")
	messages: list[dict] = []
	inbound: list[dict] = []
	inject_inbound(messages, inbound, book, now=time_now(book))
	assert any("[Cron] tick" in str(item.get("content")) for item in messages)


def time_now(book: CronBook) -> float:
	return book.jobs[0].due_at


def test_cron_tool_in_pool(tmp_path: Path) -> None:
	schemas, handlers = assemble_tool_pool(tmp_path, TodoList())
	assert any(tool["name"] == "cron" for tool in schemas)
	assert "Scheduled" in handlers["cron"](
		{"action": "schedule", "prompt": "later", "delay_seconds": 60}
	)
