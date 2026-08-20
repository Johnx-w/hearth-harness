from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from hearth.memory import MEMORY_TOOL, write_memory
from hearth.skills import SKILL_TOOL, load_skill
from hearth.tasks import TASK_TOOL, TaskGraph
from hearth.tools.bash import bash_tool, run_bash
from hearth.tools.filesystem import FILE_TOOLS, WorkspaceFS
from hearth.tools.subagent import SUBAGENT_TOOL, run_subagent
from hearth.tools.todo import TODO_TOOL, TodoList

Handler = Callable[[dict], str]


def assemble_tool_pool(
	workspace: Path,
	todos: TodoList,
	session: Any | None = None,
) -> tuple[list[dict], dict[str, Handler]]:
	"""Rebuild schemas and handlers each turn. MCP/Workflow patch here later."""
	fs = WorkspaceFS(workspace)
	graph = TaskGraph(workspace)
	schemas = [bash_tool(), *FILE_TOOLS, TODO_TOOL, SKILL_TOOL, MEMORY_TOOL, TASK_TOOL]
	handlers: dict[str, Handler] = {
		"bash": lambda args: run_bash(args, workspace),
		"read_file": fs.read_file,
		"write_file": fs.write_file,
		"edit_file": fs.edit_file,
		"glob": fs.glob,
		"grep": fs.grep,
		"todo_write": todos.write,
		"load_skill": lambda args: load_skill(args, workspace),
		"memory_write": lambda args: write_memory(args, workspace),
		"task_graph": graph.handle,
	}
	if session is not None:
		hub = getattr(session, "mcp", None)
		if hub is not None:
			schemas.extend(hub.schemas)
			handlers.update(hub.handlers)
		if getattr(session, "allow_subagent", True):
			schemas.append(SUBAGENT_TOOL)
			handlers["subagent"] = lambda args: run_subagent(args, session)
	return schemas, handlers
