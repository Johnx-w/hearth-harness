from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hearth.background import inject_inbound, should_run_background, start_background
from hearth.compact import prepare_context
from hearth.cron import CronBook
from hearth.goal import GoalGate
from hearth.hooks import Hooks
from hearth.llm import LLMClient
from hearth.mcp import McpHub
from hearth.prompt import assemble_system_prompt
from hearth.tools.pool import assemble_tool_pool
from hearth.tools.todo import TodoList
from hearth.types import StopDecision, TurnResult

DEFAULT_MAX_TOKENS = 8000


@dataclass
class Session:
	workspace: Path
	client: LLMClient
	model: str
	hooks: Hooks
	goal: GoalGate
	messages: list[dict[str, Any]] = field(default_factory=list)
	todos: TodoList = field(default_factory=TodoList)
	active_request: str = ""
	max_turns: int | None = None
	max_tokens: int = DEFAULT_MAX_TOKENS
	turns: int = 0
	allow_subagent: bool = True
	inbound: list[dict[str, Any]] = field(default_factory=list)
	sync_background: bool = False
	mcp: McpHub = field(default_factory=McpHub)


def tool_result(tool_use_id: str, content: str) -> dict[str, str]:
	return {
		"type": "tool_result",
		"tool_use_id": tool_use_id,
		"content": content,
	}


def run_turn(session: Session) -> TurnResult:
	"""One user request: loop until the model stops or the goal gate allows return."""
	while True:
		if session.max_turns is not None and session.turns >= session.max_turns:
			session.hooks.emit("Stop", session.messages)
			return TurnResult(
				text="",
				status="max_turns",
				reason="global max_turns reached",
			)
		session.turns += 1

		inject_inbound(
			session.messages,
			session.inbound,
			CronBook(session.workspace),
		)
		prepare_context(session.messages, session.active_request)
		tools, handlers = assemble_tool_pool(session.workspace, session.todos, session)
		system = assemble_system_prompt(session.workspace)

		response = session.client.complete(
			model=session.model,
			system=system,
			messages=session.messages,
			tools=tools,
			max_tokens=session.max_tokens,
		)
		session.messages.append(
			{"role": "assistant", "content": response.raw_content}
		)

		if not response.tool_uses:
			decision = _decide_stop(session)
			if decision.action == "block":
				session.messages.append(
					{
						"role": "user",
						"content": (
							"[Goal still active]\n"
							f"Evaluator: {decision.reason}\n"
							"Continue working and surface the missing evidence."
						),
					}
				)
				continue
			session.hooks.emit("Stop", session.messages)
			return TurnResult(
				text=response.text,
				status=decision.action,
				reason=decision.reason,
			)

		results = []
		for block in response.tool_uses:
			denied = session.hooks.emit("PreToolUse", block)
			if denied is not None:
				results.append(tool_result(block.id, str(denied)))
				continue
			if should_run_background(block):
				start_background(session, block)
				results.append(
					tool_result(
						block.id,
						"[Background task started] Result will arrive as a notification.",
					)
				)
				continue
			handler = handlers.get(block.name)
			if handler is None:
				output = f"Error: unknown tool {block.name}"
			else:
				try:
					output = handler(block.input)
				except Exception as error:
					output = f"{type(error).__name__}: {error}"
				session.hooks.emit("PostToolUse", block, output)
			results.append(tool_result(block.id, str(output)))
		session.messages.append({"role": "user", "content": results})


def _decide_stop(session: Session) -> StopDecision:
	return session.goal.evaluate_after_turn(
		session.messages,
		background_running=False,
	)


def last_assistant_text(messages: list[dict[str, Any]]) -> str:
	for message in reversed(messages):
		if message.get("role") != "assistant":
			continue
		content = message.get("content")
		chunks: list[str] = []
		if isinstance(content, str):
			return content
		if isinstance(content, list):
			for block in content:
				if isinstance(block, dict) and block.get("type") == "text":
					chunks.append(str(block.get("text") or ""))
				elif hasattr(block, "type") and block.type == "text":
					chunks.append(getattr(block, "text", "") or "")
			return "".join(chunks)
	return ""
