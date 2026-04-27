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
