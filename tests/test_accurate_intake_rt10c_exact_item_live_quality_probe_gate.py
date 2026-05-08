from __future__ import annotations

import json
from pathlib import Path

from scripts import build_accurate_intake_rt10c_exact_item_live_quality_probe_gate as module


def _pass_artifact() -> dict[str, object]:
    expected = module._expected_exact_truth()  # noqa: SLF001 - gate contract fixture.
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
                "case_ids": ["exact_item_official_label"],
            }
        ],
        "cases": [
            {
                "case_id": "exact_item_official_label",
                "case_contract_status": "strict_pass",
                "verdict": "pass",
                "failure_layer": None,
                "turns": [
                    {
                        "manager_final_action": "commit",
                        "state_delta": {
                            "canonical_commit": True,
                            "draft_saved": False,
                            "ledger_updated": True,
                        },
                        "remaining_budget": {
                            "status": "ready",
                            "consumed_kcal": expected["kcal"],
                        },
                        "manager_rounds": [
                            {
                                "decision": {
                                    "tool_calls": [{"name": "estimate_nutrition"}],
                                }
                            },
                            {
                                "decision": {
                                    "exactness": "exact",
                                    "confidence": "high",
                                    "evidence_posture": "evidence_present",
                                    "semantic_decision": {"followup_question": None},
                                }
                            },
                        ],
                    }
                ],
                "debug_surface": {
                    "model": {
                        "meal_threads": [
                            {
                                "active_version": {
                                    "total_kcal": expected["kcal"],
                                    "items": [
                                        {
                                            "name": expected["title"],
                                            "estimated_kcal": expected["kcal"],
                                        }
                                    ],
                                }
                            }
                        ],
                        "same_truth": {
                            "status": "pass",
                            "debug_model_consumed_kcal": expected["kcal"],
                            "current_budget_consumed_kcal": expected["kcal"],
                        },
                    }
                },
            }
        ],
    }


def test_rt10c_exact_item_live_quality_probe_gate_passes() -> None:
    artifact = module.build_rt10c_exact_item_live_quality_probe_gate(live_artifact=_pass_artifact())

    assert artifact["artifact_type"] == "accurate_intake_rt10c_exact_item_live_quality_probe_gate"
    assert artifact["target_manager_runtime_gate"] == "rt10c_exact_item_live_quality_probe"
    assert artifact["status"] == "pass"
    assert artifact["blockers"] == []
    assert artifact["summary"]["expected_case_id"] == "exact_item_official_label"
    assert artifact["summary"]["required_tool_calls"] == ["estimate_nutrition"]


def test_rt10c_exact_item_live_quality_probe_gate_blocks_near_exact_drift() -> None:
    source = _pass_artifact()
    source["cases"][0]["turns"][0]["manager_rounds"][1]["decision"]["exactness"] = "near_exact"  # type: ignore[index]
    source["cases"][0]["turns"][0]["remaining_budget"]["consumed_kcal"] = 400  # type: ignore[index]
    source["cases"][0]["debug_surface"]["model"]["meal_threads"][0]["active_version"]["total_kcal"] = 400  # type: ignore[index]
    source["cases"][0]["debug_surface"]["model"]["meal_threads"][0]["active_version"]["items"][0]["estimated_kcal"] = 400  # type: ignore[index]
    source["cases"][0]["debug_surface"]["model"]["same_truth"]["debug_model_consumed_kcal"] = 400  # type: ignore[index]
    source["cases"][0]["debug_surface"]["model"]["same_truth"]["current_budget_consumed_kcal"] = 400  # type: ignore[index]

    artifact = module.build_rt10c_exact_item_live_quality_probe_gate(live_artifact=source)

    assert artifact["status"] == "fail"
    assert "final_exactness_not_exact" in artifact["blockers"]
    assert "consumed_kcal_mismatch" in artifact["blockers"]
    assert "active_version_total_kcal_mismatch" in artifact["blockers"]


def test_rt10c_exact_item_live_quality_probe_gate_cli_writes_artifact(tmp_path: Path) -> None:
    source_path = tmp_path / "source.json"
    output_path = tmp_path / "gate.json"
    source_path.write_text(json.dumps(_pass_artifact(), ensure_ascii=False), encoding="utf-8")

    exit_code = module.main(
        [
            "--source-artifact",
            str(source_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["artifact_name"] == "gate.json"
