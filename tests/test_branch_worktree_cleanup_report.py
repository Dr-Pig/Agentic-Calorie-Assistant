from __future__ import annotations

from scripts.merge_governance import build_branch_worktree_cleanup_report


def test_cleanup_classifiers_never_delete_unknown_or_open_work() -> None:
    assert (
        build_branch_worktree_cleanup_report.classify_worktree(
            {
                "path": "C:/Users/User/.config/superpowers/worktrees/Agentic-Calorie-Assistant/done",
                "clean": True,
                "pr_state": "MERGED",
                "inside_approved_root": True,
            }
        )
        == "remove_worktree_candidate"
    )
    assert (
        build_branch_worktree_cleanup_report.classify_worktree(
            {
                "path": "C:/Users/User/.config/superpowers/worktrees/Agentic-Calorie-Assistant/unknown",
                "clean": True,
                "pr_state": None,
                "inside_approved_root": True,
            }
        )
        == "needs_review_no_pr"
    )
    assert (
        build_branch_worktree_cleanup_report.classify_branch(
            {
                "name": "codex/done",
                "pr_state": "MERGED",
                "merged_into_origin_main": True,
                "unpushed_commits": 0,
            }
        )
        == "delete_local_candidate"
    )
    assert (
        build_branch_worktree_cleanup_report.classify_branch(
            {
                "name": "codex/open",
                "pr_state": "OPEN",
                "merged_into_origin_main": False,
                "unpushed_commits": 0,
            }
        )
        == "keep_open_pr"
    )


def test_approved_worktree_root_uses_git_common_dir_project_name(monkeypatch) -> None:
    monkeypatch.setattr(
        build_branch_worktree_cleanup_report,
        "_run_text",
        lambda command: "C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/.git\n"
        if command == ["git", "rev-parse", "--git-common-dir"]
        else "",
    )

    root = build_branch_worktree_cleanup_report._approved_worktree_root()

    assert str(root).endswith("superpowers\\worktrees\\Agentic-Calorie-Assistant")
