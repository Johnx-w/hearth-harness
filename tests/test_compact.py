from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from hearth.compact import prepare_context
from hearth.goal import GoalGate
from hearth.hooks import Hooks
from hearth.llm import FakeClient, text_response
from hearth.loop import Session, run_turn
from hearth.permission import Permission


def _tool_result_message(tool_use_id: str, body: str) -> dict:
	return {
		"role": "user",
		"content": [
			{
				"type": "tool_result",
				"tool_use_id": tool_use_id,
				"content": body,
			}
		],
	}


def test_short_transcript_is_left_alone() -> None:
	messages = [
		{"role": "user", "content": "do the task"},
		{"role": "assistant", "content": "ok"},
	]
	snapshot = deepcopy(messages)
	prepare_context(messages, "do the task")
	assert messages == snapshot


def test_old_tool_result_is_snipped_recent_five_stay() -> None:
	huge = "x" * 8000
	messages = [
		{"role": "user", "content": "start"},
		{"role": "assistant", "content": "working"},
		_tool_result_message("t-old", huge),
		{"role": "user", "content": "note-1"},
		{"role": "user", "content": "note-2"},
		{"role": "user", "content": "note-3"},
		_tool_result_message("t-near", "small-near"),
		{"role": "user", "content": "current task"},
	]
	prepare_context(messages, "current task")

	old = messages[2]["content"][0]
	assert old["tool_use_id"] == "t-old"
	assert old["content"] != huge
	assert old["content"].startswith("x")
	assert "[compacted]" in old["content"]

	assert messages[3]["content"] == "note-1"
	assert messages[4]["content"] == "note-2"
	assert messages[5]["content"] == "note-3"
	assert messages[6]["content"][0]["content"] == "small-near"
	assert messages[6]["content"][0]["tool_use_id"] == "t-near"
	assert messages[7]["content"] == "current task"


def test_fewer_than_five_messages_are_not_snipped() -> None:
	huge = "y" * 8000
	messages = [
		{"role": "user", "content": "a"},
		{"role": "assistant", "content": "b"},
		_tool_result_message("t1", huge),
	]
	prepare_context(messages, "a")
	assert messages[2]["content"][0]["content"] == huge


def test_loop_sees_snipped_history_before_complete(tmp_path: Path) -> None:
	huge = "z" * 8000
	hooks = Hooks()
	hooks.register("PreToolUse", Permission(tmp_path, auto_allow_shell=True))
	session = Session(
		workspace=tmp_path,
		client=FakeClient([text_response("done")]),
		model="fake",
		hooks=hooks,
		goal=GoalGate(),
		messages=[
			{"role": "user", "content": "start"},
			{"role": "assistant", "content": "working"},
			_tool_result_message("t-old", huge),
			{"role": "user", "content": "n1"},
			{"role": "user", "content": "n2"},
			{"role": "user", "content": "n3"},
			{"role": "user", "content": "n4"},
			{"role": "user", "content": "do the task"},
		],
		active_request="do the task",
		max_turns=8,
	)
	result = run_turn(session)
	assert result.status == "allow"
	seen = session.client.calls[0]["messages"][2]["content"][0]["content"]
	assert seen != huge
	assert "[compacted]" in seen
