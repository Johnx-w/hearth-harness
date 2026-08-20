from __future__ import annotations

from pathlib import Path

from hearth.goal import GoalGate
from hearth.hooks import Hooks
from hearth.llm import FakeClient, text_response
from hearth.loop import Session
from hearth.permission import Permission
from hearth.workflow import WorkflowRegistry


def _pipe(ctx, args: dict) -> str:
	del args
	first = ctx.agent("step-a", "do a")
	second = ctx.agent("step-b", "do b")
	return f"{first}|{second}"


def test_workflow_journals_agent_calls_on_resume(tmp_path: Path) -> None:
	registry = WorkflowRegistry()
	registry.register("pipe", _pipe)
	client = FakeClient([text_response("A"), text_response("B")])
	session = Session(
		workspace=tmp_path,
		client=client,
		model="fake",
		hooks=Hooks(),
		goal=GoalGate(),
		workflows=registry,
	)
	session.hooks.register(
		"PreToolUse", Permission(tmp_path, auto_allow_shell=True)
	)
	first = registry.handle({"name": "pipe", "args": {}}, session)
	assert "A|B" in first
	run_id = first.split("run_id=", 1)[1].split("\n", 1)[0]
	assert (tmp_path / ".runtime" / f"{run_id}.json").is_file()
	assert (tmp_path / ".runtime" / f"{run_id}.journal.jsonl").is_file()

	session.client = FakeClient([])
	second = registry.handle(
		{"name": "pipe", "resume_from_run_id": run_id},
		session,
	)
	assert "A|B" in second


def test_workflow_rejects_submitted_code(tmp_path: Path) -> None:
	registry = WorkflowRegistry()
	session = Session(
		workspace=tmp_path,
		client=FakeClient([]),
		model="fake",
		hooks=Hooks(),
		goal=GoalGate(),
		workflows=registry,
	)
	out = registry.handle({"name": "pipe", "code": "print(1)"}, session)
	assert "cannot accept submitted code" in out
