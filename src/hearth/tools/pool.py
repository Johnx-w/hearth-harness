from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from hearth.tools.bash import bash_tool, run_bash
from hearth.tools.filesystem import FILE_TOOLS, WorkspaceFS
from hearth.tools.todo import TODO_TOOL, TodoList

Handler = Callable[[dict], str]


def assemble_tool_pool(
	workspace: Path,
	todos: TodoList,
) -> tuple[list[dict], dict[str, Handler]]:
	"""Rebuild schemas and handlers each turn. MCP/Workflow patch here later."""
	fs = WorkspaceFS(workspace)
	schemas = [bash_tool(), *FILE_TOOLS, TODO_TOOL]
	handlers: dict[str, Handler] = {
		"bash": lambda args: run_bash(args, workspace),
		"read_file": fs.read_file,
		"write_file": fs.write_file,
		"edit_file": fs.edit_file,
		"glob": fs.glob,
		"grep": fs.grep,
		"todo_write": todos.write,
	}
	return schemas, handlers
