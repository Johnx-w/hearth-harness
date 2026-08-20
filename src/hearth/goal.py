from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from hearth.types import StopDecision

Evaluator = Callable[[str, Sequence[dict[str, Any]]], StopDecision]


class GoalGate:
	"""Stop seam. Independent evaluator has no tools."""

	def __init__(self, evaluator: Evaluator | None = None) -> None:
		self.condition: str | None = None
		self.evaluator = evaluator

	@property
	def active(self) -> bool:
		return self.condition is not None

	def clear(self) -> None:
		self.condition = None

	def set_condition(self, condition: str) -> None:
		self.condition = condition.strip() or None

	def evaluate_after_turn(
		self,
		messages: Sequence[dict[str, Any]],
		*,
		background_running: bool = False,
	) -> StopDecision:
		if not self.active:
			return StopDecision("allow")
		if background_running:
			return StopDecision("defer", "background work is still running")
		if self.evaluator is None:
			return StopDecision(
				"allow",
				"goal is set but the evaluator is not wired; returning control to the user",
			)
		return self.evaluator(self.condition or "", messages)


def apply_goal_command(session: Any, query: str) -> str:
	if not query.startswith("/goal"):
		return query
	condition = query[len("/goal") :].strip()
	session.goal.set_condition(condition)
	return (
		"Work until this goal is met. Put verification commands and their "
		f"results in the conversation so the evaluator can see evidence.\n"
		f"Goal: {condition}"
	)


def make_llm_evaluator(client: Any, model: str) -> Evaluator:
	def evaluate(
		condition: str, messages: Sequence[dict[str, Any]]
	) -> StopDecision:
		transcript = _transcript(messages)
		response = client.complete(
			model=model,
			system=(
				"You are a Goal Evaluator. You have no tools. "
				"Judge only evidence already in the conversation. "
				"Reply with:\nACTION: achieved|block|failed|allow\nREASON: ..."
			),
			messages=[
				{
					"role": "user",
					"content": f"Goal: {condition}\n\nConversation:\n{transcript}",
				}
			],
			tools=[],
			max_tokens=400,
		)
		return parse_evaluator_text(response.text)

	return evaluate


def parse_evaluator_text(text: str) -> StopDecision:
	action = "block"
	reason = text.strip()
	for line in text.splitlines():
		stripped = line.strip()
		lower = stripped.lower()
		if lower.startswith("action:"):
			action = stripped.split(":", 1)[1].strip().lower()
		elif lower.startswith("reason:"):
			reason = stripped.split(":", 1)[1].strip()
	if action not in {"allow", "block", "achieved", "failed", "defer", "error"}:
		action = "block"
	return StopDecision(action, reason)


def _transcript(messages: Sequence[dict[str, Any]], limit: int = 8000) -> str:
	parts: list[str] = []
	for message in messages:
		parts.append(f"{message.get('role')}: {message.get('content')}")
	text = "\n".join(parts)
	return text[-limit:]
