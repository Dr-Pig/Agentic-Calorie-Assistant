from __future__ import annotations

from pathlib import Path

from scripts.merge_governance import main_merge_lock


def _entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "pr_number": 12,
        "title": "Ready FoodDB slice",
        "track": "FoodDB",
        "base_branch": "main",
        "head_branch": "codex/ready-fooddb-slice",
        "mainline_status": "mvp_mainline",
        "ci_status": "pass",
        "advisory_check_status": "pass",
        "base_drift_status": "current",
        "boundary_status": "pass",
        "deterministic_boundary_status": "pass",
        "runtime_activation_status": "inactive",
        "fat_file_status": "pass",
        "recommended_verdict": "merge_candidate",
        "blocking_reasons": [],
        "is_draft": False,
        "merge_state_status": "CLEAN",
    }
    entry.update(overrides)
    return entry


def test_main_merge_lock_accepts_current_clean_ready_candidate() -> None:
    result = main_merge_lock.evaluate_candidate(
        _entry(),
        pr_body="track: FoodDB\nREADY_FOR_QUEUE\n",
        main_branch="main",
    )

    assert result["status"] == "pass"
    assert result["allowed_verdicts"] == ["merge_candidate"]


def test_main_merge_lock_rejects_missing_ready_marker() -> None:
    result = main_merge_lock.evaluate_candidate(
        _entry(),
        pr_body="track: FoodDB\n",
        main_branch="main",
    )

    assert result["status"] == "fail"
    assert "missing_ready_marker:READY_FOR_QUEUE" in result["blocking_reasons"]
    report = result["integrator_blocker_report"]
    assert report["artifact_type"] == "main_merge_lock_integrator_blocker_report"
    assert report["blocker_type"] == "mechanical"
    assert report["owning_track"] == "FoodDB"
    assert report["can_integrator_fix"] is True
    assert report["next_integrator_action"] == "fix_and_retry"


def test_main_merge_lock_rejects_matrix_blocking_reasons_even_with_merge_candidate() -> None:
    result = main_merge_lock.evaluate_candidate(
        _entry(blocking_reasons=["missing_track_report_key:track"]),
        pr_body="READY_FOR_QUEUE\n",
        main_branch="main",
    )

    assert result["status"] == "fail"
    assert "matrix_blocking_reason:missing_track_report_key:track" in result["blocking_reasons"]
    report = result["integrator_blocker_report"]
    assert report["blocker_type"] == "semantic"
    assert report["owning_track"] == "FoodDB"
    assert report["can_integrator_fix"] is False
    assert report["next_integrator_action"] == "block_until_owner_fix"


def test_main_merge_lock_rejects_stale_draft_or_unstable_candidate() -> None:
    for override, expected in [
        ({"base_drift_status": "stale_to_main"}, "base_drift_status_not_current:stale_to_main"),
        ({"ci_status": "pending"}, "ci_status_not_pass:pending"),
        ({"is_draft": True}, "draft_pr_not_mergeable"),
        ({"merge_state_status": "UNSTABLE"}, "merge_state_not_clean:UNSTABLE"),
        ({"base_branch": "codex/stack-base"}, "base_branch_not_main:codex/stack-base"),
    ]:
        result = main_merge_lock.evaluate_candidate(
            _entry(**override),
            pr_body="READY_FOR_QUEUE\n",
            main_branch="main",
        )

        assert result["status"] == "fail"
        assert expected in result["blocking_reasons"]


def test_main_merge_lock_rejects_boundary_runtime_and_size_failures() -> None:
    for override, expected in [
        ({"boundary_status": "needs_review"}, "boundary_status_not_pass:needs_review"),
        ({"deterministic_boundary_status": "needs_review"}, "deterministic_boundary_status_not_pass:needs_review"),
        ({"runtime_activation_status": "active"}, "runtime_activation_status_not_inactive:active"),
        ({"fat_file_status": "warning"}, "fat_file_status_not_pass:warning"),
    ]:
        result = main_merge_lock.evaluate_candidate(
            _entry(**override),
            pr_body="READY_FOR_QUEUE\n",
            main_branch="main",
        )

        assert result["status"] == "fail"
        assert expected in result["blocking_reasons"]


