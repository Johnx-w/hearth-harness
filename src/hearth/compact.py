from __future__ import annotations

from typing import Any


def prepare_context(messages: list[dict[str, Any]], active_request: str) -> None:
	"""v1: tool_result budget → snip → micro compact → history summary."""
	del messages, active_request
