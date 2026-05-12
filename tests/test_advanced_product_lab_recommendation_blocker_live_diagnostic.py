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
SCRIPT = "scripts/run_advanced_product_lab_recommendation_blocker_live_diagnostic.py"


def test_recommendation_blocker_fake_diagnostic_keeps_negative_block_before_offer() -> None:
    from app.advanced_shadow_lab.product_lab_recommendation_blocker_live_diagnostic import (
        FakeRecommendationBlockerProvider,
        run_recommendation_blocker_live_diagnostic,
    )

    artifact = run_recommendation_blocker_live_diagnostic(
        provider=FakeRecommendationBlockerProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    reports = {report["case_id"]: report for report in artifact["case_reports"]}
    assert artifact["status"] == "pass"
    assert artifact["case_count"] == 2
    assert reports["positive_memory_boost_allowed"]["lab_recommendation_served"] is True
    assert reports["negative_block_wins_over_positive_boost"]["blocked_candidate_id"] == (
        "memory-spicy-ramen"
    )
    assert "memory-spicy-ramen" not in reports[
        "negative_block_wins_over_positive_boost"
    ]["allowed_candidate_ids"]
    assert reports["negative_block_wins_over_positive_boost"][
        "blocked_candidate_reason_codes"
    ] == ["confirmed_negative_preference"]
    assert artifact["provider_review_summary"]["blocker_respected"] is True
    assert artifact["lab_recommendation_served"] is True
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["diagnostic_evidence_class"] == "fake_contract"


def test_recommendation_blocker_blocks_provider_review_that_selects_blocked_candidate() -> None:
    from app.advanced_shadow_lab.product_lab_recommendation_blocker_live_diagnostic import (
        FakeRecommendationBlockerProvider,
        run_recommendation_blocker_live_diagnostic,
    )

    artifact = run_recommendation_blocker_live_diagnostic(
        provider=FakeRecommendationBlockerProvider(corrupt_review=True),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    assert artifact["status"] == "blocked"
    assert "provider_review.blocked_candidate_selected" in artifact["blockers"]


def test_recommendation_blocker_cli_fake_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "recommendation-blocker-fake.json"

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
    assert artifact["live_recommendation_blocker_diagnostic_pass"] is False
    assert artifact["live_edd_preflight"]["reviewed_preflight_status"] == (
        "fake_contract_preflight_passed_non_live"
    )


def test_recommendation_blocker_cli_blocks_live_without_gate(tmp_path: Path) -> None:
    output = tmp_path / "recommendation-blocker-blocked-live.json"

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
