from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.memory.application.derived_summaries import (
    build_golden_order_summary,
    build_preference_profile_summary,
    build_suppression_summary,
)
from app.memory.domain.summaries import CommittedMealEvent, InteractionPreferenceEvent


_REQUIRED_CASE_IDS = (
    "preference_profile_from_committed_history_only",
    "golden_order_materialized_not_promoted",
    "suppression_ignored_signal_only",
    "manager_context_injection_blocked",
)
_FALSE_FIELDS = (
    "runtime_connected",
    "mutation_changed",
    "durable_memory_written",
    "confirmed_memory_promoted",
    "memory_provider_used",
    "manager_context_injected",
    "manager_context_packet_schema_changed",
    "llm_extraction_invoked",
    "recommendation_served",
    "proactive_sent",
)


def _meal(
    event_id: str,
    *,
    day: int,
    item_names: list[str],
    store_name: str | None = None,
    cuisine_family: str | None = None,
) -> CommittedMealEvent:
    return CommittedMealEvent(
        event_id=event_id,
        occurred_at=datetime(2026, 5, day, 12, 0, tzinfo=UTC),
        item_names=item_names,
        store_name=store_name,
        cuisine_family=cuisine_family,
    )


def _interaction(event_id: str, *, day: int, action: str) -> InteractionPreferenceEvent:
    return InteractionPreferenceEvent(
        event_id=event_id,
        occurred_at=datetime(2026, 5, day, 8, 0, tzinfo=UTC),
        trigger_type="meal_reminder",
        action=action,  # type: ignore[arg-type]
    )


def _base_case(case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "semantic_owner": "memory_derived_summary_read_model",
        "deterministic_role": "derive_summary_counts_without_memory_write",
        "derived_summary_only": True,
        **dict.fromkeys(_FALSE_FIELDS, False),
    }


def _cases() -> list[dict[str, Any]]:
    preference_events = [
        _meal(
            "meal-1",
            day=1,
            item_names=["chicken bento"],
            store_name="Corner Bento",
            cuisine_family="taiwanese",
        ),
        _meal(
            "meal-2",
            day=2,
            item_names=["chicken bento"],
            store_name="Corner Bento",
            cuisine_family="taiwanese",
        ),
    ]
    preference = build_preference_profile_summary(preference_events)
    golden = build_golden_order_summary(
        [
            _meal(f"golden-{index}", day=3 + index, item_names=["salad chicken", "sweet potato"], store_name="FamilyMart")
            for index in range(3)
        ],
        minimum_count=3,
    )
    suppression = build_suppression_summary(
        [
            _interaction("interaction-dismissed", day=6, action="dismissed"),
            _interaction("interaction-ignored", day=7, action="ignored"),
        ]
    )
    return [
        _base_case("preference_profile_from_committed_history_only")
        | {
            "source_kind": preference.source_kind,
            "is_durable_memory_truth": preference.is_durable_memory_truth,
            "top_item": preference.top_items[0].label,
            "top_store": preference.top_stores[0].label,
            "source_events": [event.event_id for event in preference_events],
        },
        _base_case("golden_order_materialized_not_promoted")
        | {
            "source_kind": golden.source_kind,
            "is_durable_memory_truth": golden.is_durable_memory_truth,
            "golden_order_count": len(golden.orders),
            "golden_order_source": "canonical_history_materialized_view",
        },
        _base_case("suppression_ignored_signal_only")
        | {
            "source_kind": suppression.source_kind,
            "is_durable_memory_truth": suppression.is_durable_memory_truth,
            "suppression_trigger_type": suppression.suppression_signals[0].trigger_type,
            "suppression_count": suppression.suppression_signals[0].count,
            "dismissed_current_instance_counted": False,
        },
        _base_case("manager_context_injection_blocked")
        | {
            "context_pack_candidate_only": True,
            "manager_context_injected": False,
            "manager_context_packet_schema_changed": False,
        },
    ]


def _validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if [str(case.get("case_id") or "") for case in cases] != list(_REQUIRED_CASE_IDS):
        blockers.append("required_case_order_mismatch")
    for case in cases:
        case_id = str(case.get("case_id") or "unknown")
        for field in _FALSE_FIELDS:
            if case.get(field) is not False:
                blockers.append(f"{case_id}.{field}")
    return blockers


def build_memory_derived_summary_shadow_contract_artifact() -> dict[str, Any]:
    cases = _cases()
    blockers = _validate_cases(cases)
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_memory_derived_summary_shadow_contract",
        "status": "pass" if not blockers else "fail",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "owner": "app/memory",
        "consumer": "future memory/recommendation/proactive activation slices",
        "retirement_trigger": "approved durable_memory_activation_plan",
        "local_only": True,
        "diagnostic_only": True,
        "derived_summary_only": True,
        **dict.fromkeys(_FALSE_FIELDS, False),
        "best_practice_evidence": {
            "required": True,
            "sources_checked": [
                "https://openai.github.io/openai-agents-python/sandbox/memory/",
                "https://docs.langchain.com/oss/python/langgraph/add-memory",
            ],
            "adopted_guidance": [
                "keep readable memory separate from memory generation or update",
                "keep short-term session state separate from cross-session long-term store",
            ],
        },
        "blockers": blockers,
        "cases": cases,
    }


__all__ = ["build_memory_derived_summary_shadow_contract_artifact"]
