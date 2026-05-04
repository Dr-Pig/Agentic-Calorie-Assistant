from __future__ import annotations

from typing import Any

from app.memory.application.derived_summaries import (
    build_golden_order_summary,
    build_preference_profile_summary,
)
from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.fixture_reader import (
    _committed_meal_events,
    _source_section_counts,
)
from app.memory.application.long_term_context_shadow.utils import (
    _bounded_confidence,
    _float_value,
    _list_of_dicts,
    _model_dict,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _candidate_extraction_engine_v2_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    meal_events = _committed_meal_events(fixture)
    preference_summary = build_preference_profile_summary(meal_events)
    golden_order_summary = build_golden_order_summary(meal_events)
    menu_context = _menu_scan_shadow_context(fixture)
    return _base_artifact(
        artifact_type="candidate_extraction_engine_v2",
        fixture=fixture,
        extra={
            "source_spec_alignment": [
                "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
                "docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md",
                "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
                "docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md",
            ],
            "active_menu_scan_runtime_used": False,
            "memory_layers": [
                {
                    "layer_id": "l1_typed_history_observation",
                    "runtime_truth_owner": "canonical_typed_history",
                    "durable_memory_written": False,
                },
                {
                    "layer_id": "l2a_deterministic_pattern",
                    "runtime_truth_owner": "shadow_deterministic_consolidation",
                    "durable_memory_written": False,
                },
                {
                    "layer_id": "l3_review_candidate_only",
                    "runtime_truth_owner": "human_review_future_promotion",
                    "durable_memory_written": False,
                },
            ],
            "source_section_counts": _source_section_counts(fixture),
            "extracted_candidates": [
                _candidate_extraction_record(candidate) for candidate in candidates
            ],
            "shadow_profile_views": {
                "preference_profile_summary": _model_dict(preference_summary),
                "golden_order_summary": _model_dict(golden_order_summary),
                "pre_materialized_runtime_summary_written": False,
                "style_profile_materialized": False,
                "style_profile_reason": (
                    "L4A keeps conversation_style_profile as a later extension point."
                ),
            },
            "menu_scan_shadow_context": menu_context,
            "weekly_highlight_shadow_candidates": _weekly_highlight_shadow_candidates(
                fixture,
            ),
        },
    )


def _candidate_extraction_record(
    candidate: LongTermContextCandidate,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "layer_id": _candidate_layer_id(candidate),
        "source_trace_ids": candidate.source_trace_ids,
        "source_object_refs": candidate.source_object_refs,
        "evidence_count": candidate.evidence_count,
        "confidence": candidate.confidence,
        "freshness_posture": candidate.freshness_posture,
        "payload_extracts": _candidate_payload_extracts(candidate),
        "intended_consumers": candidate.intended_consumers,
        "runtime_effect_allowed": False,
        "durable_memory_written": False,
    }


def _candidate_layer_id(candidate: LongTermContextCandidate) -> str:
    if candidate.candidate_type in {
        "pattern",
        "food_preference",
        "logging_adherence_pattern",
        "intake_estimation_bias",
        "app_usage_style",
        "interaction_preference",
    }:
        return "l2a_deterministic_pattern"
    return "l3_review_candidate_only"


def _candidate_payload_extracts(candidate: LongTermContextCandidate) -> dict[str, Any]:
    payload = candidate.payload
    if candidate.candidate_type == "user_language_pattern":
        return {
            "user_phrase": payload.get("user_phrase"),
            "observed_meaning": payload.get("observed_meaning"),
            "portion_semantics": payload.get("portion_semantics") or {},
            "pattern_subtype": payload.get("pattern_subtype"),
        }
    if candidate.candidate_type == "intake_estimation_bias":
        return {
            "bias_direction": payload.get("bias_direction"),
            "missed_item_patterns": payload.get("missed_item_patterns") or [],
            "correction_tendencies": payload.get("correction_tendencies") or [],
            "evidence_subtypes": payload.get("evidence_subtypes") or [],
        }
    if candidate.candidate_type == "app_usage_style":
        return {
            "usage_signal_distribution": payload.get("usage_signal_distribution") or {},
        }
    if candidate.candidate_type == "interaction_preference":
        return {"preference_signal": payload.get("preference_signal")}
    if candidate.candidate_type == "golden_order":
        return {
            "store_name": payload.get("store_name"),
            "item_names": payload.get("item_names") or [],
            "materialized_from_canonical_history": True,
        }
    return dict(payload)


def _menu_scan_shadow_context(fixture: dict[str, Any]) -> dict[str, Any]:
    menu = fixture.get("menu_scan_context")
    if not isinstance(menu, dict):
        return {
            "available": False,
            "runtime_recommendation_mode_started": False,
            "parsed_item_count": 0,
            "candidate_source_only": True,
        }
    parsed_items = _list_of_dicts(menu.get("parsed_items"))
    return {
        "available": True,
        "scan_source": str(menu.get("scan_source") or "unknown"),
        "restaurant_name": str(menu.get("restaurant_name") or ""),
        "parsed_item_count": len(parsed_items),
        "parse_confidence": _bounded_confidence(
            menu.get("parse_confidence"),
            default=0.0,
        ),
        "unparsed_item_count": len(menu.get("unparsed_items") or []),
        "runtime_recommendation_mode_started": False,
        "candidate_source_only": True,
        "manager_context_injected": False,
        "intake_state_created": False,
    }


def _weekly_highlight_shadow_candidates(fixture: dict[str, Any]) -> dict[str, Any]:
    budgets = _list_of_dicts(fixture.get("budget_summaries"))
    overshoot_days = [
        item for item in budgets if _float_value(item.get("overshoot_kcal")) > 0
    ]
    at_or_under_budget = len(budgets) - len(overshoot_days)
    positive_highlights = []
    if at_or_under_budget > 0:
        positive_highlights.append(
            {
                "highlight_id": "budget-days-at-or-under-target",
                "text": f"{at_or_under_budget} fixture day(s) at or under target",
                "source": "budget_summaries",
            }
        )
    return {
        "derived_view_only": True,
        "weekly_insight_report_written": False,
        "proactive_sent": False,
        "narrative_summary_generated": False,
        "budget_day_count": len(budgets),
        "overshoot_days": len(overshoot_days),
        "positive_highlights": positive_highlights,
        "insufficient_data_posture": len(budgets) < 7,
    }
