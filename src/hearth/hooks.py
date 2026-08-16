from __future__ import annotations

from collections.abc import Callable
from typing import Any

HookFn = Callable[..., Any]

EVENTS = ("UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop")


class Hooks:
	"""Extension seam on the loop. First non-None callback result short-circuits."""

	def __init__(self) -> None:
		self._callbacks: dict[str, list[HookFn]] = {event: [] for event in EVENTS}

	def register(self, event: str, callback: HookFn) -> None:
		if event not in self._callbacks:
			raise ValueError(f"unknown hook event: {event}")
		self._callbacks[event].append(callback)

	def emit(self, event: str, *args: Any) -> Any:
		if event not in self._callbacks:
			raise ValueError(f"unknown hook event: {event}")
		for callback in self._callbacks[event]:
			result = callback(*args)
			if result is not None:
				return result
		return None
