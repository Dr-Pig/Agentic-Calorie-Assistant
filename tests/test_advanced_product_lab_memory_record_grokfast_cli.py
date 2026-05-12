from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
)
from app.advanced_shadow_lab.product_lab_calibration_fixture_inputs import (
    build_product_lab_calibration_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory_record_dogfood_summary import (
    build_memory_record_dogfood_summary,
)
from app.advanced_shadow_lab.product_lab_memory_record_integrated_e2e import (
    run_memory_record_integrated_e2e_chain,
)
from app.advanced_shadow_lab.product_lab_memory_record_readiness import (
    build_memory_record_readiness_report,
)
from app.advanced_shadow_lab.product_lab_memory_record_session import (
    run_advanced_product_lab_memory_record_session,
)
from app.advanced_shadow_lab.product_lab_simulated_scenario import (
    build_product_lab_simulated_turns,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact


ROOT = Path(__file__).resolve().parents[1]
ALLOW_ENV = "ADVANCED_PRODUCT_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
SCRIPT = "scripts/run_advanced_product_lab_memory_record_grokfast_diagnostic.py"


def test_memory_record_grokfast_diagnostic_blocks_without_live_gate(
    tmp_path: Path,
) -> None:
    integrated_path = tmp_path / "integrated_e2e.json"
    output = tmp_path / "blocked_live.json"
    write_json_artifact(integrated_path, _integrated(tmp_path))

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--integrated-e2e-json",
            str(integrated_path),
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
    assert artifact["provider_profile_id"] == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
    assert artifact["live_invoked"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["blockers"] == ["live_gate_not_enabled"]
    assert artifact["live_edd_preflight"]["reviewed_preflight_status"] == (
        "blocked_not_invoked_preflight"
    )
    assert artifact["live_edd_gate"]["reviewed_live_status"] == (
        "blocked_not_invoked_reviewed"
    )
    assert artifact["live_edd_gate"]["live_milestone_complete"] is False
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_memory_record_grokfast_diagnostic_rejects_kimi_before_input_read(
    tmp_path: Path,
) -> None:
    output = tmp_path / "blocked_kimi.json"

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--integrated-e2e-json",
            str(tmp_path / "missing_integrated.json"),
            "--output",
            str(output),
            "--provider-mode",
            "live",
            "--allow-live-provider",
            "--provider-profile-id",
            ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, ALLOW_ENV: "1"},
    )

    assert result.returncode == 0
    artifact = read_json_artifact(output)
    assert artifact["status"] == "blocked"
    assert artifact["provider_mode"] == "not_invoked"
    assert artifact["blockers"] == [
        "profile_not_live_diagnostic_allowed;kimi_live_calls_forbidden"
    ]
    assert artifact["durable_product_memory_written"] is False
    assert "No such file" not in result.stderr


def test_memory_record_grokfast_diagnostic_cli_fake_mode_writes_artifact(
    tmp_path: Path,
) -> None:
    integrated_path = tmp_path / "integrated_e2e.json"
    output = tmp_path / "fake_diagnostic.json"
    write_json_artifact(integrated_path, _integrated(tmp_path))

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--integrated-e2e-json",
            str(integrated_path),
            "--output",
            str(output),
            "--provider-mode",
            "fake",
        ],
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
    assert artifact["source_integrated_e2e_path"] == str(integrated_path)
    assert artifact["provider_profile_id"] == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
    assert artifact["live_edd_preflight"]["reviewed_preflight_status"] == (
        "fake_contract_preflight_passed_non_live"
    )
    assert artifact["live_edd_gate"]["reviewed_live_status"] == (
        "fake_contract_reviewed_non_live"
    )
    assert artifact["live_edd_gate"]["live_milestone_complete"] is False


def _integrated(tmp_path: Path) -> dict[str, object]:
    session = run_advanced_product_lab_memory_record_session(
        artifact_root=tmp_path / "session",
        session_id="memory-record-live-diagnostic-session",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=build_product_lab_simulated_turns(),
    )
    summary = build_memory_record_dogfood_summary(session)
    return run_memory_record_integrated_e2e_chain(
        summary_artifact=summary,
        readiness_report=build_memory_record_readiness_report(summary),
    )
