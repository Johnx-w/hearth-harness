from __future__ import annotations

import threading
from typing import Any

from hearth.tools.bash import run_bash
from hearth.types import ToolUse


def inject_inbound(
	messages: list[dict[str, Any]],
	inbound: list[dict[str, Any]] | None = None,
	cron: Any | None = None,
	now: float | None = None,
) -> None:
	"""Cron prompts and background notifications land here."""
	if inbound is None:
		inbound = []
	if cron is not None:
		cron.flush_due(inbound, now)
	if not inbound:
		return
	drained = inbound[:]
	inbound.clear()
	messages.extend(drained)


def should_run_background(block: ToolUse) -> bool:
	if block.name != "bash":
		return False
	flag = block.input.get("run_in_background")
	return flag is True or flag == "true"


def start_background(session: Any, block: ToolUse) -> None:
	def work() -> None:
		output = run_bash(dict(block.input), session.workspace)
		session.inbound.append(
			{
				"role": "user",
				"content": (
					f"[Background task completed] {block.name} ({block.id})\n{output}"
				),
			}
		)

	if getattr(session, "sync_background", False):
		work()
		return
	threading.Thread(target=work, daemon=True).start()
