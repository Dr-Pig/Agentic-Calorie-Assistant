from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.shared.infra.json_artifacts import read_json_artifact
from tests.test_advanced_product_lab_runtime import _fixture_inputs


HOLDOUT_PATH = Path(
    "docs/quality/advanced_product_lab_proactive_quiet_cooldown_holdouts.yaml"
)


def test_proactive_quiet_cooldown_holdout_schema_covers_silence_and_release() -> None:
    suite = _holdout_suite()

    assert suite["artifact_type"] == "advanced_product_lab_proactive_holdout_suite"
    assert suite["raw_keyword_semantic_oracle_allowed"] is False
    assert suite["mainline_activation_enabled"] is False
    assert suite["production_scheduler_delivery_allowed"] is False
    assert suite["case_count"] == len(suite["cases"]) == 6
    assert {case["case_type"] for case in suite["cases"]} == {
        "quiet_hours_silence",
        "trigger_cooldown_silence",
        "recent_send_cap_silence",
        "dismiss_until_next_signal",
        "dismiss_release_on_next_signal",
        "snooze_window_release",
    }
    assert {case["expected_decision_family"] for case in suite["cases"]} == {
        "stay_silent",
        "partial_omit",
        "release_after_signal",
        "release_after_time",
    }


def test_proactive_quiet_cooldown_holdouts_run_against_lab_runtime(
    tmp_path: Path,
) -> None:
    reports = [
        _run_case(tmp_path=tmp_path, case=case)
        for case in _holdout_suite()["cases"]
    ]
    blockers = [
        blocker
        for report in reports
        for blocker in report["blockers"]
    ]

    assert blockers == []
    assert {report["case_id"]: report["status"] for report in reports} == {
        "pro-qc-001": "pass",
        "pro-qc-002": "pass",
        "pro-qc-003": "pass",
        "pro-qc-004": "pass",
        "pro-qc-005": "pass",
        "pro-qc-006": "pass",
    }


def _run_case(*, tmp_path: Path, case: Mapping[str, Any]) -> dict[str, Any]:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id=str(case["case_id"]),
        fixture_inputs=_fixture_inputs(),
        turns=[dict(turn) for turn in case["turns"]],
    )
    blockers = [
        f"{case['case_id']}.session_status:{artifact['status']}"
        if artifact["status"] != "pass"
        else "",
        *_visible_blockers(case, artifact),
        *_omission_blockers(case, artifact),
    ]
    return {
        "case_id": str(case["case_id"]),
        "status": "pass" if not [item for item in blockers if item] else "blocked",
        "blockers": [item for item in blockers if item],
    }


def _visible_blockers(
    case: Mapping[str, Any],
    artifact: Mapping[str, Any],
) -> list[str]:
    actual = {
        str(row["turn_id"]): list(row["visible_candidate_ids"])
        for row in artifact["turn_summaries"]
    }
    expected = dict(case["expected_visible_candidate_ids_by_turn"])
    return [
        f"{case['case_id']}.visible_candidate_ids:{actual}!={expected}"
        if actual != expected
        else ""
    ]


def _omission_blockers(
    case: Mapping[str, Any],
    artifact: Mapping[str, Any],
) -> list[str]:
    by_turn = {
        str(turn_path): read_json_artifact(Path(turn_path))
        for turn_path in artifact["turn_artifact_paths"]
    }
    actual = {
        str(record["turn_artifact"]["turn_id"]): [
            trace["omission_reason"]
            for trace in record["turn_artifact"]["product_lab_proactive_artifact"][
                "omission_traces"
            ]
        ]
        for record in by_turn.values()
    }
    expected = dict(case["expected_omission_reasons_by_turn"])
    return [
        f"{case['case_id']}.omission_reasons:{actual}!={expected}"
        if actual != expected
        else ""
    ]


def _holdout_suite() -> dict[str, Any]:
    return dict(yaml.safe_load(HOLDOUT_PATH.read_text(encoding="utf-8-sig")))
