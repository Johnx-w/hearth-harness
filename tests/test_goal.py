from __future__ import annotations

import threading
from pathlib import Path

from hearth.goal import (
	GoalGate,
	apply_goal_command,
	make_llm_evaluator,
	parse_evaluator_text,
)
from hearth.hooks import Hooks
from hearth.llm import FakeClient, text_response
from hearth.loop import Session, run_turn
from hearth.permission import Permission
from hearth.types import StopDecision


def test_parse_evaluator_text() -> None:
	decision = parse_evaluator_text("ACTION: achieved\nREASON: pytest exit 0")
	assert decision.action == "achieved"
	assert "pytest" in decision.reason


def test_defer_when_background_running() -> None:
	gate = GoalGate()
	gate.set_condition("pytest exits 0")
	decision = gate.evaluate_after_turn([], background_running=True)
	assert decision.action == "defer"


def test_wired_evaluator_blocks_then_achieves(tmp_path: Path) -> None:
	seen = {"n": 0}

	def evaluator(condition: str, messages) -> StopDecision:
		del condition
		seen["n"] += 1
		blob = str(messages)
		if "exit 0" in blob:
			return StopDecision("achieved", "pytest passed")
		return StopDecision("block", "no pytest output yet")

	hooks = Hooks()
	hooks.register("PreToolUse", Permission(tmp_path, auto_allow_shell=True))
	session = Session(
		workspace=tmp_path,
		client=FakeClient(
			[text_response("working"), text_response("pytest\nexit 0")]
		),
		model="fake",
		hooks=hooks,
		goal=GoalGate(evaluator=evaluator),
		messages=[{"role": "user", "content": "finish the goal"}],
		active_request="finish the goal",
		max_turns=8,
	)
	session.goal.set_condition("pytest exits 0")
	result = run_turn(session)
	assert result.status == "achieved"
	assert result.text == "pytest\nexit 0"
	assert seen["n"] == 2
	assert session.goal.condition is None
	assert any(
		isinstance(m.get("content"), str) and "Goal still active" in m["content"]
		for m in session.messages
	)


def test_goal_slash_command_sets_condition() -> None:
	session = Session(
		workspace=Path("."),
		client=FakeClient([]),
		model="fake",
		hooks=Hooks(),
		goal=GoalGate(),
	)
	query = apply_goal_command(session, "/goal pytest 退出码 0")
	assert session.goal.condition == "pytest 退出码 0"
	assert "Goal: pytest 退出码 0" in query


def test_llm_evaluator_has_no_tools() -> None:
	client = FakeClient([text_response("ACTION: achieved\nREASON: pytest exit 0")])
	evaluate = make_llm_evaluator(client, "fake")
	decision = evaluate(
		"pytest exits 0",
		[{"role": "user", "content": "pytest\nexit 0"}],
	)
	assert decision.action == "achieved"
	assert client.calls[0]["tools"] == []


def test_defer_waits_for_background_then_evaluates(tmp_path: Path) -> None:
	seen = {"n": 0}

	def evaluator(condition: str, messages) -> StopDecision:
		del condition, messages
		seen["n"] += 1
		return StopDecision("achieved", "background finished")

	class HoldThread(threading.Thread):
		def __init__(self) -> None:
			super().__init__(daemon=True)
			self._release = threading.Event()

		def run(self) -> None:
			self._release.wait()

		def join(self, timeout: float | None = None) -> None:
			self._release.set()
			super().join(timeout)

	held = HoldThread()
	held.start()
	hooks = Hooks()
	hooks.register("PreToolUse", Permission(tmp_path, auto_allow_shell=True))
	session = Session(
		workspace=tmp_path,
		client=FakeClient(
			[text_response("waiting"), text_response("done after background")]
		),
		model="fake",
		hooks=hooks,
		goal=GoalGate(evaluator=evaluator),
		messages=[{"role": "user", "content": "finish the goal"}],
		active_request="finish the goal",
		max_turns=8,
		background_threads=[held],
	)
	session.goal.set_condition("pytest exits 0")
	result = run_turn(session)
	assert result.status == "achieved"
	assert seen["n"] == 1
	assert not held.is_alive()
	assert session.goal.condition is None
