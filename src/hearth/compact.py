from __future__ import annotations

from typing import Any

# First-cut budget: ~4 characters per token, no extra tokenizer dependency.
CHARS_PER_TOKEN = 4
CONTEXT_TOKEN_BUDGET = 1000
KEEP_RECENT_MESSAGES = 5
SNIP_PREFIX_CHARS = 200
COMPACT_MARK = "\n[compacted]"


def prepare_context(messages: list[dict[str, Any]], active_request: str) -> None:
	"""Snip old tool_result bodies when the transcript exceeds the token budget."""
	del active_request
	if _estimate_tokens(messages) <= CONTEXT_TOKEN_BUDGET:
		return
	cutoff = max(0, len(messages) - KEEP_RECENT_MESSAGES)
	for message in messages[:cutoff]:
		_snip_tool_results(message)


def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
	total = 0
	for message in messages:
		total += len(_message_text(message))
	return total // CHARS_PER_TOKEN


def _message_text(message: dict[str, Any]) -> str:
	content = message.get("content")
	if isinstance(content, str):
		return content
	if isinstance(content, list):
		parts: list[str] = []
		for block in content:
			if isinstance(block, dict):
				parts.append(str(block.get("content") or block.get("text") or ""))
			else:
				parts.append(str(getattr(block, "text", "") or ""))
		return "".join(parts)
	return str(content or "")


def _snip_tool_results(message: dict[str, Any]) -> None:
	content = message.get("content")
	if not isinstance(content, list):
		return
	for block in content:
		if not isinstance(block, dict) or block.get("type") != "tool_result":
			continue
		body = str(block.get("content") or "")
		if len(body) <= SNIP_PREFIX_CHARS:
			continue
		block["content"] = body[:SNIP_PREFIX_CHARS] + COMPACT_MARK
