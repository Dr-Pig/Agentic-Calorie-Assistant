from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_github_repo_governance_mentions_current_required_jobs() -> None:
    governance = (ROOT / "docs" / "governance" / "GITHUB_REPO_GOVERNANCE.md").read_text(encoding="utf-8")

    for job_name in (
        "repo-hygiene-and-architecture",
        "pre-edd-readiness",
        "runtime-contract-tests",
        "wave1-phase-a-contracts",
        "wave1-phase-b-contracts",
    ):
        assert f"`{job_name}`" in governance


def test_github_repo_governance_defines_merge_queue_delivery_policy() -> None:
    governance = (ROOT / "docs" / "governance" / "GITHUB_REPO_GOVERNANCE.md").read_text(encoding="utf-8")

    assert "Merge Queue Delivery Policy" in governance
    assert "mode: merge_queue_serial" in governance
    assert "Add to Merge Queue" in governance
    assert "wait for PR state MERGED" in governance
    assert "do not use main-merge-lock" in governance
    assert "cleanup only after merged and clean" in governance
    assert "dependent_child_pr" in governance
    assert "mode: stop_for_human_gate" in governance


def test_github_repo_governance_defines_branch_worktree_hygiene_policy() -> None:
    governance = (ROOT / "docs" / "governance" / "GITHUB_REPO_GOVERNANCE.md").read_text(encoding="utf-8")

    assert "Active Branch / Worktree Hygiene Policy" in governance
    assert "one active branch/worktree per active builder window" in governance
    assert "at most one temporary steward branch/worktree" in governance
    assert "duplicate local branches for the same open PR are forbidden" in governance


def test_harness_go_no_go_mentions_current_required_jobs() -> None:
    harness = (ROOT / "docs" / "governance" / "HARNESS_GO_NO_GO.md").read_text(encoding="utf-8")

    for job_name in (
        "repo-hygiene-and-architecture",
        "pre-edd-readiness",
        "runtime-contract-tests",
        "wave1-phase-a-contracts",
        "wave1-phase-b-contracts",
    ):
        assert f"`{job_name}`" in harness


def test_cd_workflow_is_manual_placeholder_only() -> None:
    workflow = (ROOT / ".github" / "workflows" / "cd.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch" in workflow
    assert "docker/build-push-action" not in workflow
    assert "DEPLOY_WEBHOOK_URL" not in workflow
    assert "Manual placeholder only." in workflow


def test_wave1_runtime_smoke_stays_manual_only() -> None:
    workflow = (ROOT / ".github" / "workflows" / "wave1-runtime-smoke.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch" in workflow
    assert "pull_request" not in workflow
    assert "push:" not in workflow


def test_merge_governance_workflow_builds_and_uploads_advisory_matrix() -> None:
    workflow = (ROOT / ".github" / "workflows" / "merge-governance.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch" in workflow
    assert "pull_request" in workflow
    assert "schedule:" in workflow
    assert "pull-requests: read" in workflow
    assert "fetch-depth: 0" in workflow
    assert "git fetch origin '+refs/heads/*:refs/remotes/origin/*' --prune" in workflow
    assert "python scripts/merge_governance/pre_pr_quality_gate.py" in workflow
    assert "python scripts/merge_governance/check_pre_queue_readiness.py" in workflow
    assert "python scripts/merge_governance/build_merge_debt_matrix.py" in workflow
    assert "name: merge-debt-matrix" in workflow
    assert "artifacts/pre_pr_quality_gate_report.json" in workflow
    assert "artifacts/pre_queue_readiness_report.json" in workflow
    assert "artifacts/merge_debt_matrix.json" in workflow
    assert "artifacts/merge_debt_matrix.md" in workflow


def test_pull_request_template_requires_current_shell_lane_metadata() -> None:
    template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")

    for field in (
        "track: PLCE",
        "owner_lane:",
        "slice_class:",
        "pass_type:",
        "upstream_runtime_gate:",
        "launch_claim_scope:",
        "shell_surface_impacted:",
        "non_claims:",
        "READY_FOR_QUEUE",
    ):
        assert field in template
