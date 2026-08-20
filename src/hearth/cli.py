from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from hearth.config import max_turns, model_id, workspace_root
from hearth.goal import GoalGate
from hearth.hooks import Hooks
from hearth.llm import AnthropicClient
from hearth.loop import Session, last_assistant_text, run_turn
from hearth.mcp import McpHub
from hearth.memory import extract_after_turn
from hearth.permission import Permission
from hearth.types import ToolUse


def _ask(prompt: str) -> bool:
	try:
		answer = input(prompt).strip().lower()
	except EOFError:
		return False
	return answer in {"y", "yes"}


def build_session(
	workspace: Path,
	*,
	auto_allow_shell: bool = False,
) -> Session:
	load_dotenv(override=True)
	if os.getenv("ANTHROPIC_BASE_URL"):
		os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
	client = AnthropicClient(
		Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
	)
	hub = McpHub()
	hooks = Hooks()
	hooks.register(
		"PreToolUse",
		Permission(
			workspace,
			ask=_ask,
			auto_allow_shell=auto_allow_shell,
			mcp_servers=hub.servers,
		),
	)
	hooks.register("PostToolUse", _log_tool)
	hooks.register("Stop", lambda messages: _on_stop(workspace, messages))
	return Session(
		workspace=workspace,
		client=client,
		model=model_id(),
		hooks=hooks,
		goal=GoalGate(),
		max_turns=max_turns(),
		mcp=hub,
	)


def _on_stop(workspace: Path, messages: list) -> None:
	extract_after_turn(workspace, messages)
	return None


def _log_tool(block: ToolUse, output: str) -> None:
	print(f"> {block.name}")
	print(str(output)[:400])


def run_query(session: Session, query: str) -> str:
	session.hooks.emit("UserPromptSubmit", query)
	session.active_request = query
	session.messages.append({"role": "user", "content": query})
	turn_start = len(session.messages)
	result = run_turn(session)
	text = result.text or last_assistant_text(session.messages[turn_start:])
	if result.status not in {"allow", "end_turn", "achieved"} and result.reason:
		print(f"[{result.status}] {result.reason}")
	return text


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(prog="hearth")
	parser.add_argument("query", nargs="?", help="Run one request and exit")
	parser.add_argument(
		"--yes",
		action="store_true",
		help="Do not prompt for bash approval (still denies the deny-list)",
	)
	args = parser.parse_args(argv)
	workspace = workspace_root()
	try:
		session = build_session(workspace, auto_allow_shell=args.yes)
	except KeyError as error:
		print(f"Missing environment variable: {error}", file=sys.stderr)
		print("Copy .env.example to .env", file=sys.stderr)
		return 1

	print(f"Hearth  workspace={workspace}")
	if args.query:
		print(run_query(session, args.query))
		return 0

	print("Type a task, or q to quit.\n")
	while True:
		try:
			query = input("hearth >> ").strip()
		except (EOFError, KeyboardInterrupt):
			print()
			return 0
		if query.lower() in {"q", "exit", "quit"}:
			return 0
		if not query:
			continue
		text = run_query(session, query)
		if text:
			print(text)
		print()


if __name__ == "__main__":
	raise SystemExit(main())
