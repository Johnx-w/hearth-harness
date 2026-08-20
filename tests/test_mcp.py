from __future__ import annotations

from pathlib import Path

from hearth.goal import GoalGate
from hearth.hooks import Hooks
from hearth.llm import FakeClient, text_response, tool_response
from hearth.loop import Session, run_turn
from hearth.mcp import McpHub
from hearth.permission import Permission
from hearth.tools.pool import assemble_tool_pool
from hearth.tools.todo import TodoList


def test_connect_mcp_exposes_tool_on_next_pool(tmp_path: Path) -> None:
	hub = McpHub()
	full = hub.connect(
		"time",
		name="now",
		description="Current time",
		handler=lambda args: "noon",
	)
	assert full == "mcp__time__now"
	session = Session(
		workspace=tmp_path,
		client=FakeClient([]),
		model="fake",
		hooks=Hooks(),
		goal=GoalGate(),
		mcp=hub,
	)
	schemas, handlers = assemble_tool_pool(tmp_path, TodoList(), session)
	assert any(tool["name"] == "mcp__time__now" for tool in schemas)
	assert handlers["mcp__time__now"]({}) == "noon"


def test_loop_runs_host_mcp_tool(tmp_path: Path) -> None:
	hub = McpHub()
	hub.connect(
		"echo",
		name="ping",
		description="Echo text",
		handler=lambda args: str(args.get("text") or ""),
		input_schema={
			"type": "object",
			"properties": {"text": {"type": "string"}},
		},
	)
	hooks = Hooks()
	hooks.register(
		"PreToolUse",
		Permission(tmp_path, auto_allow_shell=True, mcp_servers=hub.servers),
	)
	session = Session(
		workspace=tmp_path,
		client=FakeClient(
			[
				tool_response("t1", "mcp__echo__ping", {"text": "pong"}),
				text_response("got pong"),
			]
		),
		model="fake",
		hooks=hooks,
		goal=GoalGate(),
		messages=[{"role": "user", "content": "ping"}],
		active_request="ping",
		max_turns=8,
		mcp=hub,
	)
	result = run_turn(session)
	assert result.text == "got pong"
	assert "pong" in session.messages[-2]["content"][0]["content"]


def test_unknown_mcp_server_is_denied(tmp_path: Path) -> None:
	hooks = Hooks()
	hooks.register("PreToolUse", Permission(tmp_path, mcp_servers=set()))
	session = Session(
		workspace=tmp_path,
		client=FakeClient(
			[
				tool_response("t1", "mcp__shadow__x", {}),
				text_response("blocked"),
			]
		),
		model="fake",
		hooks=hooks,
		goal=GoalGate(),
		messages=[{"role": "user", "content": "try"}],
		active_request="try",
		max_turns=8,
	)
	run_turn(session)
	assert "host allowlist" in session.messages[-2]["content"][0]["content"]
