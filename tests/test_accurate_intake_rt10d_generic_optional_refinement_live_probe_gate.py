from __future__ import annotations

import json
from pathlib import Path

from scripts import build_accurate_intake_rt10d_generic_optional_refinement_live_probe_gate as module
from scripts import run_accurate_intake_mvp_live_diagnostic as live_runner


def _pass_artifact() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_mvp_live_diagnostic",
        "provider_mode": "live",
        "live_invoked": True,
        "live_llm_invoked": True,
        "readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
        "mutation_rollout_approved": False,
        "live_provider_used_as_truth": False,
        "runtime_web_activation_approved": False,
        "stages": [
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["bubble_milk_tea_refinement"],
            }
        ],
        "cases": [
            {
                "case_id": "bubble_milk_tea_refinement",
                "case_contract_status": "strict_pass",
                "verdict": "pass",
                "failure_layer": None,
                "turns": [
                    {
                        "turn": 1,
                        "manager_final_action": "commit",
                        "workflow_effect": "canonical_write",
                        "state_delta": {
                            "canonical_commit": True,
                            "draft_saved": False,
                            "new_meal_version_created": True,
                            "old_version_superseded": False,
                            "ledger_updated": True,
                        },
                        "remaining_budget": {"status": "ready", "consumed_kcal": 400},
                        "manager_rounds": [
                            {"decision": {"tool_calls": [{"name": "estimate_nutrition"}]}},
                            {
                                "decision": {
                                    "exactness": "generic",
                                    "confidence": "available",
                                    "evidence_posture": "evidence_present",
                                    "semantic_decision": {
                                        "target_attachment": {"meal_title": "\u73cd\u73e0\u5976\u8336"},
                                    },
                                    "answer_contract": {"followup_question": None},
                                    "tool_calls": [],
                                }
                            },
                        ],
                    },
                    {
                        "turn": 2,
                        "manager_final_action": "commit",
                        "workflow_effect": "canonical_write",
                        "state_delta": {
                            "canonical_commit": True,
                            "draft_saved": False,
                            "new_meal_version_created": True,
                            "old_version_superseded": True,
                            "ledger_updated": True,
                        },
                        "remaining_budget": {"status": "ready", "consumed_kcal": 400},
                        "manager_rounds": [
                            {"decision": {"tool_calls": [{"name": "estimate_nutrition"}]}},
                            {
                                "decision": {
                                    "exactness": "near_exact",
                                    "confidence": "high",
                                    "evidence_posture": "evidence_present",
                                    "semantic_decision": {
                                        "target_attachment": {
                                            "meal_thread_id": 1,
                                            "refinement_details": {},
                                        },
                                    },
                                    "answer_contract": {"followup_question": None},
                                    "tool_calls": [],
                                }
                            },
                        ],
                    },
                ],
                "debug_surface": {
                    "model": {
                        "same_truth": {
                            "status": "pass",
                            "debug_model_consumed_kcal": 400,
                            "current_budget_consumed_kcal": 400,
                        },
                        "today_summary": {"consumed_kcal": 400, "remaining_kcal": 912},
                        "meal_threads": [
                            {
                                "active_version": {
                                    "version_reason": "correction",
                                    "parent_version_id": 1,
                                    "total_kcal": 400,
                                    "items": [{"estimated_kcal": 400}],
                                }
                            }
                        ],
                    }
                },
            }
        ],
    }


def test_rt10d_generic_optional_refinement_live_probe_gate_passes() -> None:
    artifact = module.build_rt10d_generic_optional_refinement_live_probe_gate(
        live_artifact=_pass_artifact()
    )

    assert artifact["artifact_type"] == "accurate_intake_rt10d_generic_optional_refinement_live_probe_gate"
    assert artifact["target_manager_runtime_gate"] == "rt10d_generic_optional_refinement_live_probe"
    assert artifact["status"] == "pass"
    assert artifact["supports_journeys"] == ["B", "C"]


def test_rt10d_generic_optional_refinement_live_probe_gate_accepts_runner_generated_inventory_artifact(
    tmp_path: Path,
) -> None:
    live_artifact = live_runner.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=live_runner.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="live",
        live_invoked=True,
        stage="single_case_live_probe",
        case_id="bubble_milk_tea_refinement",
    )

    artifact = module.build_rt10d_generic_optional_refinement_live_probe_gate(
        live_artifact=live_artifact
    )

    assert artifact["status"] == "pass"


def test_rt10d_generic_optional_refinement_live_probe_gate_blocks_missing_second_turn_target() -> None:
    source = _pass_artifact()
    decision = source["cases"][0]["turns"][1]["manager_rounds"][1]["decision"]
    decision["semantic_decision"]["target_attachment"] = {}

    artifact = module.build_rt10d_generic_optional_refinement_live_probe_gate(live_artifact=source)

    assert artifact["status"] == "fail"
    assert "turn2_target_existing_thread_missing" in artifact["blockers"]


def test_rt10d_generic_optional_refinement_live_probe_gate_blocks_missing_supersede() -> None:
    source = _pass_artifact()
    source["cases"][0]["turns"][1]["state_delta"]["old_version_superseded"] = False

    artifact = module.build_rt10d_generic_optional_refinement_live_probe_gate(live_artifact=source)

    assert artifact["status"] == "fail"
    assert "turn2_expected_supersede_missing" in artifact["blockers"]


def test_rt10d_generic_optional_refinement_live_probe_gate_cli_writes_artifact(tmp_path: Path) -> None:
    source_path = tmp_path / "bubble_live.json"
    output_path = tmp_path / "accurate_intake_rt10d_generic_optional_refinement_live_probe_gate.json"
    source_path.write_text(json.dumps(_pass_artifact(), ensure_ascii=False), encoding="utf-8")

    rc = module.main(["--source-artifact", str(source_path), "--output", str(output_path)])

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "accurate_intake_rt10d_generic_optional_refinement_live_probe_gate"
