from __future__ import annotations

import subprocess
from pathlib import Path

from hearth.tasks import TaskGraph
from hearth.teams import TeamHub, bind_worktree, remove_worktree
from hearth.tools.pool import assemble_tool_pool
from hearth.tools.todo import TodoList


def _git_init(root: Path) -> None:
	subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
	subprocess.run(
		["git", "config", "user.email", "hearth@test"],
		cwd=root,
		check=True,
		capture_output=True,
	)
	subprocess.run(
		["git", "config", "user.name", "Hearth"],
		cwd=root,
		check=True,
		capture_output=True,
	)
	(root / "README.md").write_text("root\n", encoding="utf-8")
	subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
	subprocess.run(
		["git", "commit", "-m", "init"],
		cwd=root,
		check=True,
		capture_output=True,
	)


def test_teammate_spawn_message_and_claim_binds_worktree(tmp_path: Path) -> None:
	_git_init(tmp_path)
	graph = TaskGraph(tmp_path)
	graph.create("ship", "ship it", [])
	hub = TeamHub(tmp_path)
	assert "Spawned alice [IDLE]" in hub.spawn("alice")
	assert "Queued message" in hub.message("alice", "hello")
	out = hub.claim("alice", "ship")
	assert "Claimed ship by alice" in out
	assert "worktree=" in out
	assert hub.teammates["alice"].status == "WORK"
	worktree = tmp_path / ".worktrees" / "ship"
	assert worktree.is_dir()
	assert (worktree / "README.md").is_file()
	listing = assemble_tool_pool(tmp_path, TodoList())[0]
	assert any(tool["name"] == "teammate" for tool in listing)
	assert all(tool["name"] != "remove_worktree" for tool in listing)
	remove_worktree(tmp_path, "ship")
	assert not worktree.exists()


def test_bind_worktree_without_git_still_makes_cwd_dir(tmp_path: Path) -> None:
	path = bind_worktree(tmp_path, "local")
	assert path.is_dir()
	assert path == tmp_path / ".worktrees" / "local"
