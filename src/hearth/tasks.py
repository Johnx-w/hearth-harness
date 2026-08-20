from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from hearth.permission import resolve_in_workspace

TASKS_DIR = ".tasks"
STATUSES = ("pending", "ready", "claimed", "done")

TASK_TOOL = {
	"name": "task_graph",
	"description": (
		"Durable task graph under .tasks/. Cross-session, with dependencies. "
		"Not the in-session todo list. actions: list, create, claim, complete."
	),
	"input_schema": {
		"type": "object",
		"properties": {
			"action": {"type": "string"},
			"id": {"type": "string"},
			"content": {"type": "string"},
			"depends_on": {"type": "array", "items": {"type": "string"}},
			"claimed_by": {"type": "string"},
		},
		"required": ["action"],
	},
}


@dataclass
class Task:
	id: str
	content: str
	status: str = "pending"
	depends_on: list[str] = field(default_factory=list)
	claimed_by: str | None = None
	worktree: str | None = None


class TaskGraph:
	def __init__(self, workspace: Path) -> None:
		self.workspace = workspace
		self.root = workspace / TASKS_DIR

	def handle(self, args: dict) -> str:
		action = str(args.get("action") or "").strip()
		if action == "list":
			return self.list_text()
		if action == "create":
			return self.create(
				str(args.get("id") or "").strip(),
				str(args.get("content") or ""),
				_as_id_list(args.get("depends_on")),
			)
		if action == "claim":
			return self.claim(
				str(args.get("id") or "").strip(),
				str(args.get("claimed_by") or "agent"),
			)
		if action == "complete":
			return self.complete(str(args.get("id") or "").strip())
		return "Error: action must be list, create, claim, or complete"

	def list_text(self) -> str:
		tasks = self.load_all()
		if not tasks:
			return "Task graph empty"
		lines = []
		for task in tasks:
			deps = ",".join(task.depends_on) or "-"
			claim = task.claimed_by or "-"
			lines.append(
				f"{task.id} [{task.status}] {task.content} deps={deps} claimed_by={claim}"
			)
		return "\n".join(lines)

	def create(self, task_id: str, content: str, depends_on: list[str]) -> str:
		if not task_id:
			return "Error: id is required"
		if not content.strip():
			return "Error: content is required"
		self.root.mkdir(parents=True, exist_ok=True)
		task = Task(
			id=task_id,
			content=content.strip(),
			depends_on=depends_on,
		)
		self._refresh_status(task)
		self._save(task)
		return f"Created {task.id} [{task.status}]"

	def claim(self, task_id: str, claimed_by: str) -> str:
		task = self._load(task_id)
		if task is None:
			return f"Error: unknown task {task_id}"
		self._refresh_status(task)
		if task.status == "done":
			return f"Error: {task_id} is already done"
		if task.status == "pending":
			return f"Error: {task_id} is blocked on {','.join(task.depends_on)}"
		if task.status == "claimed" and task.claimed_by != claimed_by:
			return f"Error: {task_id} is claimed by {task.claimed_by}"
		task.status = "claimed"
		task.claimed_by = claimed_by or "agent"
		self._save(task)
		return f"Claimed {task.id} by {task.claimed_by}"

	def complete(self, task_id: str) -> str:
		task = self._load(task_id)
		if task is None:
			return f"Error: unknown task {task_id}"
		task.status = "done"
		self._save(task)
		for other in self.load_all():
			if other.id == task_id:
				continue
			before = other.status
			self._refresh_status(other)
			if other.status != before:
				self._save(other)
		return f"Completed {task.id}"

	def load_all(self) -> list[Task]:
		if not self.root.is_dir():
			return []
		tasks = []
		for path in sorted(self.root.glob("*.json")):
			task = self._load(path.stem)
			if task is not None:
				self._refresh_status(task)
				tasks.append(task)
		return tasks

	def _load(self, task_id: str) -> Task | None:
		if not task_id:
			return None
		path = self._path(task_id)
		if path is None or not path.is_file():
			return None
		raw = json.loads(path.read_text(encoding="utf-8"))
		return Task(
			id=str(raw.get("id") or task_id),
			content=str(raw.get("content") or ""),
			status=str(raw.get("status") or "pending"),
			depends_on=list(raw.get("depends_on") or []),
			claimed_by=raw.get("claimed_by"),
			worktree=raw.get("worktree"),
		)

	def _save(self, task: Task) -> None:
		path = self._path(task.id)
		if path is None:
			raise ValueError(f"invalid task id: {task.id}")
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(json.dumps(asdict(task), indent=2), encoding="utf-8")

	def _refresh_status(self, task: Task) -> None:
		if task.status == "done":
			return
		if task.status == "claimed":
			return
		if self._deps_done(task.depends_on):
			task.status = "ready"
		else:
			task.status = "pending"

	def _deps_done(self, depends_on: list[str]) -> bool:
		for dep in depends_on:
			other = self._load(dep)
			if other is None or other.status != "done":
				return False
		return True

	def _path(self, task_id: str) -> Path | None:
		if not task_id or "/" in task_id or "\\" in task_id or ".." in task_id:
			return None
		try:
			return resolve_in_workspace(
				self.workspace, str(Path(TASKS_DIR) / f"{task_id}.json")
			)
		except ValueError:
			return None


def _as_id_list(value: Any) -> list[str]:
	if value is None:
		return []
	if isinstance(value, str):
		return [part for part in value.split(",") if part.strip()]
	if isinstance(value, list):
		return [str(item).strip() for item in value if str(item).strip()]
	return []
