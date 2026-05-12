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


def test_memory_record_integrated_e2e_chain_runs_from_readiness_gate(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_integrated_e2e import (
        run_memory_record_integrated_e2e_chain,
    )

    summary = _summary(tmp_path)
    readiness = build_memory_record_readiness_report(summary)

    artifact = run_memory_record_integrated_e2e_chain(
        summary_artifact=summary,
        readiness_report=readiness,
    )

    assert artifact["artifact_type"] == (
        "advanced_product_lab_memory_record_integrated_e2e_artifact"
    )
    assert artifact["status"] == "pass"
    assert artifact["memory_record_summary_drives_chain"] is True
    assert artifact["source_readiness_status"] == "pass"
    assert artifact["source_memory_record_ids"] == [
        "golden-breakfast-oatmeal",
        "negative-cilantro",
    ]
    assert artifact["integrated_chain_artifact"]["status"] == "pass"
    assert artifact["integrated_chain_artifact"]["chat_ux_packet"]["status"] == "pass"
    assert artifact["journey_terminal_evidence_count"] == 6
    assert artifact["recommendation_selected_candidate_id"] == "golden-1"
    assert artifact["recommendation_source_refs_include_memory_records"] is True
    assert artifact["lab_enabled"] is True
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert "raw_user_utterance" not in json.dumps(artifact, ensure_ascii=False)


def test_memory_record_integrated_e2e_blocks_without_readiness_pass(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_integrated_e2e import (
        run_memory_record_integrated_e2e_chain,
    )

    summary = _summary(tmp_path)
    readiness = build_memory_record_readiness_report(summary)
    readiness["status"] = "blocked"
    readiness["blockers"] = ["memory_record_context_pack_used.missing_or_false"]

    artifact = run_memory_record_integrated_e2e_chain(
        summary_artifact=summary,
        readiness_report=readiness,
    )

    assert artifact["status"] == "blocked"
    assert artifact["integrated_chain_artifact"] is None
    assert artifact["blockers"] == [
        "readiness_report.status_blocked",
        "readiness_report.memory_record_context_pack_used.missing_or_false",
    ]
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_memory_record_integrated_e2e_cli_reads_summary_and_readiness(
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "summary.json"
    readiness_path = tmp_path / "readiness.json"
    output_path = tmp_path / "integrated_e2e.json"
    summary = _summary(tmp_path)
    readiness = build_memory_record_readiness_report(summary)
    write_json_artifact(summary_path, summary)
    write_json_artifact(readiness_path, readiness)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_product_lab_memory_record_integrated_e2e.py",
            "--summary-json",
            str(summary_path),
            "--readiness-json",
            str(readiness_path),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout_artifact = json.loads(result.stdout)
    file_artifact = read_json_artifact(output_path)
    assert stdout_artifact == file_artifact
    assert file_artifact["status"] == "pass"
    assert file_artifact["source_summary_path"] == str(summary_path)
    assert file_artifact["source_readiness_path"] == str(readiness_path)


def _summary(tmp_path: Path) -> dict[str, object]:
    session = run_advanced_product_lab_memory_record_session(
        artifact_root=tmp_path / "session",
        session_id="integrated-e2e-memory-record-session",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=build_product_lab_simulated_turns(),
    )
    return build_memory_record_dogfood_summary(session)
