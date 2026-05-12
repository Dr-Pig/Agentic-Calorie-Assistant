from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.shared.infra.json_artifacts import read_json_artifact


ROOT = Path(__file__).resolve().parents[1]


def test_memory_record_closure_pipeline_cli_writes_complete_chain(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "closure-pipeline"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_product_lab_memory_record_closure_pipeline.py",
            "--output-root",
            str(output_root),
            "--session-id",
            "closure-pipeline-session",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout_summary = json.loads(result.stdout)
    assert stdout_summary["status"] == "pass"
    assert stdout_summary["final_artifact"] == str(output_root / "activation_wall.json")

    expected_files = {
        "summary.json",
        "readiness.json",
        "integrated_e2e.json",
        "live_diagnostic.json",
        "holdout.json",
        "closure_pack.json",
        "activation_wall.json",
    }
    assert {path.name for path in output_root.glob("*.json")} == expected_files

    closure = read_json_artifact(output_root / "closure_pack.json")
    audit = read_json_artifact(output_root / "activation_wall.json")
    assert closure["status"] == "pass"
    assert audit["status"] == "pass"
    assert audit["source_closure_pack_path"] == str(output_root / "closure_pack.json")
    assert audit["mainline_activation_enabled"] is False
    assert audit["self_use_v1_affected"] is False
    assert audit["canonical_product_mutation_allowed"] is False
    assert "raw_user_utterance" not in json.dumps(audit, ensure_ascii=False)
