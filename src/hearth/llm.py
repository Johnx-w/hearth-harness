from __future__ import annotations

from typing import Any, Protocol

from hearth.types import LLMResponse, ToolUse


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
	def __init__(self, client: Any) -> None:
		self._client = client

	def complete(
		self,
		*,
		model: str,
		system: str,
		messages: list[dict[str, Any]],
		tools: list[dict[str, Any]],
		max_tokens: int,
	) -> LLMResponse:
		response = self._client.messages.create(
			model=model,
			system=system,
			messages=messages,
			tools=tools,
			max_tokens=max_tokens,
		)
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
