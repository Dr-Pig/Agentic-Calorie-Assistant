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
SCRIPT = "scripts/run_advanced_product_lab_memory_tool_lookup_live_diagnostic.py"


def test_memory_tool_lookup_fake_diagnostic_uses_record_first_bounded_source_path() -> None:
    from app.advanced_shadow_lab.product_lab_memory_tool_lookup_live_diagnostic import (
        FakeMemoryToolLookupProvider,
        run_memory_tool_lookup_live_diagnostic,
    )

    artifact = run_memory_tool_lookup_live_diagnostic(
        provider=FakeMemoryToolLookupProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    assert artifact["status"] == "pass"
    assert artifact["tool_sequence"] == ["memory.search", "memory.source_lookup"]
    assert artifact["memory_record_first"] is True
    assert artifact["bounded_evidence_read"] is True
    assert artifact["full_raw_transcript_allowed"] is False
    assert artifact["raw_transcript_included"] is False
    assert artifact["source_lookup_result_count"] == 1
    assert artifact["diagnostic_evidence_class"] == "fake_contract"
    assert artifact["live_completion_claim_allowed"] is False
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["durable_product_memory_written"] is False


def test_memory_tool_lookup_grader_blocks_raw_transcript_and_non_record_first_output() -> None:
    from app.advanced_shadow_lab.product_lab_memory_tool_lookup_live_diagnostic import (
        FakeMemoryToolLookupProvider,
        run_memory_tool_lookup_live_diagnostic,
    )

    artifact = run_memory_tool_lookup_live_diagnostic(
        provider=FakeMemoryToolLookupProvider(corrupt_review=True),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    assert artifact["status"] == "blocked"
    assert "provider_review.memory_record_first_mismatch" in artifact["blockers"]
    assert "provider_review.raw_transcript_requested" in artifact["blockers"]
    assert artifact["semantic_hardening_allowed"] is False


def test_memory_tool_lookup_cli_fake_mode_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "memory-tool-lookup-fake.json"

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
    assert artifact["tool_result_summary"]["search_status"] == "pass"
    assert artifact["tool_result_summary"]["source_lookup_status"] == "pass"
    assert artifact["live_edd_preflight"]["reviewed_preflight_status"] == (
        "fake_contract_preflight_passed_non_live"
    )


def test_memory_tool_lookup_cli_blocks_live_without_gate(tmp_path: Path) -> None:
    output = tmp_path / "memory-tool-lookup-blocked-live.json"

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
