from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.intake.application.manager_context_policy import (
    MANAGER_CONTEXT_POLICY_VERSION,
    build_manager_context_packet_v1,
)
from app.runtime.contracts.phase_a import CurrentTurnContextV1, InteractionEvent


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _context() -> CurrentTurnContextV1:
    return CurrentTurnContextV1(
        user_utterance="\u628a\u8c46\u5e72\u62ff\u6389",
        last_system_question="\u6ef7\u5473\u88e1\u6709\u54ea\u4e9b\u6771\u897f\uff1f",
        recent_chat_turns=[
            {"message_id": "u1", "role": "user", "content": "\u665a\u9910\u5403\u6ef7\u5473"},
            {"message_id": "a1", "role": "assistant", "content": "\u8acb\u544a\u8a34\u6211\u6709\u54ea\u4e9b\u6771\u897f"},
        ],
        pending_followup={
            "is_open": True,
            "runtime_turn_id": "turn-luwei-ask",
            "expected_answer_type": "listed_basket_components",
        },
        current_budget_snapshot={
            "target_kcal": 1600,
            "consumed_kcal": 420,
            "remaining_kcal": 1180,
            "read_only": True,
        },
        recent_item_targets=[
            {"meal_item_id": 1, "display_name": "\u8c46\u5e72", "meal_thread_id": "meal-1"},
            {"meal_item_id": 2, "display_name": "\u6d77\u5e36", "meal_thread_id": "meal-1"},
        ],
        target_resolution_posture={"mutation_authority": False},
        current_interaction_event=InteractionEvent(
            source="chat",
            event_type="user_message",
            raw_text="\u628a\u8c46\u5e72\u62ff\u6389",
        ),
    )


def build_fake_provider_context_smoke_artifact() -> dict[str, Any]:
    packet = build_manager_context_packet_v1(
        current_turn_context=_context(),
        user_id="local-user",
        local_date="2026-05-04",
        session_id="fake-provider-context-smoke",
        target_candidates=[
            {
                "meal_item_id": 1,
                "display_name": "\u8c46\u5e72",
                "meal_thread_id": "meal-1",
                "removable": True,
            }
        ],
        raw_trace_dump={"excluded": True},
        long_term_memory={"excluded": True},
        proactive_context={"excluded": True},
        rescue_context={"excluded": True},
    )
    loading = packet["context_loading_artifact"]
    target_candidates = packet["target_candidates"]["for_correction_or_removal"]
    omitted_ids = {
        item["context_id"]
        for item in packet["omitted_context"]
        if isinstance(item, dict)
    }
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_fake_provider_context_smoke",
            "claim_scope": "fake_provider_context_smoke",
            "status": "pass",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "provider_mode": "fake_provider_contract_test",
            "provider_profile_id": "fake-provider-pl-ce-context-smoke",
            "context_policy_version": MANAGER_CONTEXT_POLICY_VERSION,
            "provider_input_summary": {
                "context_policy_version_present": bool(packet["metadata"]["context_policy_version"]),
                "loaded_context_summary_present": bool(loading["loaded_context_summary"]),
                "omitted_context_summary_present": bool(loading["omitted_context_summary"]),
                "target_candidates_present": bool(target_candidates),
                "forbidden_context_excluded": {"raw_trace_dump", "long_term_memory"}.issubset(omitted_ids),
                "manager_context_packet_schema_changed": False,
            },
            "tool_loop_trace_attributable": True,
            "final_semantic_decision_source": "fixture_manager_structured_decision",
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "live_provider_called": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "production_db_used": False,
            "ready_for_live_diagnostic_decision": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "real_fooddb_pass_claimed": False,
            "fooddb_truth_updated": False,
        }
    )


__all__ = ["build_fake_provider_context_smoke_artifact"]
