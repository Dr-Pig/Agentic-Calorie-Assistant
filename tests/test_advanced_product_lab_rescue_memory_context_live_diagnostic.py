from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.shared.infra.json_artifacts import read_json_artifact


ROOT = Path(__file__).resolve().parents[1]
ALLOW_ENV = "ADVANCED_PRODUCT_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
SCRIPT = "scripts/run_advanced_product_lab_rescue_memory_context_live_diagnostic.py"


def test_rescue_memory_context_fake_diagnostic_uses_memory_without_mutation() -> None:
    from app.advanced_shadow_lab.product_lab_rescue_memory_context_live_diagnostic import (
        FakeRescueMemoryContextProvider,
        run_rescue_memory_context_live_diagnostic,
    )

    artifact = run_rescue_memory_context_live_diagnostic(
        provider=FakeRescueMemoryContextProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    reports = {report["case_id"]: report for report in artifact["case_reports"]}
    assert artifact["status"] == "pass"
    assert artifact["case_count"] == 2
    assert reports["scoped_memory_context_used_for_rescue"][
        "memory_summary_projection_used"
    ] is True
    assert reports["scoped_memory_context_used_for_rescue"][
        "proposal_presented_to_lab"
    ] is True
    assert reports["claim_drift_memory_context_rejected"][
        "claim_boundary_blocked"
    ] is True
    assert artifact["provider_review_summary"]["memory_context_used"] is True
    assert artifact["provider_review_summary"]["meal_or_budget_truth_mutated"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["diagnostic_evidence_class"] == "fake_contract"


def test_rescue_memory_context_blocks_provider_review_that_mutates_truth() -> None:
    from app.advanced_shadow_lab.product_lab_rescue_memory_context_live_diagnostic import (
        FakeRescueMemoryContextProvider,
        run_rescue_memory_context_live_diagnostic,
    )

    artifact = run_rescue_memory_context_live_diagnostic(
        provider=FakeRescueMemoryContextProvider(corrupt_review=True),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    assert artifact["status"] == "blocked"
    assert "provider_review.meal_or_budget_truth_mutated" in artifact["blockers"]
    assert "provider_review.rescue_commit_requested" in artifact["blockers"]


def test_rescue_memory_context_cli_fake_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "rescue-memory-context-fake.json"

    result = subprocess.run(
        [sys.executable, SCRIPT, "--output", str(output), "--provider-mode", "fake"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout = json.loads(result.stdout)
    artifact = read_json_artifact(output)
    assert stdout["status"] == "pass"
    assert artifact["status"] == "pass"
    assert artifact["live_rescue_memory_context_diagnostic_pass"] is False
    assert artifact["live_edd_preflight"]["reviewed_preflight_status"] == (
        "fake_contract_preflight_passed_non_live"
    )


def test_rescue_memory_context_cli_blocks_live_without_gate(tmp_path: Path) -> None:
    output = tmp_path / "rescue-memory-context-blocked-live.json"

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--output",
            str(output),
            "--provider-mode",
            "live",
            "--allow-live-provider",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={key: value for key, value in os.environ.items() if key != ALLOW_ENV},
    )

    assert result.returncode == 0, result.stderr
    artifact = read_json_artifact(output)
    assert artifact["status"] == "blocked"
    assert artifact["provider_mode"] == "not_invoked"
    assert artifact["blockers"] == ["live_gate_not_enabled"]
    assert artifact["diagnostic_evidence_class"] == "blocked_not_invoked"
