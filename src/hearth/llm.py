from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Protocol

from hearth.compact import prepare_context
from hearth.types import LLMResponse, ToolUse

MAX_RATE_RETRIES = 3
RATE_LIMIT_SLEEP = 0.5


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
	) -> None:
		self._client = client
		self._sleep = sleep or time.sleep

	def complete(
		self,
		*,
		model: str,
		system: str,
		messages: list[dict[str, Any]],
		tools: list[dict[str, Any]],
		max_tokens: int,
	) -> LLMResponse:
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
				if _is_rate_limited(error) and rate_tries < MAX_RATE_RETRIES:
					self._sleep(RATE_LIMIT_SLEEP * (2 ** rate_tries))
					rate_tries += 1
					continue
				raise
			return _parse_response(response)


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


def _is_rate_limited(error: BaseException) -> bool:
	return getattr(error, "status_code", None) in {429, 529}


def _is_prompt_too_long(error: BaseException) -> bool:
	return "prompt is too long" in str(error).lower()
