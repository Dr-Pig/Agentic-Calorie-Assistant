from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.advanced_shadow_lab.product_lab_calibration_fixture_inputs import (
    build_product_lab_calibration_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory_record_session import (
    run_advanced_product_lab_memory_record_session,
)
from app.advanced_shadow_lab.product_lab_memory_record_session_memory import (
    memory_write,
)
from app.advanced_shadow_lab.product_lab_simulated_scenario import (
    build_product_lab_simulated_turns,
)
from app.memory.application.memory_preference_policy import (
    evaluate_preference_memory_policy,
)
from app.shared.infra.json_artifacts import read_json_artifact


ROOT = Path(__file__).resolve().parents[1]


def test_memory_record_holdout_fixture_preserves_negative_strengths() -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_holdout import (
        build_memory_record_holdout_candidates,
        build_memory_record_holdout_turns,
    )

    write = memory_write(build_memory_record_holdout_turns()[0], session_id="holdout")
    report = evaluate_preference_memory_policy(
        memory_records=write["records"],
        candidates=build_memory_record_holdout_candidates(),
    )
    evaluations = {
        item["candidate_id"]: item for item in report["candidate_evaluations"]
    }

    assert write["status"] == "pass"
    assert write["promoted_record_ids"] == [
        "negative-bitter-melon",
        "negative-spicy",
        "negative-vegetarian",
        "negative-bland",
        "negative-eggplant",
    ]
    assert write["pending_or_rejected_signal_ids"] == ["negative-dessert-ignored"]
    assert evaluations["candidate-bitter-melon"]["blocked"] is True
    assert evaluations["candidate-spicy-ramen"]["blocked"] is True
    assert evaluations["candidate-vegetarian-bowl"]["blocked"] is False
    assert evaluations["candidate-vegetarian-bowl"]["score_adjustment"] == -100
    assert evaluations["candidate-bland-soup"]["score_adjustment"] == -100
    assert evaluations["candidate-eggplant-rice"]["score_adjustment"] == -100
    assert evaluations["candidate-dessert"]["score_adjustment"] == 0


def test_memory_record_holdout_session_adds_edge_cases_without_breaking_loop(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_record_holdout import (
        build_memory_record_holdout_report,
        build_memory_record_holdout_turns,
    )

    turns = [*build_product_lab_simulated_turns(), *build_memory_record_holdout_turns()]
    artifact = run_advanced_product_lab_memory_record_session(
        artifact_root=tmp_path,
        session_id="memory-record-holdout-session",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=turns,
    )
    report = build_memory_record_holdout_report(artifact)

    assert artifact["status"] == "pass"
    assert artifact["turn_count"] == 6
    assert report["artifact_type"] == "advanced_product_lab_memory_record_holdout_report"
    assert report["status"] == "pass"
    assert report["holdout_case_count"] == 6
    assert report["confirmed_negative_record_ids"] == [
        "negative-bitter-melon",
        "negative-spicy",
        "negative-vegetarian",
        "negative-bland",
        "negative-eggplant",
    ]
    assert report["ignored_signal_ids"] == ["negative-dessert-ignored"]
    assert report["mainline_activation_enabled"] is False
    assert report["durable_product_memory_written"] is False
    assert report["canonical_product_mutation_allowed"] is False


def test_memory_record_holdout_cli_writes_report_artifact(tmp_path: Path) -> None:
    output_root = tmp_path / "holdout-session"
    report_path = tmp_path / "holdout-report.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_product_lab_memory_record_holdout.py",
            "--output-root",
            str(output_root),
            "--report-output",
            str(report_path),
            "--session-id",
            "holdout-cli-session",
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
    assert file_report["session_id"] == "holdout-cli-session"
    assert Path(file_report["session_artifact_path"]).is_relative_to(
        output_root.resolve(strict=False)
    )
