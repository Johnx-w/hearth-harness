from __future__ import annotations

from pathlib import Path

from hearth.goal import GoalGate
from hearth.hooks import Hooks
from hearth.llm import FakeClient, text_response, tool_response
from hearth.loop import Session, run_turn
from hearth.permission import Permission


def test_subagent_returns_summary_without_merging_child_trace(tmp_path: Path) -> None:
	hooks = Hooks()
	hooks.register("PreToolUse", Permission(tmp_path, auto_allow_shell=True))
	session = Session(
		workspace=tmp_path,
		client=FakeClient(
			[
				tool_response("t1", "subagent", {"prompt": "inspect"}),
				text_response("only in child"),
				text_response("used the summary"),
			]
		),
		model="fake",
		hooks=hooks,
		goal=GoalGate(),
		messages=[{"role": "user", "content": "do the task"}],
		active_request="do the task",
		max_turns=8,
	)
	result = run_turn(session)
	assert result.text == "used the summary"
	plain_users = [
		message["content"]
		for message in session.messages
		if message.get("role") == "user" and isinstance(message.get("content"), str)
	]
	assert "inspect" not in plain_users
	tool_msg = session.messages[-2]
	assert "only in child" in tool_msg["content"][0]["content"]
