from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.shared.infra.json_artifacts import read_json_artifact


ROOT = Path(__file__).resolve().parents[1]


def test_memory_record_dogfood_cli_writes_reviewable_operator_artifacts(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "memory-record-operator-pack"
    summary_path = tmp_path / "memory-record-summary.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_product_lab_memory_record_dogfood.py",
            "--output-root",
            str(output_root),
            "--summary-output",
            str(summary_path),
            "--session-id",
            "memory-record-operator-session",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout_summary = json.loads(result.stdout)
    file_summary = read_json_artifact(summary_path)
    assert stdout_summary == file_summary

    assert file_summary["artifact_type"] == (
        "advanced_product_lab_memory_record_dogfood_summary"
    )
    assert file_summary["status"] == "pass"
    assert file_summary["session_id"] == "memory-record-operator-session"
    assert file_summary["turn_count"] == 5
    assert file_summary["memory_record_session_replay_enabled"] is True
    assert file_summary["memory_record_context_pack_used"] is True
    assert file_summary["memory_record_write_artifact_count"] == 5
    assert file_summary["lab_memory_record_ids"] == [
        "golden-breakfast-oatmeal",
        "negative-cilantro",
    ]
    assert len(file_summary["lab_memory_tool_calls"]) == 5
    assert file_summary["advanced_product_lab_product_loop_closed"] is True
    assert file_summary["advanced_product_lab_closure_missing"] == []
    assert file_summary["mainline_activation_enabled"] is False
    assert file_summary["mainline_runtime_connected"] is False
    assert file_summary["durable_product_memory_written"] is False
    assert file_summary["canonical_product_mutation_allowed"] is False
    assert file_summary["operator_review_artifact_written"] is True
    assert file_summary["live_provider_invoked"] is False
    assert "raw_user_utterance" not in json.dumps(file_summary, ensure_ascii=False)

    session_artifact = read_json_artifact(Path(file_summary["session_artifact_path"]))
    assert session_artifact["memory_record_session_replay_enabled"] is True
    assert session_artifact["memory_record_context_pack_used"] is True
    assert session_artifact["mainline_activation_enabled"] is False
    assert Path(file_summary["session_artifact_path"]).is_relative_to(
        output_root.resolve(strict=False)
    )

    first_turn = read_json_artifact(Path(file_summary["turn_artifact_paths"][0]))
    assert first_turn["memory_record_write_artifact"]["promoted_record_ids"] == [
        "golden-breakfast-oatmeal",
        "negative-cilantro",
    ]
    assert first_turn["memory_record_context_pack"]["selected_record_ids"] == []
