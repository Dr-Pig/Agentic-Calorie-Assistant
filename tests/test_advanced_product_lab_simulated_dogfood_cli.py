from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.shared.infra.json_artifacts import read_json_artifact


ROOT = Path(__file__).resolve().parents[1]


def test_simulated_dogfood_cli_writes_operator_review_artifacts(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "operator-pack"
    summary_path = tmp_path / "summary.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_product_lab_simulated_dogfood.py",
            "--output-root",
            str(output_root),
            "--summary-output",
            str(summary_path),
            "--session-id",
            "operator-session-1",
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
        "advanced_product_lab_simulated_dogfood_summary"
    )
    assert file_summary["status"] == "pass"
    assert file_summary["session_id"] == "operator-session-1"
    assert file_summary["turn_count"] == 4
    assert file_summary["lab_session_store_written"] is True
    assert file_summary["lab_memory_store_written"] is True
    assert file_summary["lab_memory_context_injected"] is True
    assert file_summary["memory_context_injected"] is True
    assert file_summary["lab_memory_record_ids"] == [
        "golden-breakfast-oatmeal",
        "negative-cilantro",
    ]
    assert file_summary["operator_review_artifact_written"] is True
    assert file_summary["live_provider_invoked"] is False
    assert file_summary["kimi_live_calls_allowed"] is False
    assert file_summary["mainline_runtime_connected"] is False
    assert file_summary["user_facing_behavior_changed"] is False
    assert file_summary["production_db_migration_allowed"] is False
    assert file_summary["durable_product_memory_written"] is False
    assert file_summary["canonical_product_mutation_allowed"] is False
    assert file_summary["visible_candidate_counts"] == [2, 1, 2, 1]
    assert file_summary["product_runtime_capabilities_exercised"] == [
        "long_term_memory",
        "recommendation",
        "rescue",
        "proactive",
        "chat_surface",
    ]
    assert file_summary["product_recommendation_selected_candidate_ids"] == [
        "golden-1",
        "golden-breakfast-oatmeal",
        "golden-breakfast-oatmeal",
        "golden-breakfast-oatmeal",
    ]
    assert file_summary["product_proactive_candidate_counts"] == [2, 2, 2, 2]
    assert file_summary["product_outputs_applied_to_chat_surface"] is True

    session_artifact = read_json_artifact(Path(file_summary["session_artifact_path"]))
    assert session_artifact["artifact_type"] == (
        "advanced_product_lab_dogfood_session_artifact"
    )
    assert session_artifact["turn_count"] == 4
    assert session_artifact["lab_memory_context_injected"] is True
    assert session_artifact["product_outputs_applied_to_chat_surface"] is True
    assert Path(session_artifact["lab_memory_surface_paths"]["user_md"]).exists()
    assert Path(file_summary["session_artifact_path"]).is_relative_to(
        output_root.resolve(strict=False)
    )
    assert len(file_summary["turn_artifact_paths"]) == 4
    assert all(
        Path(path).is_relative_to(output_root.resolve(strict=False))
        for path in file_summary["turn_artifact_paths"]
    )
