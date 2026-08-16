from __future__ import annotations

from pathlib import Path

from hearth.goal import GoalGate
from hearth.hooks import Hooks
from hearth.llm import FakeClient, text_response, tool_response
from hearth.loop import Session, run_turn
from hearth.permission import Permission
from hearth.types import StopDecision


def _session(tmp_path: Path, script, *, auto_allow_shell: bool = True) -> Session:
	hooks = Hooks()
	hooks.register(
		"PreToolUse",
		Permission(tmp_path, auto_allow_shell=auto_allow_shell),
	)
	return Session(
		workspace=tmp_path,
		client=FakeClient(script),
		model="fake",
		hooks=hooks,
		goal=GoalGate(),
		messages=[{"role": "user", "content": "do the task"}],
		active_request="do the task",
		max_turns=8,
	)


def test_loop_runs_write_then_stops(tmp_path: Path) -> None:
	session = _session(
		tmp_path,
		[
			tool_response("t1", "write_file", {"path": "hello.txt", "content": "hi"}),
			text_response("wrote hello.txt"),
		],
	)
	result = run_turn(session)
	assert result.status == "allow"
	assert result.text == "wrote hello.txt"
	assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "hi"
	assert session.messages[-1]["role"] == "assistant"


def test_permission_blocks_path_escape(tmp_path: Path) -> None:
	session = _session(
		tmp_path,
		[
			tool_response("t1", "write_file", {"path": "../outside.txt", "content": "x"}),
			text_response("could not write"),
		],
	)
	run_turn(session)
	assert not (tmp_path.parent / "outside.txt").exists()
	tool_msg = session.messages[-2]
	assert "Permission denied" in tool_msg["content"][0]["content"]


def test_permission_blocks_deny_list_without_asking(tmp_path: Path) -> None:
	session = _session(
		tmp_path,
		[
			tool_response("t1", "bash", {"command": "sudo shutdown now"}),
			text_response("blocked"),
		],
		auto_allow_shell=True,
	)
	run_turn(session)
	assert "deny list" in session.messages[-2]["content"][0]["content"]


def test_todo_write_replaces_the_session_list(tmp_path: Path) -> None:
	session = _session(
		tmp_path,
		[
			tool_response(
				"t1",
				"todo_write",
				{
					"todos": [
						{"id": "1", "content": "read files", "status": "in_progress"},
					]
				},
			),
			text_response("planned"),
		],
	)
	run_turn(session)
	assert session.todos.items[0].content == "read files"


def test_goal_block_continues_the_same_loop(tmp_path: Path) -> None:
	class OnceBlock(GoalGate):
		def __init__(self) -> None:
			super().__init__()
			self.seen = 0

		def evaluate_after_turn(self, messages, *, background_running: bool = False):
			del messages, background_running
			self.seen += 1
			if self.seen == 1:
				return StopDecision("block", "no pytest output yet")
			return StopDecision("allow")

	session = _session(tmp_path, [text_response("done?"), text_response("really done")])
	session.goal = OnceBlock()
	session.goal.set_condition("pytest exits 0")
	result = run_turn(session)
	assert result.text == "really done"
	assert session.goal.seen == 2
	assert any(
		isinstance(m.get("content"), str) and "Goal still active" in m["content"]
		for m in session.messages
	)


def test_unknown_tool_does_not_crash_the_loop(tmp_path: Path) -> None:
	session = _session(
		tmp_path,
		[
			tool_response("t1", "not_a_tool", {}),
			text_response("ok"),
		],
	)
	result = run_turn(session)
	assert result.status == "allow"
	assert "unknown tool" in session.messages[-2]["content"][0]["content"]
