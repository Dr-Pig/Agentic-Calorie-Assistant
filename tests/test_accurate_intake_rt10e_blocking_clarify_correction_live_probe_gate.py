from __future__ import annotations

import json
from pathlib import Path

from scripts import build_accurate_intake_rt10e_blocking_clarify_correction_live_probe_gate as module


def _blocking_artifact() -> dict[str, object]:
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
                "case_ids": ["luwei_bare_to_listed_basket"],
            }
        ],
        "cases": [
            {
                "case_id": "luwei_bare_to_listed_basket",
                "case_contract_status": "strict_pass",
                "verdict": "pass",
                "failure_layer": None,
                "turns": [
                    {
                        "turn": 1,
                        "manager_final_action": "ask_followup",
                        "workflow_effect": "ask_followup",
                        "state_delta": {
                            "canonical_commit": False,
                            "new_meal_version_created": False,
                            "ledger_updated": False,
                        },
                        "remaining_budget": {"status": "ready", "consumed_kcal": 0, "meal_count": 0},
                        "manager_rounds": [{"decision": {"tool_calls": []}}],
                    },
                    {
                        "turn": 2,
                        "manager_final_action": "commit",
                        "workflow_effect": "canonical_write",
                        "state_delta": {
                            "canonical_commit": True,
                            "new_meal_version_created": True,
                            "old_version_superseded": False,
                            "ledger_updated": True,
                        },
                        "remaining_budget": {"status": "ready", "consumed_kcal": 400, "remaining_kcal": 912},
                        "manager_rounds": [{"decision": {"tool_calls": [{"name": "estimate_nutrition"}]}}],
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
                        "pending_drafts": [],
                        "meal_threads": [
                            {
                                "active_version": {
                                    "version_reason": "new_intake",
                                },
                                "superseded_versions": [],
                            }
                        ],
                    }
                },
            }
        ],
    }


def _correction_artifact() -> dict[str, object]:
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
                "case_ids": ["chinese_chicken_rice_correction_removal_debug"],
            }
        ],
        "cases": [
            {
                "case_id": "chinese_chicken_rice_correction_removal_debug",
                "case_contract_status": "strict_pass",
                "verdict": "pass",
                "failure_layer": None,
                "turns": [
                    {
                        "turn": 1,
                        "manager_final_action": "commit",
                        "workflow_effect": "canonical_write",
                        "state_delta": {"canonical_commit": True},
                    },
                    {
                        "turn": 2,
                        "manager_final_action": "correction_applied",
                        "workflow_effect": "correction_write",
                        "state_delta": {
                            "canonical_commit": True,
                            "old_version_superseded": True,
                        },
                        "manager_rounds": [{"decision": {"tool_calls": [{"name": "estimate_nutrition"}]}}],
                    },
                    {
                        "turn": 3,
                        "manager_final_action": "correction_applied",
                        "workflow_effect": "correction_write",
                        "state_delta": {
                            "canonical_commit": True,
                            "old_version_superseded": True,
                        },
                        "manager_rounds": [{"decision": {"tool_calls": [{"name": "resolve_correction_target"}]}}],
                    },
                    {
                        "turn": 4,
                        "workflow_effect": "answer_remaining_budget",
                        "state_delta": {
                            "canonical_commit": False,
                            "ledger_updated": False,
                        },
                        "remaining_budget": {"consumed_kcal": 320, "remaining_kcal": 992},
                        "manager_rounds": [],
                    },
                ],
                "debug_surface": {
                    "model": {
                        "same_truth": {
                            "status": "pass",
                            "debug_model_consumed_kcal": 320,
                            "current_budget_consumed_kcal": 320,
                        },
                        "today_summary": {"consumed_kcal": 320, "remaining_kcal": 992},
                        "correction_history": [
                            {"removed_item_names": []},
                            {"removed_item_names": ["湯"]},
                        ],
                        "meal_threads": [
                            {
                                "active_version": {
                                    "version_reason": "correction",
                                    "parent_version_id": 2,
                                    "total_kcal": 320,
                                    "items": [{"estimated_kcal": 320}],
                                },
                                "superseded_versions": [{"meal_version_id": 1}, {"meal_version_id": 2}],
                            }
                        ],
                    }
                },
            }
        ],
    }


def test_rt10e_blocking_clarify_correction_live_probe_gate_passes() -> None:
    artifact = module.build_rt10e_blocking_clarify_correction_live_probe_gate(
        blocking_clarify_artifact=_blocking_artifact(),
        correction_artifact=_correction_artifact(),
    )

    assert artifact["artifact_type"] == "accurate_intake_rt10e_blocking_clarify_correction_live_probe_gate"
    assert artifact["target_manager_runtime_gate"] == "rt10e_blocking_clarify_correction_live_probe"
    assert artifact["status"] == "pass"
    assert artifact["supports_journeys"] == ["D", "K"]


def test_rt10e_gate_blocks_if_blocking_followup_commits() -> None:
    source = _blocking_artifact()
    source["cases"][0]["turns"][0]["state_delta"]["canonical_commit"] = True

    artifact = module.build_rt10e_blocking_clarify_correction_live_probe_gate(
        blocking_clarify_artifact=source,
        correction_artifact=_correction_artifact(),
    )

    assert artifact["status"] == "fail"
    assert "blocking_turn1_canonical_commit_present" in artifact["blockers"]


def test_rt10e_gate_blocks_if_remove_item_skips_target_resolution() -> None:
    source = _correction_artifact()
    source["cases"][0]["turns"][2]["manager_rounds"][0]["decision"]["tool_calls"] = [{"name": "estimate_nutrition"}]

    artifact = module.build_rt10e_blocking_clarify_correction_live_probe_gate(
        blocking_clarify_artifact=_blocking_artifact(),
        correction_artifact=source,
    )

    assert artifact["status"] == "fail"
    assert "correction_turn3_unexpected_tool_inventory" in artifact["blockers"]


def test_rt10e_gate_cli_writes_artifact(tmp_path: Path) -> None:
    blocking_path = tmp_path / "blocking.json"
    correction_path = tmp_path / "correction.json"
    output_path = tmp_path / "accurate_intake_rt10e_blocking_clarify_correction_live_probe_gate.json"
    blocking_path.write_text(json.dumps(_blocking_artifact(), ensure_ascii=False), encoding="utf-8")
    correction_path.write_text(json.dumps(_correction_artifact(), ensure_ascii=False), encoding="utf-8")

    rc = module.main(
        [
            "--blocking-clarify-artifact",
            str(blocking_path),
            "--correction-artifact",
            str(correction_path),
            "--output",
            str(output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "accurate_intake_rt10e_blocking_clarify_correction_live_probe_gate"