def test_main_merge_lock_marks_boundary_failures_as_contract_gap() -> None:
    result = main_merge_lock.evaluate_candidate(
        _entry(boundary_status="needs_review"),
        pr_body="READY_FOR_QUEUE\n",
        main_branch="main",
    )

    report = result["integrator_blocker_report"]
    assert report["blocker_type"] == "contract_gap"
    assert report["can_integrator_fix"] is False
    assert "boundary_status_not_pass:needs_review" in report["evidence"]


def test_main_merge_lock_allows_dormant_shadow_only_when_explicitly_enabled() -> None:
    dormant = _entry(
        recommended_verdict="dormant_shadow_candidate",
        mainline_status="future_shadow",
        fat_file_status="warning",
    )

    blocked = main_merge_lock.evaluate_candidate(
        dormant,
        pr_body="READY_FOR_QUEUE\n",
        main_branch="main",
    )
    allowed = main_merge_lock.evaluate_candidate(
        dormant,
        pr_body="READY_FOR_QUEUE\n",
        main_branch="main",
        allow_dormant_shadow=True,
    )

    assert blocked["status"] == "fail"
    assert "verdict_not_allowed:dormant_shadow_candidate" in blocked["blocking_reasons"]
    assert allowed["status"] == "pass"
    assert allowed["allowed_verdicts"] == ["merge_candidate", "dormant_shadow_candidate"]


def test_main_merge_lock_expected_check_names_include_required_and_advisory() -> None:
    names = main_merge_lock.expected_lock_check_names(
        {
            "required_checks": ["repo-hygiene-and-architecture", "runtime-contract-tests"],
            "advisory_checks": ["phase-c-environment-gate", "repo-hygiene-and-architecture"],
        }
    )

    assert names == ["repo-hygiene-and-architecture", "runtime-contract-tests", "phase-c-environment-gate"]


def test_main_merge_lock_wait_readiness_accepts_clean_passed_checks() -> None:
    result = main_merge_lock.evaluate_wait_readiness(
        {
            "mergeStateStatus": "CLEAN",
            "statusCheckRollup": [
                {"name": "repo-hygiene-and-architecture", "status": "COMPLETED", "conclusion": "SUCCESS"},
                {"name": "phase-c-environment-gate", "status": "COMPLETED", "conclusion": "SUCCESS"},
            ],
        },
        expected_checks=["repo-hygiene-and-architecture", "phase-c-environment-gate"],
    )

    assert result["status"] == "pass"


def test_main_merge_lock_wait_readiness_waits_for_unknown_state_and_missing_checks() -> None:
    result = main_merge_lock.evaluate_wait_readiness(
        {
            "mergeStateStatus": "UNKNOWN",
            "statusCheckRollup": [
                {"name": "repo-hygiene-and-architecture", "status": "IN_PROGRESS", "conclusion": ""},
            ],
        },
        expected_checks=["repo-hygiene-and-architecture", "phase-c-environment-gate"],
    )

    assert result["status"] == "pending"
    assert "pending_check:repo-hygiene-and-architecture" in result["pending_reasons"]
    assert "missing_check:phase-c-environment-gate" in result["pending_reasons"]
    assert "merge_state_not_clean:UNKNOWN" in result["pending_reasons"]


def test_main_merge_lock_wait_readiness_fails_failed_checks_and_dirty_state() -> None:
    result = main_merge_lock.evaluate_wait_readiness(
        {
            "mergeStateStatus": "DIRTY",
            "statusCheckRollup": [
                {"name": "repo-hygiene-and-architecture", "status": "COMPLETED", "conclusion": "FAILURE"},
                {"name": "phase-c-environment-gate", "status": "COMPLETED", "conclusion": "SUCCESS"},
            ],
        },
        expected_checks=["repo-hygiene-and-architecture", "phase-c-environment-gate"],
    )

    assert result["status"] == "fail"
    assert "failed_check:repo-hygiene-and-architecture" in result["failed_reasons"]
    assert "merge_state_not_clean:DIRTY" in result["failed_reasons"]


def test_main_merge_lock_workflow_serializes_main_promotion() -> None:
    workflow = Path(".github/workflows/main-merge-lock.yml").read_text(encoding="utf-8")

    assert "concurrency:" in workflow
    assert "group: main-merge-lock-main" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "MAIN_MERGE_TOKEN" in workflow
    assert "persist-credentials: false" in workflow
    assert "main_merge_lock.py wait-ready" in workflow
    assert "python scripts/merge_governance/main_merge_lock.py assert-candidate" in workflow
    assert "expected_base_sha" in workflow
    assert "queue_race_retry" in workflow
    assert "gh pr merge" in workflow
