from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

DEFAULT_MAX_TOKENS = 8000


def workspace_root() -> Path:
	return Path(os.getenv("HEARTH_WORKSPACE", os.getcwd())).resolve()


def model_id() -> str:
	return os.environ["MODEL_ID"]


def api_key() -> str | None:
	return os.getenv("ANTHROPIC_API_KEY")


def max_turns() -> int | None:
	raw = os.getenv("MAX_TURNS", "").strip()
	if not raw:
		return None
	value = int(raw)
	if value < 1:
		raise ValueError("MAX_TURNS must be at least 1")
	return value
