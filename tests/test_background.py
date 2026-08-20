from __future__ import annotations

from pathlib import Path

from hearth.goal import GoalGate
from hearth.hooks import Hooks
from hearth.llm import FakeClient, text_response, tool_response
from hearth.loop import Session, run_turn
from hearth.permission import Permission


def test_background_bash_notifies_on_next_turn(tmp_path: Path) -> None:
	hooks = Hooks()
	hooks.register("PreToolUse", Permission(tmp_path, auto_allow_shell=True))
	session = Session(
		workspace=tmp_path,
		client=FakeClient(
			[
				tool_response(
					"t1",
					"bash",
					{"command": "echo bg-ok", "run_in_background": True},
				),
				text_response("saw the notification"),
			]
		),
		model="fake",
		hooks=hooks,
		goal=GoalGate(),
		messages=[{"role": "user", "content": "run it"}],
		active_request="run it",
		max_turns=8,
		sync_background=True,
	)
	result = run_turn(session)
	assert result.text == "saw the notification"
	started = session.client.calls[0]
	# second complete should already include the inbound notification
	follow = session.client.calls[1]["messages"]
	assert any(
		isinstance(message.get("content"), str)
		and "Background task completed" in message["content"]
		and "bg-ok" in message["content"]
		for message in follow
	)
	assert started["tools"]
