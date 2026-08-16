from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from hearth.types import StopDecision


class GoalGate:
	"""Stop seam. MVP: no active goal → allow. v2: independent evaluator."""

	def __init__(self) -> None:
		self.condition: str | None = None

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
		del messages
		if not self.active:
			return StopDecision("allow")
		if background_running:
			return StopDecision("defer", "background work is still running")
		# v2: call an evaluator with no tools. Until then, do not pretend success.
		return StopDecision(
			"allow",
			"goal is set but the evaluator is not wired; returning control to the user",
		)
