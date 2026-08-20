from __future__ import annotations

from pathlib import Path

from hearth.tasks import TaskGraph
from hearth.tools.pool import assemble_tool_pool
from hearth.tools.todo import TodoList


def test_task_graph_persists_and_blocks_on_deps(tmp_path: Path) -> None:
	graph = TaskGraph(tmp_path)
	assert "Created a1 [ready]" in graph.create("a1", "setup", [])
	assert "Created a2 [pending]" in graph.create("a2", "use setup", ["a1"])
	blocked = graph.claim("a2", "alice")
	assert "blocked" in blocked
	assert "Claimed a1" in graph.claim("a1", "alice")
	assert "Completed a1" in graph.complete("a1")
	assert "Claimed a2" in graph.claim("a2", "bob")
	listing = graph.list_text()
	assert "a1 [done]" in listing
	assert "a2 [claimed]" in listing
	assert (tmp_path / ".tasks" / "a1.json").is_file()


def test_task_graph_tool_is_in_pool(tmp_path: Path) -> None:
	schemas, handlers = assemble_tool_pool(tmp_path, TodoList())
	assert any(tool["name"] == "task_graph" for tool in schemas)
	out = handlers["task_graph"]({"action": "create", "id": "t1", "content": "ship it"})
	assert "Created t1" in out
