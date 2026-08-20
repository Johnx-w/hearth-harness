from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from hearth.permission import resolve_in_workspace
from hearth.tasks import TaskGraph

WORKTREES_DIR = ".worktrees"
TEAMS_FILE = ".teams/roster.json"

TEAM_TOOL = {
	"name": "teammate",
	"description": (
		"Persistent teammates: spawn, message, claim a task, status. "
		"Claim binds a git worktree (cwd only, not a sandbox). "
		"Worktree deletion is a host operation, not a tool."
	),
	"input_schema": {
		"type": "object",
		"properties": {
			"action": {"type": "string"},
			"id": {"type": "string"},
			"to": {"type": "string"},
			"text": {"type": "string"},
			"task_id": {"type": "string"},
		},
		"required": ["action"],
	},
}


@dataclass
class Teammate:
	id: str
	status: str = "IDLE"
	mailbox: list[str] = field(default_factory=list)
	task_id: str | None = None


class TeamHub:
	def __init__(self, workspace: Path) -> None:
		self.workspace = workspace
		self.teammates: dict[str, Teammate] = {}
		self._load()

	def handle(self, args: dict) -> str:
		action = str(args.get("action") or "").strip()
		if action == "spawn":
			return self.spawn(str(args.get("id") or "").strip())
		if action == "status":
			return self.status_text()
		if action == "message":
			return self.message(
				str(args.get("to") or "").strip(),
				str(args.get("text") or ""),
			)
		if action == "claim":
			return self.claim(
				str(args.get("id") or "").strip(),
				str(args.get("task_id") or "").strip(),
			)
		if action == "idle":
			return self.idle(str(args.get("id") or "").strip())
		return "Error: action must be spawn, status, message, claim, or idle"

	def spawn(self, teammate_id: str) -> str:
		if not teammate_id:
			return "Error: id is required"
		if teammate_id in self.teammates:
			return f"Error: teammate {teammate_id} already exists"
		self.teammates[teammate_id] = Teammate(id=teammate_id)
		self._save()
		return f"Spawned {teammate_id} [IDLE]"

	def status_text(self) -> str:
		if not self.teammates:
			return "No teammates"
		lines = []
		for mate in self.teammates.values():
			task = mate.task_id or "-"
			inbox = len(mate.mailbox)
			lines.append(f"{mate.id} [{mate.status}] task={task} inbox={inbox}")
		return "\n".join(lines)

	def message(self, to: str, text: str) -> str:
		mate = self.teammates.get(to)
		if mate is None:
			return f"Error: unknown teammate {to}"
		if not text.strip():
			return "Error: text is required"
		mate.mailbox.append(text.strip())
		self._save()
		return f"Queued message for {to}"

	def claim(self, teammate_id: str, task_id: str) -> str:
		mate = self.teammates.get(teammate_id)
		if mate is None:
			return f"Error: unknown teammate {teammate_id}"
		graph = TaskGraph(self.workspace)
		claimed = graph.claim(task_id, teammate_id)
		if claimed.startswith("Error:"):
			return claimed
		path = bind_worktree(self.workspace, task_id)
		task = graph.get(task_id)
		if task is not None:
			task.worktree = str(path)
			graph.save(task)
		mate.status = "WORK"
		mate.task_id = task_id
		self._save()
		return f"{claimed}; worktree={path}"

	def idle(self, teammate_id: str) -> str:
		mate = self.teammates.get(teammate_id)
		if mate is None:
			return f"Error: unknown teammate {teammate_id}"
		mate.status = "IDLE"
		mate.task_id = None
		self._save()
		return f"{teammate_id} [IDLE]"

	def _load(self) -> None:
		path = self.workspace / TEAMS_FILE
		if not path.is_file():
			return
		raw = json.loads(path.read_text(encoding="utf-8"))
		for item in raw.get("teammates", []):
			mate = Teammate(
				id=str(item["id"]),
				status=str(item.get("status") or "IDLE"),
				mailbox=list(item.get("mailbox") or []),
				task_id=item.get("task_id"),
			)
			self.teammates[mate.id] = mate

	def _save(self) -> None:
		path = self.workspace / TEAMS_FILE
		path.parent.mkdir(parents=True, exist_ok=True)
		payload = {"teammates": [asdict(mate) for mate in self.teammates.values()]}
		path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def bind_worktree(workspace: Path, task_id: str) -> Path:
	"""Host helper: extra git worktree, cwd only. Not a sandbox."""
	if not task_id or ".." in task_id or "/" in task_id or "\\" in task_id:
		raise ValueError("invalid task id for worktree")
	dest = resolve_in_workspace(workspace, str(Path(WORKTREES_DIR) / task_id))
	if dest.exists():
		return dest
	dest.parent.mkdir(parents=True, exist_ok=True)
	git_dir = workspace / ".git"
	if git_dir.exists():
		result = subprocess.run(
			[
				"git",
				"worktree",
				"add",
				"-b",
				f"hearth/{task_id}",
				str(dest),
			],
			cwd=workspace,
			capture_output=True,
			text=True,
		)
		if result.returncode == 0:
			return dest
	dest.mkdir(parents=True, exist_ok=True)
	return dest


def remove_worktree(workspace: Path, task_id: str) -> None:
	"""Host-only. Do not expose to the model."""
	dest = workspace / WORKTREES_DIR / task_id
	if (workspace / ".git").exists():
		subprocess.run(
			["git", "worktree", "remove", "--force", str(dest)],
			cwd=workspace,
			capture_output=True,
			text=True,
		)
	if dest.exists():
		shutil.rmtree(dest, ignore_errors=True)
