from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CRON_FILE = ".cron/jobs.json"

CRON_TOOL = {
	"name": "cron",
	"description": (
		"Schedule a prompt into this session's messages when due. "
		"Delivery is at-least-once. Not a second agent loop."
	),
	"input_schema": {
		"type": "object",
		"properties": {
			"action": {"type": "string"},
			"id": {"type": "string"},
			"prompt": {"type": "string"},
			"delay_seconds": {"type": "number"},
		},
		"required": ["action"],
	},
}


@dataclass
class CronJob:
	id: str
	prompt: str
	due_at: float
	delivered: bool = False


class CronBook:
	def __init__(self, workspace: Path) -> None:
		self.workspace = workspace
		self.jobs: list[CronJob] = []
		self._load()

	def handle(self, args: dict) -> str:
		action = str(args.get("action") or "").strip()
		if action == "list":
			return self.list_text()
		if action == "schedule":
			return self.schedule(
				str(args.get("prompt") or ""),
				float(args.get("delay_seconds") or 0),
				str(args.get("id") or "").strip() or None,
			)
		return "Error: action must be schedule or list"

	def schedule(
		self,
		prompt: str,
		delay_seconds: float = 0,
		job_id: str | None = None,
	) -> str:
		if not prompt.strip():
			return "Error: prompt is required"
		job_id = job_id or f"cron-{len(self.jobs) + 1}"
		due_at = time.time() + max(0.0, delay_seconds)
		self.jobs.append(
			CronJob(id=job_id, prompt=prompt.strip(), due_at=due_at)
		)
		self._save()
		return f"Scheduled {job_id} in {max(0.0, delay_seconds)}s"

	def list_text(self) -> str:
		if not self.jobs:
			return "No cron jobs"
		lines = []
		for job in self.jobs:
			state = "delivered" if job.delivered else "pending"
			lines.append(f"{job.id} [{state}] {job.prompt}")
		return "\n".join(lines)

	def flush_due(
		self,
		inbound: list[dict[str, Any]],
		now: float | None = None,
	) -> int:
		"""Append due prompts, then mark delivered (at-least-once)."""
		stamp = time.time() if now is None else now
		count = 0
		for job in self.jobs:
			if job.delivered or job.due_at > stamp:
				continue
			inbound.append(
				{
					"role": "user",
					"content": f"[Cron] {job.prompt}",
				}
			)
			job.delivered = True
			count += 1
		if count:
			self._save()
		return count

	def _load(self) -> None:
		path = self.workspace / CRON_FILE
		if not path.is_file():
			return
		raw = json.loads(path.read_text(encoding="utf-8"))
		self.jobs = [
			CronJob(
				id=str(item["id"]),
				prompt=str(item["prompt"]),
				due_at=float(item["due_at"]),
				delivered=bool(item.get("delivered")),
			)
			for item in raw.get("jobs", [])
		]

	def _save(self) -> None:
		path = self.workspace / CRON_FILE
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(
			json.dumps({"jobs": [asdict(job) for job in self.jobs]}, indent=2),
			encoding="utf-8",
		)
