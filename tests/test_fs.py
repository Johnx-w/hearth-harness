from pathlib import Path

from hearth.permission import resolve_in_workspace
from hearth.tools.filesystem import WorkspaceFS


def test_edit_requires_unique_old_text(tmp_path: Path) -> None:
	path = tmp_path / "a.py"
	path.write_text("foo\nfoo\n", encoding="utf-8")
	fs = WorkspaceFS(tmp_path)
	out = fs.edit_file({"path": "a.py", "old_text": "foo", "new_text": "bar"})
	assert "2 times" in out


def test_grep_finds_line(tmp_path: Path) -> None:
	(tmp_path / "a.py").write_text("hello hearth\n", encoding="utf-8")
	fs = WorkspaceFS(tmp_path)
	out = fs.grep({"pattern": "hearth"})
	assert "a.py:1:hello hearth" in out


def test_workspace_rejects_escape(tmp_path: Path) -> None:
	try:
		resolve_in_workspace(tmp_path, "../secret")
	except ValueError as error:
		assert "escapes" in str(error)
	else:
		raise AssertionError("expected escape to fail")
