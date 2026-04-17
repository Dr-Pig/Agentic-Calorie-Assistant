from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_intake_executable_pack.py"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_intake_executable_pack as intake_runner


def test_selected_runtime_cases_resolve_source_utterances_and_contract_ready_scope() -> None:
    cases = intake_runner._selected_runtime_cases(case_id=None)

    assert len(cases) == 5
    assert {case.executable_case_id for case in cases} == {
        "intake_create_executable_001",
        "intake_clarify_create_executable_001",
        "intake_turn2_continue_executable_001",
        "intake_correction_executable_001",
        "intake_open_new_workflow_executable_001",
    }
    for case in cases:
        assert case.derivation_status == "contract_ready"
        assert case.execution_mode == "text_turn"
        assert case.source_utterance
        assert case.source_official_case_id.endswith("_001")
        assert case.expected_runtime_outcome["expected_target_workflow_family"] == "intake"


def test_run_intake_executable_pack_cli_emits_report_and_summary(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output-dir", str(output_dir)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    stdout_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    json_paths = [line for line in stdout_lines if line.endswith(".json")]
    assert len(json_paths) >= 2

    report_path = Path(json_paths[0])
    summary_path = Path(json_paths[1])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert report_path.exists()
    assert summary_path.exists()
    assert report["pack_id"] == "intake_executable_action_pack_v1"
    assert report["isolated_mode"] is True
    assert report["summary"]["total_cases"] == 5
    assert report["summary"]["passed_cases"] == 5
    assert report["summary"]["failed_cases"] == 0
    assert summary == report["summary"]
    assert {case["executable_case_id"] for case in report["cases"]} == {
        "intake_create_executable_001",
        "intake_clarify_create_executable_001",
        "intake_turn2_continue_executable_001",
        "intake_correction_executable_001",
        "intake_open_new_workflow_executable_001",
    }
    assert all(case["checks"]["passed"] is True for case in report["cases"])
