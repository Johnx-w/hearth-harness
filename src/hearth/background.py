from __future__ import annotations

from typing import Any

from hearth.types import ToolUse


def inject_inbound(messages: list[dict[str, Any]]) -> None:
	"""v1/v2: cron prompts and background task_notification land here."""
	del messages


def should_run_background(block: ToolUse) -> bool:
	del block
	return False
