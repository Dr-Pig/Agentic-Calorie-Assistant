from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.advanced_shadow_lab.product_lab_calibration_fixture_inputs import (
    build_product_lab_calibration_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory_record_dogfood_summary import (
    build_memory_record_dogfood_summary,
)
from app.advanced_shadow_lab.product_lab_memory_record_session import (
    run_advanced_product_lab_memory_record_session,
)
from app.advanced_shadow_lab.product_lab_simulated_scenario import (
    build_product_lab_simulated_turns,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact


ROOT = Path(__file__).resolve().parents[1]


def test_memory_record_readiness_report_marks_integrated_lab_ready(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_readiness import (
        build_memory_record_readiness_report,
    )

    summary = _summary(tmp_path)

    report = build_memory_record_readiness_report(
        summary,
        source_summary_path=tmp_path / "summary.json",
    )

    assert report["artifact_type"] == (
        "advanced_product_lab_memory_record_readiness_report"
    )
    assert report["status"] == "pass"
    assert report["lab_enabled"] is True
    assert report["mainline_activation_enabled"] is False
    assert report["mainline_runtime_connected"] is False
    assert report["user_facing_behavior_changed"] is False
    assert report["durable_product_memory_written"] is False
    assert report["canonical_product_mutation_allowed"] is False
    assert report["blockers"] == []
    assert report["capability_readiness"] == {
        "long_term_memory": "ready_for_integrated_lab_e2e",
        "recommendation": "ready_for_integrated_lab_e2e",
        "rescue": "ready_for_integrated_lab_e2e",
        "calibration": "ready_for_integrated_lab_e2e",
        "proactive": "ready_for_integrated_lab_e2e",
        "chat_surface": "ready_for_integrated_lab_e2e",
    }
    assert report["next_allowed_slices"] == [
        "memory_record_integrated_lab_e2e_chain",
        "memory_record_env_gated_grokfast_diagnostic",
        "simulated_dogfood_holdout_expansion",
    ]


def test_memory_record_readiness_report_blocks_context_or_activation_drift(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_readiness import (
        build_memory_record_readiness_report,
    )

    summary = _summary(tmp_path)
    summary["memory_record_context_pack_used"] = False
    summary["canonical_product_mutation_allowed"] = True

    report = build_memory_record_readiness_report(summary)

    assert report["status"] == "blocked"
    assert report["next_allowed_slices"] == []
    assert report["blockers"] == [
        "memory_record_context_pack_used.missing_or_false",
        "canonical_product_mutation_allowed.claim_drift",
    ]


def test_memory_record_readiness_report_cli_reads_summary_and_writes_report(
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "summary.json"
    report_path = tmp_path / "readiness.json"
    write_json_artifact(summary_path, _summary(tmp_path))

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_advanced_product_lab_memory_record_readiness.py",
            "--summary-json",
            str(summary_path),
            "--output",
            str(report_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout_report = json.loads(result.stdout)
    file_report = read_json_artifact(report_path)
    assert stdout_report == file_report
    assert file_report["status"] == "pass"
    assert file_report["source_summary_path"] == str(summary_path)
    assert "raw_user_utterance" not in json.dumps(file_report, ensure_ascii=False)


def _summary(tmp_path: Path) -> dict[str, object]:
    session = run_advanced_product_lab_memory_record_session(
        artifact_root=tmp_path / "session",
        session_id="readiness-memory-record-session",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=build_product_lab_simulated_turns(),
    )
    return build_memory_record_dogfood_summary(session)
