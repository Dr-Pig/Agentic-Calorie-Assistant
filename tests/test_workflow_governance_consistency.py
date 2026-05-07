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


def test_github_repo_governance_documents_current_shell_cutover_rules() -> None:
    governance = (ROOT / "docs" / "governance" / "GITHUB_REPO_GOVERNANCE.md").read_text(encoding="utf-8")

    assert "`CurrentShell`" in governance
    assert "`PLCE`" in governance
    assert "`owner_lane`" in governance


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
    assert "--skip-diff-scan --limit 40" in workflow
    assert "github.event_name != 'merge_group'" in workflow
    assert "name: merge-debt-matrix" in workflow
    assert "artifacts/pre_pr_quality_gate_report.json" in workflow
    assert "artifacts/pre_queue_readiness_report.json" in workflow
    assert "artifacts/merge_debt_matrix.json" in workflow
    assert "artifacts/merge_debt_matrix.md" in workflow


def test_current_shell_sync_contract_uses_canonical_track_and_conservative_launch_scope() -> None:
    contract = (ROOT / "docs" / "quality" / "CURRENT_SHELL_SYNC_CONTRACT.yaml").read_text(encoding="utf-8")

    assert "canonical_machine_track: CurrentShell" in contract
    assert "launch_claim_scope: none" in contract
    assert "track_alias_target" not in contract
    assert "gate_advanced" not in contract

    for alias in (
        "PLCE",
        "PL_CE",
        "PL/CE",
        "PL-CE",
        "ProductLoop",
        "ProductLifecycleContextEngineering",
    ):
        assert f"  - {alias}" in contract


def test_pull_request_template_includes_owner_lane_and_required_report_keys() -> None:
    template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")

    assert "track: fill_me" in template
    assert "`track: CurrentShell`" in template
    assert "`track: FoodDB`" in template
    assert "`track: MergeGovernance`" in template
    assert "owner_lane: none" in template
    assert "runtime_truth_changed: false" in template
    assert "manager_context_packet_changed: false" in template
    assert "mutation_changed: false" in template
    assert "product_readiness_claimed: false" in template
    assert "launch_claim_scope: none" in template
    assert "track_alias_target" not in template
    assert "gate_advanced" not in template
