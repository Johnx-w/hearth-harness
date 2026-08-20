from __future__ import annotations

import threading
import time
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
	thread = threading.Thread(target=work, daemon=True)
	thread.start()
	threads = getattr(session, "background_threads", None)
	if threads is not None:
		threads.append(thread)


def is_background_running(session: Any) -> bool:
	threads = getattr(session, "background_threads", [])
	return any(thread.is_alive() for thread in threads)


def wait_for_background(session: Any, timeout: float | None = None) -> None:
	"""Block until background threads finish or the wait budget runs out."""
	if timeout is None:
		timeout = float(getattr(session, "background_wait_timeout", 30.0))
	deadline = time.monotonic() + timeout
	while is_background_running(session):
		remaining = deadline - time.monotonic()
		if remaining <= 0:
			return
		alive = [
			thread
			for thread in getattr(session, "background_threads", [])
			if thread.is_alive()
		]
		if not alive:
			return
		alive[0].join(timeout=min(0.25, remaining))
