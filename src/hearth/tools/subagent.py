from __future__ import annotations

from typing import Any

from hearth.goal import GoalGate

SUBAGENT_TOOL = {
	"name": "subagent",
	"description": (
		"Dispatch a one-shot subagent with its own messages. "
		"The parent only receives a final summary."
	),
	"input_schema": {
		"type": "object",
		"properties": {
			"prompt": {"type": "string"},
		},
		"required": ["prompt"],
	},
}


def run_subagent(args: dict, parent: Any) -> str:
	from hearth.loop import Session, last_assistant_text, run_turn

	prompt = args.get("prompt", "")
	if not isinstance(prompt, str) or not prompt.strip():
		return "Error: prompt must be a non-empty string"
	task = prompt.strip()
	child_turns = 6
	if parent.max_turns is not None:
		child_turns = min(child_turns, parent.max_turns)
	child = Session(
		workspace=parent.workspace,
		client=parent.client,
		model=parent.model,
		hooks=parent.hooks,
		goal=GoalGate(),
		messages=[{"role": "user", "content": task}],
		active_request=task,
		max_turns=child_turns,
		allow_subagent=False,
	)
	result = run_turn(child)
	return (result.text or last_assistant_text(child.messages)).strip() or "(empty summary)"
