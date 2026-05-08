from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_github_repo_governance_mentions_current_required_jobs() -> None:
    governance = (ROOT / "docs" / "governance" / "GITHUB_REPO_GOVERNANCE.md").read_text(encoding="utf-8")

    for job_name in (
        "repo-hygiene-and-architecture",
        "runtime-contract-tests",
        "product-pages-browser-e2e",
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
        "runtime-contract-tests",
        "product-pages-browser-e2e",
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


def test_merge_governance_workflow_is_manual_or_scheduled_advisory_only() -> None:
    workflow = (ROOT / ".github" / "workflows" / "merge-governance.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch" in workflow
    assert "pull_request" not in workflow
    assert "merge_group" not in workflow
    assert "pull-requests: read" in workflow
    assert "fetch-depth: 0" in workflow
    assert "git fetch origin '+refs/heads/*:refs/remotes/origin/*' --prune" in workflow
    assert "python scripts/merge_governance/build_merge_governance_advisory.py" in workflow
    assert "--skip-diff-scan --limit 40" in workflow
    assert "merge-governance-advisory" in workflow
    assert "artifacts/merge_governance_advisory.json" in workflow
    assert "artifacts/merge_governance_advisory.md" in workflow


def test_ci_advisory_workflow_is_manual_only() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci-advisory.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch" in workflow
    assert "pull_request" not in workflow
    assert "merge_group" not in workflow
    assert "pre-edd-readiness" in workflow
    assert "accurate-intake-mvp-gate" in workflow
    assert "wave1-phase-a-contracts" in workflow


def test_required_runtime_contract_wall_does_not_run_pre_edd_readiness() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "tests/test_pre_edd_readiness.py" not in workflow


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


def test_agents_bootstrap_uses_current_docs_index_and_operating_entry() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "[docs/DOC_INDEX.md]" in agents
    assert "[docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md]" in agents
    assert "docs/_spec_snapshots" in agents
    assert "[docs/V2_DOC_INDEX.md]" not in agents
    assert "[docs/specs/APP_V2_ENGINEERING_OPERATING_ENTRY.md]" not in agents
    assert "artifacts/docs-snapshots" not in agents


def test_docs_bootstrap_index_and_legacy_reference_are_consistent() -> None:
    doc_index = (ROOT / "docs" / "DOC_INDEX.md").read_text(encoding="utf-8")
    operating_entry = (ROOT / "docs" / "specs" / "APP_ENGINEERING_OPERATING_ENTRY.md").read_text(encoding="utf-8")
    legacy_index = (ROOT / "docs" / "specs" / "LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md").read_text(encoding="utf-8")
    docs_index_stub = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    v2_index_stub = (ROOT / "docs" / "V2_DOC_INDEX.md").read_text(encoding="utf-8")

    assert "sole active docs index: `docs/DOC_INDEX.md`" in doc_index
    assert "`docs/index.md` is compatibility-only and must stay thin" in doc_index
    assert "`docs/V2_DOC_INDEX.md` is compatibility-only and must stay thin" in doc_index
    assert "sole active operating entry: `docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md`" in doc_index
    assert "sole legacy runtime reference index: `docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md`" in doc_index
    assert "canonical preservation path: `docs/_spec_snapshots/`" in doc_index
    assert "Current Shell" in operating_entry
    assert "stop and return to [docs/DOC_INDEX.md]" in docs_index_stub
    assert "stop and return to [docs/DOC_INDEX.md]" in v2_index_stub
    assert "docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md" in legacy_index
    assert "docs/specs/APP_V2_IMPLEMENTATION_PLAN.md" in legacy_index


def test_provider_docs_do_not_hardlink_missing_local_artifacts() -> None:
    provider_profile = (ROOT / "docs" / "provider" / "BUILDERSPACE_PROVIDER_PROFILE.md").read_text(encoding="utf-8")
    candidate_matrix = (ROOT / "docs" / "provider" / "MANAGER_MODEL_CANDIDATE_MATRIX.md").read_text(encoding="utf-8")

    assert "Historical local artifact filenames referenced in older provider diagnostics are no longer retained in tracked repo state." in provider_profile
    assert "Historical local candidate-eval artifact filenames from the first BuilderSpace pass are no longer retained in tracked repo state." in candidate_matrix
    assert "](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/artifacts/" not in provider_profile
    assert "](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/artifacts/" not in candidate_matrix
