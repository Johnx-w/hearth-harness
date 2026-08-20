from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from hearth.goal import GoalGate

RUNTIME_DIR = ".runtime"

WORKFLOW_TOOL = {
	"name": "Workflow",
	"description": (
		"Run a host-registered workflow script. Pass name, args, "
		"and optional resume_from_run_id. You cannot submit code."
	),
	"input_schema": {
		"type": "object",
		"properties": {
			"name": {"type": "string"},
			"args": {"type": "object"},
			"resume_from_run_id": {"type": "string"},
		},
		"required": ["name"],
	},
}

Script = Callable[["WorkflowCtx", dict], str]


class WorkflowCtx:
	def __init__(
		self,
		*,
		run_id: str,
		workspace: Path,
		parent: Any,
		journal: dict[str, str],
	) -> None:
		self.run_id = run_id
		self.workspace = workspace
		self.parent = parent
		self.journal = journal

	def agent(self, key: str, prompt: str) -> str:
		if key in self.journal:
			return self.journal[key]
		from hearth.loop import Session, last_assistant_text, run_turn

		child = Session(
			workspace=self.workspace,
			client=self.parent.client,
			model=self.parent.model,
			hooks=self.parent.hooks,
			goal=GoalGate(),
			messages=[{"role": "user", "content": prompt}],
			active_request=prompt,
			max_turns=4,
			allow_subagent=False,
		)
		result = run_turn(child)
		text = (result.text or last_assistant_text(child.messages)).strip()
		self.journal[key] = text
		_append_journal(self.workspace, self.run_id, key, text)
		return text


class WorkflowRegistry:
	def __init__(self) -> None:
		self.scripts: dict[str, Script] = {}

	def register(self, name: str, script: Script) -> None:
		self.scripts[name] = script

	def handle(self, args: dict, parent: Any) -> str:
		name = str(args.get("name") or "").strip()
		if not name:
			return "Error: name is required"
		if "code" in args or "script" in args:
			return "Error: workflows cannot accept submitted code"
		raw_args = args.get("args") or {}
		if isinstance(raw_args, str):
			try:
				raw_args = json.loads(raw_args)
			except json.JSONDecodeError:
				return "Error: args must be an object"
		if not isinstance(raw_args, dict):
			return "Error: args must be an object"
		resume = str(args.get("resume_from_run_id") or "").strip() or None
		return self.run(name, raw_args, resume, parent)

	def run(
		self,
		name: str,
		args: dict,
		resume_from_run_id: str | None,
		parent: Any,
	) -> str:
		script = self.scripts.get(name)
		if script is None:
			return f"Error: unknown workflow {name}"
		workspace = parent.workspace
		run_id = resume_from_run_id or uuid.uuid4().hex[:12]
		state = _load_state(workspace, run_id) if resume_from_run_id else None
		journal = dict(state.get("journal") or {}) if state else {}
		ctx = WorkflowCtx(
			run_id=run_id,
			workspace=workspace,
			parent=parent,
			journal=journal,
		)
		output = script(ctx, args)
		_save_state(
			workspace,
			run_id,
			{"name": name, "args": args, "journal": ctx.journal},
		)
		return f"run_id={run_id}\n{output}"


def _runtime_dir(workspace: Path) -> Path:
	path = workspace / RUNTIME_DIR
	path.mkdir(parents=True, exist_ok=True)
	return path


def _load_state(workspace: Path, run_id: str) -> dict:
	path = _runtime_dir(workspace) / f"{run_id}.json"
	if not path.is_file():
		return {}
	return json.loads(path.read_text(encoding="utf-8"))


def _save_state(workspace: Path, run_id: str, state: dict) -> None:
	path = _runtime_dir(workspace) / f"{run_id}.json"
	path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_journal(workspace: Path, run_id: str, key: str, value: str) -> None:
	path = _runtime_dir(workspace) / f"{run_id}.journal.jsonl"
	with path.open("a", encoding="utf-8") as handle:
		handle.write(json.dumps({"key": key, "value": value}) + "\n")
