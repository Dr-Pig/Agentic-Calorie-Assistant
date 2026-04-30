from __future__ import annotations

import json
from pathlib import Path

from scripts.build_wave1_founder_live_failure_layer_diagnostic import (
    build_founder_live_failure_layer_diagnostic,
    write_founder_live_failure_layer_diagnostic,
)


def test_missing_nutrition_payload_is_reported_not_fabricated() -> None:
    report = build_founder_live_failure_layer_diagnostic(
        _artifact(
            [
                _case(
                    case_id="generic_stable_tea_egg",
                    failure_layer="b2",
                    actual_behavior={
                        "assistant_message": "I logged 80 kcal.",
                        "manager_intent": "log_meal",
                        "manager_final_action": "commit",
                        "state_delta": {"canonical_commit": True},
                    },
                    b2={"tool_results": [], "nutrition_payload": None, "evidence_summary": {}},
                )
            ]
        )
    )

    case = report["focus_cases"][0]
    assert case["case_id"] == "generic_stable_tea_egg"
    assert case["b2_trace"]["nutrition_payload_present"] is False
    assert case["b2_trace"]["estimated_kcal"] == "not_available"
    assert case["fabrication_guard"]["nutrition_payload_fabricated"] is False
    assert "80" not in json.dumps(case["b2_trace"], ensure_ascii=False)


def test_missing_final_mapping_is_reported_not_backfilled_from_projection() -> None:
    report = build_founder_live_failure_layer_diagnostic(
        _artifact(
            [
                _case(
                    case_id="pearl_milk_tea_logged_followup",
                    failure_layer="mutation",
                    actual_behavior={"manager_final_action": "commit", "state_delta": {"canonical_commit": False}},
                    final_mapping={
                        "observable": True,
                        "manager_final_action": "commit",
                        "boundary_projection": {"commit_boundary_decision": {"intent": "commit"}},
                        "persistence_result_observable": False,
                    },
                )
            ]
        )
    )

    case = report["focus_cases"][0]
    assert case["final_mapping_trace"]["b2_final_mapping_present"] is False
    assert case["final_mapping_trace"]["external_outcome"] == "not_available"
    assert case["fabrication_guard"]["final_mapping_fabricated"] is False
    assert case["commit_boundary_trace"]["present"] is False


def test_missing_canonical_commit_stays_not_available() -> None:
    report = build_founder_live_failure_layer_diagnostic(
        _artifact(
            [
                _case(
                    case_id="correction_prior_pearl_milk_tea_half_sugar",
                    failure_layer="mutation",
                    mutation={"state_delta": {"meal_logged": False}, "persistence_result": None},
                )
            ]
        )
    )

    case = report["focus_cases"][0]
    assert case["state_delta_trace"]["state_delta_present"] is True
    assert case["state_delta_trace"]["canonical_commit_status"] == "not_available"
    assert case["fabrication_guard"]["canonical_commit_fabricated"] is False


def test_summary_failure_layers_are_case_observed_only() -> None:
    report = build_founder_live_failure_layer_diagnostic(
        _artifact(
            [
                _case(case_id="b2-case", failure_layer="b2"),
                _case(case_id="mutation-case", failure_layer="mutation"),
                _case(case_id="provider-case", failure_layer="provider_contract_non_adherence"),
                _case(case_id="pass-case", verdict="pass", failure_layer=None),
            ]
        )
    )

    assert report["summary"]["focus_case_count"] == 3
    assert report["summary"]["failure_layers"] == [
        "b2",
        "mutation",
        "provider_contract_non_adherence",
    ]
    assert report["readiness_claimed"] is False
    assert report["runtime_web_activation_approved"] is False


def test_failure_sublayer_reports_manager_skipped_tool_path_before_b2() -> None:
    report = build_founder_live_failure_layer_diagnostic(
        _artifact(
            [
                _case(
                    case_id="generic_stable_tea_egg",
                    failure_layer="b2",
                    actual_behavior={
                        "manager_final_action": "no_commit",
                        "manager_rounds": [
                            {
                                "decision": {
                                    "manager_action": "final",
                                    "final_action": "no_commit",
                                    "tool_calls": [],
                                }
                            }
                        ],
                    },
                    b2={"tool_results": [], "nutrition_payload": None, "evidence_summary": {}},
                )
            ]
        )
    )

    case = report["focus_cases"][0]
    assert case["failure_sublayers"] == [
        "manager_skipped_tool_path",
        "payload_absent_before_b2",
        "b2_final_mapping_absent",
        "persistence_not_attempted",
    ]
    assert report["summary"]["failure_sublayers"]["manager_skipped_tool_path"] == 1


def test_failure_layer_diagnostic_writer_creates_artifact(tmp_path: Path) -> None:
    source = tmp_path / "wave1_founder_e2e_live_diagnostic.json"
    source.write_text(json.dumps(_artifact([_case(case_id="b2-case", failure_layer="b2")])), encoding="utf-8")

    output = write_founder_live_failure_layer_diagnostic(
        founder_live_artifact_path=source,
        output_dir=tmp_path,
    )

    written = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "wave1_founder_live_failure_layer_diagnostic.json"
    assert written["source_artifact"] == str(source)
    assert written["summary"]["focus_case_count"] == 1


def _artifact(cases: list[dict[str, object]]) -> dict[str, object]:
    return {
        "artifact_type": "wave1_founder_e2e_live_diagnostic",
        "provider_mode": "live",
        "live_invoked": True,
        "readiness_claimed": False,
        "production_selected": False,
        "runtime_web_activation_approved": False,
        "mutation_enabled": False,
        "summary": {"failure_layers": sorted({str(case.get("failure_layer")) for case in cases if case.get("failure_layer")})},
        "cases": cases,
    }


def _case(
    *,
    case_id: str,
    failure_layer: str | None,
    verdict: str = "fail",
    actual_behavior: dict[str, object] | None = None,
    phase_a: dict[str, object] | None = None,
    b2: dict[str, object] | None = None,
    final_mapping: dict[str, object] | None = None,
    mutation: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "verdict": verdict,
        "failure_layer": failure_layer,
        "failure_family": failure_layer,
        "case_contract_status": "strict_pass",
        "actual_behavior": actual_behavior or {},
        "phase_a": phase_a or {},
        "b2": b2 or {"tool_results": [], "nutrition_payload": None, "evidence_summary": {}},
        "final_mapping": final_mapping or {"observable": False, "boundary_projection": {}},
        "mutation": mutation or {"state_delta": {}, "persistence_result": None},
        "same_truth": {},
    }
