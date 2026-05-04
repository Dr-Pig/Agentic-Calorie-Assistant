from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _scenario(
    *,
    scenario_id: str,
    raw_user_input: str,
    target_resolution_status: str,
    pending_pin_present: bool = False,
    context_candidates_present: bool = True,
    omitted_context_expected: bool = False,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "raw_user_input": raw_user_input,
        "raw_user_input_role": "display_only",
        "semantic_source": "fixture_manager_structured_decision",
        "context_candidates_present": context_candidates_present,
        "pending_pin_present": pending_pin_present,
        "omitted_context_expected": omitted_context_expected,
        "target_resolution_status": target_resolution_status,
        "ambiguity_preserved": target_resolution_status == "ambiguous",
        "deterministic_supplies_candidates_and_pins_only": True,
        "deterministic_semantic_inference_used": False,
        "raw_text_intent_router_used": False,
        "mutation_authority": False,
    }


def _scenarios() -> list[dict[str, Any]]:
    return [
        _scenario(
            scenario_id="remove_previous_item",
            raw_user_input="\u628a\u525b\u525b\u90a3\u500b\u62ff\u6389",
            target_resolution_status="ambiguous",
        ),
        _scenario(
            scenario_id="remove_named_item",
            raw_user_input="\u8c46\u5e72\u62ff\u6389",
            target_resolution_status="candidate_supported",
        ),
        _scenario(
            scenario_id="modify_drink_sugar",
            raw_user_input="\u90a3\u676f\u6539\u534a\u7cd6",
            target_resolution_status="candidate_supported",
        ),
        _scenario(
            scenario_id="modify_rice_portion",
            raw_user_input="\u98ef\u6539\u5c11\u4e00\u9ede",
            target_resolution_status="candidate_supported",
        ),
        _scenario(
            scenario_id="correct_previous_identity",
            raw_user_input="\u525b\u525b\u90a3\u500b\u5176\u5be6\u4e0d\u662f\u62ff\u9435",
            target_resolution_status="ambiguous",
        ),
        _scenario(
            scenario_id="pending_followup_answer",
            raw_user_input="\u6709\u8c46\u5e72\u3001\u6d77\u5e36\u3001\u8ca2\u4e38",
            target_resolution_status="pending_draft_supported",
            pending_pin_present=True,
        ),
        _scenario(
            scenario_id="long_chat_with_pinned_pending_draft",
            raw_user_input="\u525b\u525b\u90a3\u4efd\u6ef7\u5473\u88e1\u9084\u6709\u7c73\u8840",
            target_resolution_status="pending_draft_supported",
            pending_pin_present=True,
        ),
        _scenario(
            scenario_id="remove_lunch_rice_scoped",
            raw_user_input="\u5348\u9910\u90a3\u500b\u98ef\u62ff\u6389",
            target_resolution_status="candidate_supported",
        ),
        _scenario(
            scenario_id="modify_previous_drink_unsweetened",
            raw_user_input="\u525b\u525b\u90a3\u676f\u6539\u7121\u7cd6",
            target_resolution_status="candidate_supported",
        ),
        _scenario(
            scenario_id="pending_quantity_answer",
            raw_user_input="\u5169\u584a\u8c46\u5e72\u4e00\u4efd\u6d77\u5e36",
            target_resolution_status="pending_draft_supported",
            pending_pin_present=True,
        ),
        _scenario(
            scenario_id="cancel_logging_intent_requires_manager",
            raw_user_input="\u4e0d\u662f\u8981\u8a18\uff0c\u6211\u53ea\u662f\u554f",
            target_resolution_status="manager_semantic_required",
            context_candidates_present=False,
        ),
        _scenario(
            scenario_id="outside_current_day_reference_omitted",
            raw_user_input="\u6628\u5929\u90a3\u676f\u4e0d\u8981\u7b97",
            target_resolution_status="outside_current_day_omitted",
            context_candidates_present=False,
            omitted_context_expected=True,
        ),
    ]


def build_context_replay_pack_artifact() -> dict[str, Any]:
    scenarios = _scenarios()
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_replay_pack",
            "status": "generated",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "local_context_replay_pack",
            "local_only": True,
            "diagnostic_only": True,
            "deterministic_supplies_candidates_and_pins_only": True,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "manager_context_packet_schema_changed": False,
            "real_fooddb_pass_claimed": False,
            "fooddb_truth_updated": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "scenario_count": len(scenarios),
            "summary": {
                "scenario_count": len(scenarios),
                "ambiguous_scenarios": sum(
                    1 for scenario in scenarios if scenario["target_resolution_status"] == "ambiguous"
                ),
                "pending_pin_scenarios": sum(
                    1 for scenario in scenarios if scenario["pending_pin_present"] is True
                ),
                "manager_semantic_required_scenarios": sum(
                    1
                    for scenario in scenarios
                    if scenario["target_resolution_status"] == "manager_semantic_required"
                ),
                "outside_current_day_omitted_scenarios": sum(
                    1
                    for scenario in scenarios
                    if scenario["target_resolution_status"] == "outside_current_day_omitted"
                ),
            },
            "scenarios": scenarios,
        }
    )


__all__ = ["build_context_replay_pack_artifact"]
