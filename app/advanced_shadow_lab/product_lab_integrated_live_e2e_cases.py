from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory_tool_lookup_fixtures import (
    FakeMemoryToolLookupProvider,
)
from app.advanced_shadow_lab.product_lab_memory_tool_lookup_live_diagnostic import (
    run_memory_tool_lookup_live_diagnostic,
)
from app.advanced_shadow_lab.product_lab_proactive_feedback_live_diagnostic import (
    FakeProactiveFeedbackProvider,
    run_proactive_feedback_live_diagnostic,
)
from app.advanced_shadow_lab.product_lab_recommendation_blocker_live_diagnostic import (
    FakeRecommendationBlockerProvider,
    run_recommendation_blocker_live_diagnostic,
)
from app.advanced_shadow_lab.product_lab_rescue_memory_context_live_diagnostic import (
    FakeRescueMemoryContextProvider,
    run_rescue_memory_context_live_diagnostic,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn


def build_integrated_live_e2e_case_bundle() -> dict[str, Any]:
    components = {
        "memory_tool_lookup": run_memory_tool_lookup_live_diagnostic(
            provider=FakeMemoryToolLookupProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
            provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        ),
        "recommendation_blocker": run_recommendation_blocker_live_diagnostic(
            provider=FakeRecommendationBlockerProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
            provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        ),
        "rescue_memory_context": run_rescue_memory_context_live_diagnostic(
            provider=FakeRescueMemoryContextProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
            provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        ),
        "proactive_feedback": run_proactive_feedback_live_diagnostic(
            provider=FakeProactiveFeedbackProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
            provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        ),
    }
    product_turn = _product_lab_turn()
    statuses = {name: str(artifact.get("status") or "") for name, artifact in components.items()}
    statuses["product_lab_turn"] = str(product_turn.get("status") or "")
    return {
        "component_statuses": statuses,
        "component_summaries": {
            "memory_tool_lookup": _memory_summary(components["memory_tool_lookup"]),
            "recommendation_blocker": _recommendation_summary(
                components["recommendation_blocker"]
            ),
            "rescue_memory_context": _rescue_summary(components["rescue_memory_context"]),
            "proactive_feedback": _proactive_summary(components["proactive_feedback"]),
        },
        "product_lab_turn_summary": _turn_summary(product_turn),
    }


def _product_lab_turn() -> dict[str, Any]:
    return run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            "session_id": "integrated-live-e2e",
            "turn_id": "turn-pr12",
            "surface": "chat",
            "semantic_intent_fixture": "advanced_recommendation_rescue_proactive_loop",
            "lab_now_minute": 0,
        },
        fixture_inputs=build_product_lab_fixture_inputs(),
        lab_memory_context_pack=_memory_pack(),
    )


def _memory_pack() -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_memory_context_pack",
        "status": "pass",
        "session_id": "integrated-live-e2e",
        "turn_id": "turn-pr12",
        "entries": [
            {
                "record_id": "memory-oatmeal",
                "memory_type": "golden_order",
                "summary": "Morning Bar oatmeal is reliable before meetings.",
                "store_name": "Morning Bar",
                "item_names": ["oatmeal"],
                "estimated_kcal": 420,
                "intended_consumers": ["recommendation", "proactive"],
            }
        ],
        "selected_record_ids": ["memory-oatmeal"],
        "negative_preference_blockers": [],
        "memory_tools_enabled": True,
        "memory_tool_calls": [{"tool": "memory.search", "selected_record_ids": ["memory-oatmeal"]}],
        "memory_context_injected": True,
        "lab_manager_context_injected": True,
        "lab_memory_context_pack_used": True,
        "mainline_activation_enabled": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "blockers": [],
    }


def _memory_summary(artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": artifact.get("status"),
        "memory_record_first": artifact.get("memory_record_first") is True,
        "bounded_evidence_read": artifact.get("bounded_evidence_read") is True,
    }


def _recommendation_summary(artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": artifact.get("status"),
        "lab_recommendation_served": artifact.get("lab_recommendation_served") is True,
        "negative_block_before_offer": artifact.get("negative_block_before_offer") is True,
    }


def _rescue_summary(artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": artifact.get("status"),
        "memory_context_used": artifact.get("memory_context_used") is True,
        "claim_drift_rejected": artifact.get("claim_drift_rejected") is True,
    }


def _proactive_summary(artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": artifact.get("status"),
        "scheduler_delivery_allowed": artifact.get("scheduler_delivery_allowed") is True,
        "proactive_delivery_enabled": artifact.get("proactive_delivery_enabled") is True,
    }


def _turn_summary(turn: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": turn.get("status"),
        "lab_user_facing_behavior_changed": turn.get("lab_user_facing_behavior_changed")
        is True,
        "memory_context_injected": turn.get("memory_context_injected") is True,
        "recommendation_served_to_lab": _mapping(
            turn.get("product_lab_recommendation_artifact")
        ).get("recommendation_served_to_lab")
        is True,
        "rescue_proposal_presented_to_lab": _mapping(
            turn.get("product_lab_rescue_artifact")
        ).get("proposal_presented_to_lab")
        is True,
        "proactive_candidate_count": _mapping(turn.get("product_lab_proactive_artifact")).get(
            "candidate_count"
        ),
        "mainline_activation_enabled": turn.get("mainline_activation_enabled") is True,
        "canonical_product_mutation_allowed": turn.get(
            "canonical_product_mutation_allowed"
        )
        is True,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_integrated_live_e2e_case_bundle"]
