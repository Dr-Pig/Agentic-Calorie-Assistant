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
    requires_manager_or_clarification: bool,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "raw_user_input": raw_user_input,
        "raw_user_input_role": "display_only",
        "semantic_source": "fixture_manager_structured_decision",
        "fixture_manager_decision": {
            "target_resolution_status": target_resolution_status,
            "requires_manager_or_clarification": requires_manager_or_clarification,
        },
        "context_target_candidates_present": True,
        "target_candidate_count": 2,
        "target_resolution_status": target_resolution_status,
        "requires_manager_or_clarification": requires_manager_or_clarification,
        "deterministic_selected_target": False,
        "deterministic_semantic_inference_used": False,
        "mutation_authority": False,
    }


def _scenarios() -> list[dict[str, Any]]:
    return [
        _scenario(
            scenario_id="remove_previous_reference",
            raw_user_input="\u628a\u525b\u525b\u90a3\u500b\u62ff\u6389",
            target_resolution_status="ambiguous",
            requires_manager_or_clarification=True,
        ),
        _scenario(
            scenario_id="remove_named_item",
            raw_user_input="\u8c46\u5e72\u62ff\u6389",
            target_resolution_status="candidate_supported",
            requires_manager_or_clarification=False,
        ),
        _scenario(
            scenario_id="modify_drink_sugar",
            raw_user_input="\u90a3\u676f\u6539\u534a\u7cd6",
            target_resolution_status="candidate_supported",
            requires_manager_or_clarification=False,
        ),
        _scenario(
            scenario_id="modify_rice_portion",
            raw_user_input="\u98ef\u6539\u5c11\u4e00\u9ede",
            target_resolution_status="candidate_supported",
            requires_manager_or_clarification=False,
        ),
        _scenario(
            scenario_id="correct_previous_identity",
            raw_user_input="\u525b\u525b\u90a3\u500b\u5176\u5be6\u4e0d\u662f\u62ff\u9435",
            target_resolution_status="ambiguous",
            requires_manager_or_clarification=True,
        ),
    ]


def build_context_target_candidate_eval_artifact() -> dict[str, Any]:
    scenarios = _scenarios()
    ambiguous = sum(
        1 for scenario in scenarios if scenario["target_resolution_status"] == "ambiguous"
    )
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_target_candidate_eval",
            "status": "generated",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "local_context_target_candidate_eval",
            "local_only": True,
            "diagnostic_only": True,
            "fixture_manager_used": True,
            "deterministic_semantic_inference_used": False,
            "deterministic_selected_target": False,
            "manager_context_packet_schema_changed": False,
            "mutation_authority": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "scenario_count": len(scenarios),
            "summary": {
                "scenario_count": len(scenarios),
                "ambiguous_scenarios": ambiguous,
                "candidate_supported_scenarios": len(scenarios) - ambiguous,
                "deterministic_selected_target": False,
            },
            "scenarios": scenarios,
        }
    )


__all__ = ["build_context_target_candidate_eval_artifact"]
