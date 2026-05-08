from __future__ import annotations

from pathlib import Path

from scripts.clean_local_workspace import clean_workspace, plan_cleanup


def test_clean_local_workspace_removes_disposable_scratch_but_preserves_data_roots(tmp_path: Path) -> None:
    for relative in (
        ".pytest_cache",
        ".pytest_tmp_case",
        ".ruff_cache",
        ".codex_tmp",
        ".import_linter_cache",
        "runtime",
        "app/__pycache__",
    ):
        (tmp_path / relative).mkdir(parents=True)

    for relative in (
        ".git",
        ".env",
        "artifacts",
        "workspace_data/local_dogfood",
        "docs/_spec_snapshots",
    ):
        path = tmp_path / relative
        if path.suffix:
            path.write_text("secret", encoding="utf-8")
        else:
            path.mkdir(parents=True)

    report = clean_workspace(tmp_path)

    assert report["removed_count"] == 7
    assert ".pytest_cache" in report["removed"]
    assert ".pytest_tmp_case" in report["removed"]
    assert ".codex_tmp" in report["removed"]
    assert "app/__pycache__" in report["removed"]
    assert not (tmp_path / ".pytest_cache").exists()
    assert not (tmp_path / "app" / "__pycache__").exists()
    assert (tmp_path / ".env").exists()
    assert (tmp_path / "artifacts").exists()
    assert (tmp_path / "workspace_data" / "local_dogfood").exists()
    assert (tmp_path / "docs" / "_spec_snapshots").exists()


def test_clean_local_workspace_keeps_local_tooling_unless_explicitly_included(tmp_path: Path) -> None:
    (tmp_path / ".devcontainer").mkdir()
    (tmp_path / ".kiro").mkdir()

    assert plan_cleanup(tmp_path) == []

    dry_run = clean_workspace(tmp_path, dry_run=True, include_local_tooling=True)
    assert dry_run["planned"] == [".devcontainer", ".kiro"]
    assert dry_run["removed"] == []
    assert (tmp_path / ".devcontainer").exists()
    assert (tmp_path / ".kiro").exists()

    report = clean_workspace(tmp_path, include_local_tooling=True)

    assert report["removed"] == [".devcontainer", ".kiro"]
    assert not (tmp_path / ".devcontainer").exists()
    assert not (tmp_path / ".kiro").exists()
