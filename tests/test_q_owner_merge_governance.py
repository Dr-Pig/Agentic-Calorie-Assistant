from __future__ import annotations

from scripts.merge_governance import build_branch_worktree_cleanup_report, build_q_owner_queue


def _matrix_entry(
    *,
    pr_number: int,
    verdict: str,
    track: str = "FoodDB",
    ci_status: str = "pass",
    base_drift_status: str = "current",
    merge_state_status: str = "CLEAN",
) -> dict[str, object]:
    return {
        "pr_number": pr_number,
        "title": f"PR {pr_number}",
        "url": f"https://example.test/pull/{pr_number}",
        "track": track,
        "base_branch": "main",
        "head_branch": f"codex/pr-{pr_number}",
        "stack_role": "standalone",
        "stack_depth": 1,
        "mainline_status": "mvp_mainline",
        "ci_status": ci_status,
        "advisory_check_status": "pass",
        "base_drift_status": base_drift_status,
        "boundary_status": "pass",
        "deterministic_boundary_status": "pass",
        "runtime_activation_status": "inactive",
        "fat_file_status": "pass",
        "recommended_verdict": verdict,
        "blocking_reasons": [] if verdict == "merge_candidate" else ["needs_work"],
        "safe_next_action": "Queue for human review.",
        "additions": 10,
        "deletions": 0,
        "changed_files": 1,
        "is_draft": False,
        "merge_state_status": merge_state_status,
    }


def test_worker_prompt_forbids_agent_self_merge() -> None:
    report = build_q_owner_queue.build_queue_report({"entries": []}, pr_bodies={})

    assert report["policy"]["parallel_build_allowed"] is True
    assert report["policy"]["self_merge_allowed"] is False
    assert report["policy"]["ready_marker"] == "READY_FOR_QUEUE"
    assert "Do not run gh pr merge" in report["worker_prompt"]
    assert "gh workflow run main-merge-lock.yml -f pr_number=<PR_NUMBER>" in report["worker_prompt"]
    assert "READY_FOR_QUEUE" in report["worker_prompt"]


def test_queue_report_selects_only_ready_and_allowed_next_candidate() -> None:
    matrix = {
        "main_branch": "main",
        "entries": [
            _matrix_entry(pr_number=12, verdict="merge_candidate"),
            _matrix_entry(pr_number=11, verdict="merge_candidate"),
            _matrix_entry(pr_number=10, verdict="fix_gate"),
        ],
    }

    report = build_q_owner_queue.build_queue_report(
        matrix,
        pr_bodies={
            12: "track: FoodDB\nREADY_FOR_QUEUE\n",
            11: "track: FoodDB\n",
            10: "track: FoodDB\nREADY_FOR_QUEUE\n",
        },
    )

    by_number = {entry["pr_number"]: entry for entry in report["entries"]}
    assert by_number[12]["queue_status"] == "ready_for_queue"
    assert by_number[12]["five_axis_status"]["base_and_ci"] == "pass"
    assert by_number[12]["five_axis_status"]["boundary_and_runtime"] == "pass"
    assert by_number[12]["five_axis_status"]["deterministic_boundary"] == "pass"
    assert by_number[11]["queue_status"] == "waiting_for_ready_marker"
    assert by_number[10]["queue_status"] == "blocked_by_matrix"
    assert report["next_candidate_pr_number"] == 12
    assert report["script_mutates_repository"] is False


def test_dormant_shadow_candidate_can_queue_with_ready_marker() -> None:
    matrix = {
        "main_branch": "main",
        "entries": [
            _matrix_entry(pr_number=20, verdict="dormant_shadow_candidate", track="RecommendationShadow"),
        ],
    }

    report = build_q_owner_queue.build_queue_report(matrix, pr_bodies={20: "READY_FOR_QUEUE\n"})

    assert report["entries"][0]["queue_status"] == "ready_for_queue"
    assert report["entries"][0]["queue_lane"] == "dormant_shadow"
    assert report["next_candidate_pr_number"] == 20


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
