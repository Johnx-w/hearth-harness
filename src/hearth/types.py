from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolUse:
	id: str
	name: str
	input: dict[str, Any]


@dataclass
class LLMResponse:
	stop_reason: str
	text: str
	tool_uses: list[ToolUse]
	raw_content: Any


@dataclass(frozen=True)
class StopDecision:
	action: str
	reason: str = ""


@dataclass
class TurnResult:
	text: str
	status: str
	reason: str = ""


@dataclass
class TodoItem:
	id: str
	content: str
	status: str = "pending"
