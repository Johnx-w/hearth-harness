from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import Any, Protocol

from hearth.compact import prepare_context
from hearth.types import LLMResponse, ToolUse

MAX_RATE_RETRIES = 3
RATE_LIMIT_SLEEP = 0.5
OVERLOAD_SLEEP = 2.0
JITTER_RATIO = 0.25
CIRCUIT_FAILURE_THRESHOLD = 2
CIRCUIT_COOLDOWN_SECONDS = 30.0


class CircuitOpenError(Exception):
	"""Raised when repeated 429/529 have opened the client circuit."""


class LLMClient(Protocol):
	def complete(
		self,
		*,
		model: str,
		system: str,
		messages: list[dict[str, Any]],
		tools: list[dict[str, Any]],
		max_tokens: int,
	) -> LLMResponse:
		...


class FakeClient:
	"""Scripted adapter for tests. Each complete() pops the next response."""

	def __init__(self, script: list[LLMResponse]) -> None:
		self.script = list(script)
		self.calls: list[dict[str, Any]] = []

	def complete(
		self,
		*,
		model: str,
		system: str,
		messages: list[dict[str, Any]],
		tools: list[dict[str, Any]],
		max_tokens: int,
	) -> LLMResponse:
		self.calls.append(
			{
				"model": model,
				"system": system,
				"messages": messages,
				"tools": tools,
				"max_tokens": max_tokens,
			}
		)
		if not self.script:
			raise AssertionError("FakeClient has no more scripted responses")
		return self.script.pop(0)


def text_response(text: str) -> LLMResponse:
	content = [{"type": "text", "text": text}]
	return LLMResponse(
		stop_reason="end_turn",
		text=text,
		tool_uses=[],
		raw_content=content,
	)


def tool_response(tool_id: str, name: str, arguments: dict[str, Any], text: str = "") -> LLMResponse:
	blocks: list[dict[str, Any]] = []
	if text:
		blocks.append({"type": "text", "text": text})
	blocks.append(
		{
			"type": "tool_use",
			"id": tool_id,
			"name": name,
			"input": arguments,
		}
	)
	return LLMResponse(
		stop_reason="tool_use",
		text=text,
		tool_uses=[ToolUse(id=tool_id, name=name, input=arguments)],
		raw_content=blocks,
	)


class AnthropicClient:
	def __init__(
		self,
		client: Any,
		sleep: Callable[[float], None] | None = None,
		rng: Callable[[], float] | None = None,
		clock: Callable[[], float] | None = None,
	) -> None:
		self._client = client
		self._sleep = sleep or time.sleep
		self._rng = rng or random.random
		self._clock = clock or time.monotonic
		self._consecutive_failures = 0
		self._circuit_until: float | None = None

	def complete(
		self,
		*,
		model: str,
		system: str,
		messages: list[dict[str, Any]],
		tools: list[dict[str, Any]],
		max_tokens: int,
	) -> LLMResponse:
		self._raise_if_circuit_open()
		rate_tries = 0
		compacted = False
		while True:
			try:
				response = self._client.messages.create(
					model=model,
					system=system,
					messages=messages,
					tools=tools,
					max_tokens=max_tokens,
				)
			except Exception as error:
				if _is_prompt_too_long(error) and not compacted:
					prepare_context(messages, "")
					compacted = True
					continue
				status = _status_code(error)
				if status in {429, 529} and rate_tries < MAX_RATE_RETRIES:
					base = OVERLOAD_SLEEP if status == 529 else RATE_LIMIT_SLEEP
					self._sleep(_retry_delay(base, rate_tries, self._rng()))
					rate_tries += 1
					continue
				if status in {429, 529}:
					self._note_rate_failure()
				raise
			self._consecutive_failures = 0
			self._circuit_until = None
			return _parse_response(response)

	def _raise_if_circuit_open(self) -> None:
		if self._circuit_until is None:
			return
		if self._clock() < self._circuit_until:
			raise CircuitOpenError(
				"LLM circuit is open after repeated 429/529; wait before retrying"
			)
		self._circuit_until = None

	def _note_rate_failure(self) -> None:
		self._consecutive_failures += 1
		if self._consecutive_failures >= CIRCUIT_FAILURE_THRESHOLD:
			self._circuit_until = self._clock() + CIRCUIT_COOLDOWN_SECONDS


def _retry_delay(base: float, attempt: int, unit_interval: float) -> float:
	backoff = base * (2 ** attempt)
	jitter = max(0.0, min(1.0, unit_interval))
	return backoff * (1 + JITTER_RATIO * jitter)


def _parse_response(response: Any) -> LLMResponse:
	tool_uses: list[ToolUse] = []
	texts: list[str] = []
	for block in response.content:
		kind = getattr(block, "type", None)
		if kind == "tool_use":
			tool_uses.append(
				ToolUse(
					id=block.id,
					name=block.name,
					input=dict(block.input or {}),
				)
			)
		elif kind == "text":
			texts.append(block.text or "")
	return LLMResponse(
		stop_reason=response.stop_reason or "end_turn",
		text="".join(texts),
		tool_uses=tool_uses,
		raw_content=response.content,
	)


def _status_code(error: BaseException) -> int | None:
	return getattr(error, "status_code", None)


def _is_prompt_too_long(error: BaseException) -> bool:
	return "prompt is too long" in str(error).lower()
