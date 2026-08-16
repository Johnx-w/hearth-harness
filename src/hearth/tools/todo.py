from __future__ import annotations

from hearth.types import TodoItem

TODO_TOOL = {
	"name": "todo_write",
	"description": "Replace the current-session todo list. statuses: pending | in_progress | completed.",
	"input_schema": {
		"type": "object",
		"properties": {
			"todos": {
				"type": "array",
				"items": {
					"type": "object",
					"properties": {
						"id": {"type": "string"},
						"content": {"type": "string"},
						"status": {"type": "string"},
					},
					"required": ["id", "content"],
				},
			},
		},
		"required": ["todos"],
	},
}


class TodoList:
	def __init__(self) -> None:
		self.items: list[TodoItem] = []

	def write(self, args: dict) -> str:
		raw = args.get("todos")
		if not isinstance(raw, list):
			return "Error: todos must be a list"
		items: list[TodoItem] = []
		for entry in raw:
			if not isinstance(entry, dict):
				return "Error: each todo must be an object"
			status = str(entry.get("status") or "pending")
			if status not in {"pending", "in_progress", "completed"}:
				return f"Error: invalid status {status}"
			items.append(
				TodoItem(
					id=str(entry.get("id") or ""),
					content=str(entry.get("content") or ""),
					status=status,
				)
			)
		self.items = items
		if not items:
			return "Todo list cleared"
		lines = [f"[{item.status}] {item.id}: {item.content}" for item in items]
		return "Updated todos:\n" + "\n".join(lines)
