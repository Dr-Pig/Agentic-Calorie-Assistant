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
SCRIPT = "scripts/run_advanced_product_lab_memory_feedback_live_diagnostic.py"


def test_memory_feedback_fake_diagnostic_projects_confirm_reject_and_correct_without_promotion() -> None:
    from app.advanced_shadow_lab.product_lab_memory_feedback_live_diagnostic import (
        FakeMemoryFeedbackProvider,
        run_memory_feedback_live_diagnostic,
    )

    artifact = run_memory_feedback_live_diagnostic(
        provider=FakeMemoryFeedbackProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    reports = {report["case_id"]: report for report in artifact["case_reports"]}
    assert artifact["status"] == "pass"
    assert artifact["case_count"] == 3
    assert reports["memory_confirm_validator_input"]["projection_type"] == (
        "memory_confirmation_validator_input"
    )
    assert reports["memory_reject_validator_input"]["projection_type"] == (
        "feedback_validator_input"
    )
    assert reports["memory_correct_validator_input"]["projection_type"] == (
        "feedback_validator_input"
    )
    assert artifact["confirmed_memory_promoted"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["diagnostic_evidence_class"] == "fake_contract"


def test_memory_feedback_live_diagnostic_blocks_provider_review_that_claims_promotion() -> None:
    from app.advanced_shadow_lab.product_lab_memory_feedback_live_diagnostic import (
        FakeMemoryFeedbackProvider,
        run_memory_feedback_live_diagnostic,
    )

    artifact = run_memory_feedback_live_diagnostic(
        provider=FakeMemoryFeedbackProvider(corrupt_review=True),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    assert artifact["status"] == "blocked"
    assert "provider_review.confirmed_memory_promoted" in artifact["blockers"]
    assert "provider_review.durable_memory_written" in artifact["blockers"]
    assert artifact["semantic_hardening_allowed"] is False


def test_memory_feedback_cli_fake_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "memory-feedback-fake.json"

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
    assert artifact["live_memory_feedback_projection_pass"] is False
    assert artifact["live_edd_preflight"]["reviewed_preflight_status"] == (
        "fake_contract_preflight_passed_non_live"
    )


def test_memory_feedback_cli_blocks_live_without_gate(tmp_path: Path) -> None:
    output = tmp_path / "memory-feedback-blocked-live.json"

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
