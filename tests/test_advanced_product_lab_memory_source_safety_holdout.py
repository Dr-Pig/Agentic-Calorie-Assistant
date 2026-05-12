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
SCRIPT = "scripts/run_advanced_product_lab_memory_source_safety_holdout.py"


def test_source_safety_holdout_fake_diagnostic_covers_prompt_cross_scope_and_semantic_query() -> None:
    from app.advanced_shadow_lab.product_lab_memory_source_safety_holdout import (
        FakeMemorySourceSafetyProvider,
        run_memory_source_safety_holdout,
    )

    artifact = run_memory_source_safety_holdout(
        provider=FakeMemorySourceSafetyProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    reports = {report["case_id"]: report for report in artifact["case_reports"]}
    assert artifact["status"] == "pass"
    assert artifact["case_count"] == 3
    assert reports["prompt_material_source_blocked"]["status"] == "pass"
    assert reports["cross_scope_source_omitted"]["status"] == "pass"
    assert reports["semantic_query_without_source_ref_blocked"]["status"] == "pass"
    assert artifact["source_prompt_material_allowed"] is False
    assert artifact["cross_scope_result_used"] is False
    assert artifact["general_rag_pool_used"] is False
    assert artifact["diagnostic_evidence_class"] == "fake_contract"
    assert artifact["mainline_activation_enabled"] is False


def test_source_safety_holdout_blocks_provider_review_that_follows_poisoned_source() -> None:
    from app.advanced_shadow_lab.product_lab_memory_source_safety_holdout import (
        FakeMemorySourceSafetyProvider,
        run_memory_source_safety_holdout,
    )

    artifact = run_memory_source_safety_holdout(
        provider=FakeMemorySourceSafetyProvider(corrupt_review=True),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    assert artifact["status"] == "blocked"
    assert "provider_review.prompt_material_followed" in artifact["blockers"]
    assert "provider_review.cross_scope_source_used" in artifact["blockers"]
    assert artifact["semantic_hardening_allowed"] is False


def test_source_safety_holdout_cli_fake_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "source-safety-fake.json"

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
    assert artifact["live_source_safety_holdout_pass"] is False
    assert artifact["live_edd_preflight"]["reviewed_preflight_status"] == (
        "fake_contract_preflight_passed_non_live"
    )


def test_source_safety_holdout_cli_blocks_live_without_gate(tmp_path: Path) -> None:
    output = tmp_path / "source-safety-blocked-live.json"

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
