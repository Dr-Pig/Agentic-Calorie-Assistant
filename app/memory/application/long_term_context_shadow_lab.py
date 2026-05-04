from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from app.memory.application.derived_summaries import (
    build_golden_order_summary,
    build_preference_profile_summary,
)
from app.memory.domain.long_term_context_candidates import (
    ContextValueReviewItem,
    LongTermContextCandidate,
)
from app.memory.domain.summaries import CommittedMealEvent
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.long_term_context_shadow_lab"
)

SHADOW_NON_CLAIM_FLAGS: dict[str, bool] = {
    "shadow_mode": True,
    "real_runtime_effect": False,
    "dogfood_db_mutated": False,
    "durable_memory_written": False,
    "manager_context_injected": False,
    "proactive_sent": False,
    "recommendation_served": False,
    "rescue_committed": False,
    "body_plan_mutated": False,
    "day_budget_mutated": False,
    "meal_thread_mutated": False,
    "product_readiness_claimed": False,
    "private_self_use_approved": False,
}

DOGFOOD_EXPORT_SECTIONS: tuple[str, ...] = (
    "meal_logs",
    "body_observations",
    "budget_summaries",
    "calibration_diagnostics",
    "language_observations",
    "intake_estimation_events",
    "app_usage_events",
    "interaction_events",
    "negative_preference_observations",
    "temporary_preference_observations",
    "conversation_history_summaries",
    "trace_metadata",
    "candidate_pool",
    "menu_scan_context",
    "review_actions",
)

CHAT_TRACE_SECTION_ALIASES: tuple[str, ...] = (
    "chat_trace_metadata",
    "chat_traces",
    "conversation_trace_metadata",
)

ARTIFACT_CONSUMER_CATALOG: dict[str, list[str]] = {
    "artifact_registry_manifest": ["human_review", "architecture_governance"],
    "long_term_memory_candidate_review": [
        "human_review",
        "recommendation",
        "intake_clarification",
        "calibration",
        "chat_context",
    ],
    "context_value_review_queue": ["human_review", "architecture_governance"],
    "context_signal_quality_scorecard": [
        "human_review",
        "architecture_governance",
    ],
    "candidate_extraction_engine_v2": [
        "human_review",
        "architecture_governance",
        "recommendation",
        "intake_clarification",
        "calibration",
    ],
    "context_value_scoring_v2": [
        "human_review",
        "architecture_governance",
        "recommendation",
        "intake_clarification",
        "calibration",
    ],
    "shadow_replay_evaluators": [
        "human_review",
        "recommendation",
        "intake_clarification",
        "calibration",
    ],
    "review_queue_reducer": ["human_review", "architecture_governance"],
    "context_pack_token_pressure_shadow_eval": [
        "context_packing_review",
        "architecture_governance",
    ],
    "proactive_no_send_simulation": ["proactive", "human_review"],
    "recommendation_shadow_eval": ["recommendation", "human_review"],
    "rescue_shadow_candidates": ["rescue_later", "human_review"],
    "memory_review_action_shadow_result": ["human_review", "memory_governance"],
    "memory_promotion_demotion_shadow_eval": ["human_review", "memory_governance"],
    "semantic_pattern_extraction_shadow_plan": [
        "recommendation",
        "nightly_insight",
        "confirmed_memory_candidate_review",
    ],
    "conversation_recall_shadow_eval": [
        "chat_context",
        "intake_clarification",
        "recommendation",
        "calibration",
    ],
    "conversation_recall_tool_shadow_plan": [
        "chat_context",
        "future_manager_context_retrieval",
    ],
    "conversation_recall_retrieval_shadow_eval": [
        "chat_context",
        "intake_clarification",
        "recommendation",
        "calibration",
    ],
    "entity_normalization_shadow_plan": [
        "architecture_governance",
        "recommendation",
        "intake_clarification",
        "calibration",
    ],
    "context_quality_contradiction_review_queue": [
        "human_review",
        "architecture_governance",
    ],
    "capability_scenario_fixture_pack": [
        "human_review",
        "architecture_governance",
    ],
    "pr_review_autopilot_closeout": ["human_review", "delivery_governance"],
    "long_term_context_pack_shadow_eval": [
        "recommendation",
        "intake_clarification",
        "chat_context",
        "calibration",
        "proactive",
        "rescue_later",
    ],
    "product_capability_context_map": [
        "architecture_governance",
        "human_review",
    ],
    "external_memory_framework_research_review": [
        "architecture_governance",
        "human_review",
    ],
    "local_memory_framework_review": ["architecture_governance", "human_review"],
    "local_memory_framework_deep_review": [
        "architecture_governance",
        "human_review",
    ],
}


def build_shadow_lab_artifacts(
    fixture_payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    fixture = _normalize_dogfood_export_payload(fixture_payload)
    candidates = _build_candidates(fixture)
    context_items = _build_context_value_items(candidates)

    artifacts = {
        "long_term_memory_candidate_review": _memory_candidate_review_artifact(
            fixture,
            candidates,
        ),
        "context_value_review_queue": _context_value_review_queue_artifact(
            fixture,
            context_items,
        ),
        "context_signal_quality_scorecard": _context_signal_quality_scorecard_artifact(
            fixture,
            candidates,
        ),
        "candidate_extraction_engine_v2": _candidate_extraction_engine_v2_artifact(
            fixture,
            candidates,
        ),
        "context_value_scoring_v2": _context_value_scoring_v2_artifact(
            fixture,
            candidates,
        ),
        "shadow_replay_evaluators": _shadow_replay_evaluators_artifact(
            fixture,
            candidates,
        ),
        "review_queue_reducer": _review_queue_reducer_artifact(
            fixture,
            candidates,
        ),
        "context_pack_token_pressure_shadow_eval": (
            _context_pack_token_pressure_shadow_artifact(
                fixture,
                candidates,
            )
        ),
        "proactive_no_send_simulation": _proactive_no_send_artifact(
            fixture, candidates
        ),
        "recommendation_shadow_eval": _recommendation_shadow_artifact(
            fixture, candidates
        ),
        "rescue_shadow_candidates": _rescue_shadow_artifact(fixture, candidates),
        "memory_review_action_shadow_result": _memory_review_action_shadow_artifact(
            fixture,
            candidates,
        ),
        "memory_promotion_demotion_shadow_eval": (
            _memory_promotion_demotion_shadow_artifact(
                fixture,
                candidates,
            )
        ),
        "semantic_pattern_extraction_shadow_plan": (
            _semantic_pattern_extraction_shadow_artifact(
                fixture,
            )
        ),
        "conversation_recall_shadow_eval": _conversation_recall_shadow_artifact(
            fixture,
            candidates,
        ),
        "conversation_recall_tool_shadow_plan": (
            _conversation_recall_tool_shadow_plan_artifact(
                fixture,
                candidates,
            )
        ),
        "conversation_recall_retrieval_shadow_eval": (
            _conversation_recall_retrieval_shadow_artifact(
                fixture,
                candidates,
            )
        ),
        "entity_normalization_shadow_plan": _entity_normalization_shadow_artifact(
            fixture,
            candidates,
        ),
        "context_quality_contradiction_review_queue": (
            _context_quality_contradiction_review_artifact(
                fixture,
                candidates,
            )
        ),
        "capability_scenario_fixture_pack": _capability_scenario_fixture_pack_artifact(
            fixture,
            candidates,
        ),
        "pr_review_autopilot_closeout": _pr_review_autopilot_closeout_artifact(
            fixture,
        ),
        "long_term_context_pack_shadow_eval": _long_term_context_pack_shadow_artifact(
            fixture,
            candidates,
        ),
        "product_capability_context_map": _product_capability_context_map_artifact(
            fixture,
            candidates,
        ),
    }
    artifacts = {
        "artifact_registry_manifest": _artifact_registry_manifest_artifact(
            fixture,
            artifacts,
        ),
        **artifacts,
    }
    return artifacts


def build_artifact_registry_manifest(
    fixture_payload: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    fixture = (
        dict(fixture_payload)
        if "_input_reader" in fixture_payload
        else _normalize_dogfood_export_payload(fixture_payload)
    )
    return _artifact_registry_manifest_artifact(
        fixture,
        {
            artifact_key: artifact
            for artifact_key, artifact in artifacts.items()
            if artifact_key != "artifact_registry_manifest"
        },
    )


def _normalize_dogfood_export_payload(
    fixture_payload: dict[str, Any],
) -> dict[str, Any]:
    root = dict(fixture_payload or {})
    export_root, source_shape = _dogfood_export_root(root)
    fixture = dict(root)

    normalized_sections: list[str] = []
    for section in DOGFOOD_EXPORT_SECTIONS:
        if section in export_root:
            fixture[section] = export_root[section]
            normalized_sections.append(section)

    if "conversation_history_summaries" not in fixture:
        for alias in CHAT_TRACE_SECTION_ALIASES:
            if alias in export_root:
                fixture["conversation_history_summaries"] = export_root[alias]
                normalized_sections.append("conversation_history_summaries")
                break

    fixture["_input_reader"] = {
        "source_shape": source_shape,
        "fixture_input_used": True,
        "real_dogfood_export_used": False,
        "real_dogfood_export_claim_ignored": source_shape != "top_level_fixture",
        "normalized_sections": sorted(set(normalized_sections)),
        "supported_sections": list(DOGFOOD_EXPORT_SECTIONS) + ["chat_trace_metadata"],
        "direct_db_access_used": False,
        "live_provider_called": False,
    }
    return fixture


def _dogfood_export_root(root: dict[str, Any]) -> tuple[dict[str, Any], str]:
    for key in ("dogfood_export", "dogfood_exports", "exports", "export"):
        value = root.get(key)
        if isinstance(value, dict):
            return dict(value), key
    return root, "top_level_fixture"


def _base_artifact(
    *,
    artifact_type: str,
    fixture: dict[str, Any],
    extra: dict[str, Any],
) -> dict[str, Any]:
    generated_at = str(fixture.get("generated_at_utc") or "1970-01-01T00:00:00+00:00")
    contract = artifact_review_contract(artifact_type)
    payload = {
        "artifact_schema_version": "1.0",
        "artifact_type": artifact_type,
        "status": "generated",
        "generated_at_utc": generated_at,
        "claim_scope": "long_term_context_shadow_lab",
        "local_only": True,
        "diagnostic_only": True,
        "fixture_input_used": True,
        "real_dogfood_export_used": False,
        "input_reader": fixture.get("_input_reader")
        or {
            "source_shape": "top_level_fixture",
            "fixture_input_used": True,
            "real_dogfood_export_used": False,
            "real_dogfood_export_claim_ignored": False,
            "normalized_sections": [],
            "supported_sections": list(DOGFOOD_EXPORT_SECTIONS)
            + ["chat_trace_metadata"],
            "direct_db_access_used": False,
            "live_provider_called": False,
        },
        **SHADOW_NON_CLAIM_FLAGS,
        **contract,
        **extra,
    }
    payload["runtime_effect_allowed"] = False
    return _json_safe(payload)


def artifact_review_contract(artifact_type: str) -> dict[str, Any]:
    consumers = ARTIFACT_CONSUMER_CATALOG.get(
        artifact_type,
        ["human_review", "architecture_governance"],
    )
    return {
        "intended_consumers": consumers,
        "consumer_use_hints": _consumer_use_hints(consumers),
        "risk_if_wrong": _artifact_risk_if_wrong(artifact_type),
        "promotion_path": _artifact_promotion_path(artifact_type),
        "runtime_effect_allowed": False,
        "why_this_is_not_runtime_truth": _artifact_non_runtime_truth_reason(
            artifact_type
        ),
    }


def _artifact_registry_manifest_artifact(
    fixture: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    entries = [
        _artifact_registry_entry(
            artifact_key="artifact_registry_manifest",
            artifact_type="artifact_registry_manifest",
            artifact=artifact_review_contract("artifact_registry_manifest"),
        )
    ]
    entries.extend(
        _artifact_registry_entry(
            artifact_key=artifact_key,
            artifact_type=str(artifact.get("artifact_type") or artifact_key),
            artifact=artifact,
        )
        for artifact_key, artifact in artifacts.items()
    )
    artifacts_without_consumers = [
        entry["artifact_key"] for entry in entries if not entry["intended_consumers"]
    ]
    pseudo_runtime_truth_risks = [
        entry["artifact_key"]
        for entry in entries
        if entry["runtime_effect_allowed"] or not entry["why_this_is_not_runtime_truth"]
    ]
    return _base_artifact(
        artifact_type="artifact_registry_manifest",
        fixture=fixture,
        extra={
            "manifest_scope": "batch_1_shadow_lab_artifact_registry",
            "artifact_count": len(entries),
            "artifact_registry_entries": entries,
            "artifacts_without_consumers": artifacts_without_consumers,
            "pseudo_runtime_truth_risks": pseudo_runtime_truth_risks,
            "all_artifacts_have_future_consumers": not artifacts_without_consumers,
            "all_artifacts_block_runtime_truth": not pseudo_runtime_truth_risks,
        },
    )


def _artifact_registry_entry(
    *,
    artifact_key: str,
    artifact_type: str,
    artifact: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_key": artifact_key,
        "artifact_type": artifact_type,
        "intended_consumers": list(artifact.get("intended_consumers") or []),
        "consumer_use_hints": dict(artifact.get("consumer_use_hints") or {}),
        "risk_if_wrong": str(artifact.get("risk_if_wrong") or ""),
        "promotion_path": str(artifact.get("promotion_path") or ""),
        "runtime_effect_allowed": bool(artifact.get("runtime_effect_allowed") is True),
        "why_this_is_not_runtime_truth": str(
            artifact.get("why_this_is_not_runtime_truth") or ""
        ),
        "manager_context_injection_allowed": False,
        "durable_memory_write_allowed": False,
        "future_consumer_declared": bool(artifact.get("intended_consumers")),
    }


def _build_candidates(fixture: dict[str, Any]) -> list[LongTermContextCandidate]:
    user_id = str(fixture.get("user_id") or "fixture-user")
    meals = _list_of_dicts(fixture.get("meal_logs"))
    body_observations = _list_of_dicts(fixture.get("body_observations"))
    budgets = _list_of_dicts(fixture.get("budget_summaries"))
    diagnostics = _list_of_dicts(fixture.get("calibration_diagnostics"))
    language_observations = _list_of_dicts(fixture.get("language_observations"))
    bias_events = _list_of_dicts(fixture.get("intake_estimation_events"))
    usage_events = _list_of_dicts(fixture.get("app_usage_events"))
    interaction_events = _list_of_dicts(fixture.get("interaction_events"))
    negative_preferences = _list_of_dicts(
        fixture.get("negative_preference_observations")
    )
    temporary_preferences = _list_of_dicts(
        fixture.get("temporary_preference_observations")
    )
    conversation_summaries = _list_of_dicts(
        fixture.get("conversation_history_summaries")
    )
    trace_refs = _trace_refs(fixture)

    candidates: list[LongTermContextCandidate] = []
    candidates.extend(_meal_distribution_candidates(user_id, meals, trace_refs))
    candidates.extend(_golden_order_candidates(user_id, meals, trace_refs))
    candidates.extend(_body_logging_candidates(user_id, body_observations, trace_refs))
    candidates.extend(_budget_candidates(user_id, budgets, trace_refs))
    candidates.extend(_calibration_candidates(user_id, diagnostics, trace_refs))
    candidates.extend(_language_candidates(user_id, language_observations, trace_refs))
    candidates.extend(
        _intake_estimation_bias_candidates(user_id, bias_events, trace_refs)
    )
    candidates.extend(_app_usage_style_candidates(user_id, usage_events, trace_refs))
    candidates.extend(
        _interaction_preference_candidates(user_id, interaction_events, trace_refs)
    )
    candidates.extend(
        _negative_preference_candidates(user_id, negative_preferences, trace_refs)
    )
    candidates.extend(
        _temporary_preference_candidates(user_id, temporary_preferences, trace_refs)
    )
    candidates.extend(
        _conversation_recall_context_candidates(
            user_id, conversation_summaries, trace_refs
        )
    )
    return candidates


def _meal_distribution_candidates(
    user_id: str,
    meals: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not meals:
        return []

    item_kinds: Counter[str] = Counter()
    staple_types: Counter[str] = Counter()
    drinks: Counter[str] = Counter()
    time_buckets: Counter[str] = Counter()
    trace_ids: list[str] = []
    observed_at: list[datetime] = []

    for meal in meals:
        trace_ids.append(_trace_id(meal))
        item_kinds.update(str(value) for value in meal.get("item_kinds") or [])
        staple_types.update(str(value) for value in meal.get("staple_types") or [])
        drinks.update(str(value) for value in meal.get("drink_names") or [])
        time_buckets[_time_bucket(meal.get("logged_at"))] += 1
        parsed = _parse_datetime(meal.get("logged_at"))
        if parsed:
            observed_at.append(parsed)

    candidates = [
        _candidate(
            candidate_id="pattern-item-kind-distribution",
            candidate_type="pattern",
            user_id=user_id,
            source_trace_ids=trace_ids,
            source_object_refs=_source_refs_for_meals(meals, trace_refs),
            evidence_count=len(meals),
            observed_at=observed_at,
            confidence=_confidence(len(meals), threshold=5),
            proposed_memory_text="Observed meal item-kind distribution in fixture logs",
            payload={"distribution": dict(sorted(item_kinds.items()))},
            reason_codes=["l2a_item_kind_distribution"],
            intended_consumers=["recommendation", "intake_clarification"],
        ),
        _candidate(
            candidate_id="pattern-time-of-day-distribution",
            candidate_type="pattern",
            user_id=user_id,
            source_trace_ids=trace_ids,
            source_object_refs=_source_refs_for_meals(meals, trace_refs),
            evidence_count=len(meals),
            observed_at=observed_at,
            confidence=_confidence(len(meals), threshold=5),
            proposed_memory_text="Observed time-of-day logging pattern in fixture logs",
            payload={"distribution": dict(sorted(time_buckets.items()))},
            reason_codes=["l2a_time_of_day_pattern"],
            intended_consumers=["chat_context", "proactive", "intake_clarification"],
        ),
    ]

    if staple_types:
        label, count = _most_common(staple_types)
        candidates.append(
            _candidate(
                candidate_id=f"preference-staple-{_slug(label)}",
                candidate_type="food_preference",
                user_id=user_id,
                source_trace_ids=_trace_ids_matching(meals, "staple_types", label),
                source_object_refs=_source_refs_matching(
                    meals, trace_refs, "staple_types", label
                ),
                evidence_count=count,
                observed_at=observed_at,
                confidence=_confidence(count, threshold=5),
                proposed_memory_text=f"Candidate staple preference: {label}",
                payload={
                    "preference_kind": "staple_type",
                    "value": label,
                    "count": count,
                },
                reason_codes=["l2a_staple_type_distribution"],
                intended_consumers=[
                    "recommendation",
                    "proactive",
                    "intake_clarification",
                ],
            )
        )

    if drinks:
        label, count = _most_common(drinks)
        candidates.append(
            _candidate(
                candidate_id=f"preference-drink-{_slug(label)}",
                candidate_type="food_preference",
                user_id=user_id,
                source_trace_ids=_trace_ids_matching(meals, "drink_names", label),
                source_object_refs=_source_refs_matching(
                    meals, trace_refs, "drink_names", label
                ),
                evidence_count=count,
                observed_at=observed_at,
                confidence=_confidence(count, threshold=5),
                proposed_memory_text=f"Candidate drink preference: {label}",
                payload={"preference_kind": "drink", "value": label, "count": count},
                reason_codes=["l2a_drink_preference_strength"],
                intended_consumers=[
                    "recommendation",
                    "proactive",
                    "intake_clarification",
                ],
            )
        )

    return candidates


def _golden_order_candidates(
    user_id: str,
    meals: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    grouped: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = defaultdict(list)
    for meal in meals:
        store_name = meal.get("store_name")
        item_names = tuple(str(item) for item in meal.get("item_names") or [])
        if store_name and item_names:
            grouped[(str(store_name), item_names)].append(meal)

    candidates: list[LongTermContextCandidate] = []
    for (store_name, item_names), matches in sorted(grouped.items()):
        if len(matches) < 3:
            continue
        observed_at = [_parse_datetime(meal.get("logged_at")) for meal in matches]
        item_text = ", ".join(item_names)
        candidates.append(
            _candidate(
                candidate_id=f"golden-order-{_slug(store_name)}-{_slug('-'.join(item_names))}",
                candidate_type="golden_order",
                user_id=user_id,
                source_trace_ids=[_trace_id(meal) for meal in matches],
                source_object_refs=_source_refs_for_meals(matches, trace_refs),
                evidence_count=len(matches),
                observed_at=[value for value in observed_at if value is not None],
                confidence=_confidence(len(matches), threshold=3),
                proposed_memory_text=f"Possible golden order: {store_name} - {item_text}",
                payload={
                    "store_name": store_name,
                    "item_names": list(item_names),
                    "materialized_from_canonical_history": True,
                    "not_promoted_memory": True,
                },
                reason_codes=["golden_order_materialized_view_candidate"],
                intended_consumers=[
                    "recommendation",
                    "intake_clarification",
                    "chat_context",
                ],
            )
        )
    return candidates


def _body_logging_candidates(
    user_id: str,
    observations: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not observations:
        return []
    observed_at = [_parse_datetime(item.get("observed_at")) for item in observations]
    trace_ids = [_trace_id(item) for item in observations]
    refs = [
        _source_ref(
            item,
            trace_refs,
            fallback_kind="BodyObservation",
            fallback_id_key="trace_id",
        )
        for item in observations
    ]
    return [
        _candidate(
            candidate_id="pattern-weight-logging-consistency",
            candidate_type="logging_adherence_pattern",
            user_id=user_id,
            source_trace_ids=trace_ids,
            source_object_refs=refs,
            evidence_count=len(observations),
            observed_at=[value for value in observed_at if value is not None],
            confidence=_confidence(len(observations), threshold=4),
            proposed_memory_text="Observed body logging consistency candidate",
            payload={"observation_count": len(observations)},
            reason_codes=["l2a_weight_logging_consistency"],
            intended_consumers=["calibration", "proactive", "rescue_later"],
        )
    ]


def _budget_candidates(
    user_id: str,
    budgets: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not budgets:
        return []
    overshoots = [
        budget for budget in budgets if _float_value(budget.get("overshoot_kcal")) > 0
    ]
    trace_ids = [_trace_id(budget) for budget in budgets]
    observed_at = [_parse_date_as_datetime(budget.get("date")) for budget in budgets]
    return [
        _candidate(
            candidate_id="pattern-budget-overshoot-frequency",
            candidate_type="logging_adherence_pattern",
            user_id=user_id,
            source_trace_ids=trace_ids,
            source_object_refs=[
                _source_ref(
                    budget,
                    trace_refs,
                    fallback_kind="DayBudgetLedger",
                    fallback_id_key="date",
                )
                for budget in budgets
            ],
            evidence_count=len(budgets),
            observed_at=[value for value in observed_at if value is not None],
            confidence=_confidence(len(overshoots), threshold=3),
            proposed_memory_text="Observed budget overshoot frequency candidate",
            payload={
                "budget_day_count": len(budgets),
                "overshoot_day_count": len(overshoots),
                "overshoot_frequency": len(overshoots) / len(budgets),
            },
            reason_codes=["l2a_overshoot_frequency"],
            intended_consumers=["calibration", "proactive", "rescue_later"],
        )
    ]


def _calibration_candidates(
    user_id: str,
    diagnostics: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not diagnostics:
        return []
    trace_ids = [_trace_id(diagnostic) for diagnostic in diagnostics]
    return [
        _candidate(
            candidate_id="pattern-calibration-mismatch-trend",
            candidate_type="pattern",
            user_id=user_id,
            source_trace_ids=trace_ids,
            source_object_refs=[
                _source_ref(
                    diagnostic,
                    trace_refs,
                    fallback_kind="CalibrationDiagnostic",
                    fallback_id_key="trace_id",
                )
                for diagnostic in diagnostics
            ],
            evidence_count=len(diagnostics),
            observed_at=[
                value
                for value in (
                    _parse_date_as_datetime(diagnostic.get("window_end"))
                    for diagnostic in diagnostics
                )
                if value is not None
            ],
            confidence=_confidence(len(diagnostics), threshold=3),
            proposed_memory_text="Observed calibration mismatch trend candidate",
            payload={"diagnostics": diagnostics},
            reason_codes=["l2a_calibration_mismatch_trend"],
            intended_consumers=["calibration", "intake_risk_tagging"],
        )
    ]


def _language_candidates(
    user_id: str,
    observations: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    candidates: list[LongTermContextCandidate] = []
    for observation in observations:
        phrase = str(observation.get("user_phrase") or "unknown_phrase")
        observed_at = _parse_datetime(observation.get("observed_at"))
        candidates.append(
            _candidate(
                candidate_id=f"user-language-{_slug(phrase)}",
                candidate_type="user_language_pattern",
                user_id=user_id,
                source_trace_ids=[_trace_id(observation)],
                source_object_refs=[
                    _source_ref(
                        observation,
                        trace_refs,
                        fallback_kind="UserLanguageObservation",
                        fallback_id_key="trace_id",
                    )
                ],
                evidence_count=1,
                observed_at=[observed_at] if observed_at else [],
                confidence=_bounded_confidence(
                    observation.get("confidence"), default=0.4
                ),
                proposed_memory_text=f'Candidate user-language meaning: "{phrase}"',
                payload={
                    "user_phrase": phrase,
                    "observed_meaning": observation.get("observed_meaning"),
                    "pattern_subtype": str(
                        observation.get("phrase_kind") or "semantic_alias"
                    ),
                    "portion_semantics": observation.get("portion_semantics") or {},
                },
                reason_codes=["user_language_semantic_alias_candidate"],
                intended_consumers=[
                    "intake_clarification",
                    "chat_context",
                    "recommendation",
                ],
            )
        )
    return candidates


def _intake_estimation_bias_candidates(
    user_id: str,
    events: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not events:
        return []
    directions: Counter[str] = Counter(
        str(event.get("bias_direction") or "unknown") for event in events
    )
    direction, count = _most_common(directions)
    observed_at = [_parse_datetime(event.get("observed_at")) for event in events]
    missed_item_patterns = _dedupe(
        [
            str(event.get("missed_item_kind"))
            for event in events
            if event.get("missed_item_kind")
        ]
    )
    correction_tendencies = _dedupe(
        [
            str(event.get("correction_tendency"))
            for event in events
            if event.get("correction_tendency")
        ]
    )
    evidence_subtypes = _dedupe(
        [
            *(
                str(event.get("event_kind"))
                for event in events
                if event.get("event_kind")
            ),
            *(["correction_tendency"] if correction_tendencies else []),
        ]
    )
    return [
        _candidate(
            candidate_id=f"intake-estimation-bias-{_slug(direction)}",
            candidate_type="intake_estimation_bias",
            user_id=user_id,
            source_trace_ids=[_trace_id(event) for event in events],
            source_object_refs=[
                _source_ref(
                    event,
                    trace_refs,
                    fallback_kind="IntakeEstimationBiasObservation",
                    fallback_id_key="trace_id",
                )
                for event in events
            ],
            evidence_count=len(events),
            observed_at=[value for value in observed_at if value is not None],
            confidence=_confidence(count, threshold=3),
            proposed_memory_text=f"Candidate intake estimation bias posture: {direction}",
            payload={
                "bias_direction": direction,
                "events": events,
                "evidence_subtypes": evidence_subtypes,
                "missed_item_patterns": missed_item_patterns,
                "correction_tendencies": correction_tendencies,
            },
            reason_codes=["intake_estimation_bias_candidate"],
            intended_consumers=[
                "calibration",
                "intake_risk_tagging",
                "nutrition_clarify_priority",
                "response_context",
            ],
        )
    ]


def _app_usage_style_candidates(
    user_id: str,
    events: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not events:
        return []
    signals: Counter[str] = Counter(
        str(event.get("usage_signal") or "unknown") for event in events
    )
    observed_at = [_parse_datetime(event.get("observed_at")) for event in events]
    return [
        _candidate(
            candidate_id="app-usage-style-pattern",
            candidate_type="app_usage_style",
            user_id=user_id,
            source_trace_ids=[_trace_id(event) for event in events],
            source_object_refs=[
                _source_ref(
                    event,
                    trace_refs,
                    fallback_kind="AppUsageEvent",
                    fallback_id_key="trace_id",
                )
                for event in events
            ],
            evidence_count=len(events),
            observed_at=[value for value in observed_at if value is not None],
            confidence=_confidence(len(events), threshold=5),
            proposed_memory_text="Candidate app usage style pattern",
            payload={"usage_signal_distribution": dict(sorted(signals.items()))},
            reason_codes=["app_usage_style_candidate"],
            intended_consumers=[
                "chat_context",
                "proactive",
                "ux",
                "recommendation_presentation",
            ],
        )
    ]


def _interaction_preference_candidates(
    user_id: str,
    events: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not events:
        return []
    signals: Counter[str] = Counter(
        str(event.get("preference_signal") or "unknown") for event in events
    )
    signal, count = _most_common(signals)
    observed_at = [_parse_datetime(event.get("observed_at")) for event in events]
    return [
        _candidate(
            candidate_id=f"interaction-preference-{_slug(signal)}",
            candidate_type="interaction_preference",
            user_id=user_id,
            source_trace_ids=[_trace_id(event) for event in events],
            source_object_refs=[
                _source_ref(
                    event,
                    trace_refs,
                    fallback_kind="InteractionPreferenceEvent",
                    fallback_id_key="trace_id",
                )
                for event in events
            ],
            evidence_count=len(events),
            observed_at=[value for value in observed_at if value is not None],
            confidence=_confidence(count, threshold=3),
            proposed_memory_text=f"Candidate interaction preference: {signal}",
            payload={"preference_signal": signal, "events": events},
            reason_codes=["interaction_preference_candidate"],
            intended_consumers=[
                "response_generation",
                "chat_context",
                "proactive_message_style",
            ],
        )
    ]


def _negative_preference_candidates(
    user_id: str,
    observations: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    candidates: list[LongTermContextCandidate] = []
    for observation in observations:
        scope = str(observation.get("preference_scope") or "general")
        value = str(observation.get("value") or "unknown")
        observed_at = _parse_datetime(observation.get("observed_at"))
        candidates.append(
            _candidate(
                candidate_id=f"negative-preference-{_slug(scope)}-{_slug(value)}",
                candidate_type="negative_preference",
                user_id=user_id,
                source_trace_ids=[_trace_id(observation)],
                source_object_refs=[
                    _source_ref(
                        observation,
                        trace_refs,
                        fallback_kind="NegativePreferenceObservation",
                        fallback_id_key="trace_id",
                    )
                ],
                evidence_count=1,
                observed_at=[observed_at] if observed_at else [],
                confidence=_bounded_confidence(
                    observation.get("confidence"), default=0.5
                ),
                proposed_memory_text=f"Candidate negative preference: avoid {value}",
                payload={
                    "preference_scope": scope,
                    "value": value,
                    "source_signal": observation.get("source_signal"),
                    "confirmed": False,
                },
                reason_codes=["negative_preference_candidate"],
                intended_consumers=[
                    "recommendation",
                    "proactive",
                    "intake_clarification",
                ],
            )
        )
    return candidates


def _temporary_preference_candidates(
    user_id: str,
    observations: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    candidates: list[LongTermContextCandidate] = []
    for observation in observations:
        value = str(observation.get("value") or "unknown")
        observed_at = _parse_datetime(observation.get("observed_at"))
        valid_until = str(observation.get("valid_until") or "")
        candidates.append(
            _candidate(
                candidate_id=f"temporary-preference-{_slug(value)}",
                candidate_type="temporary_preference",
                user_id=user_id,
                source_trace_ids=[_trace_id(observation)],
                source_object_refs=[
                    _source_ref(
                        observation,
                        trace_refs,
                        fallback_kind="TemporaryPreferenceObservation",
                        fallback_id_key="trace_id",
                    )
                ],
                evidence_count=1,
                observed_at=[observed_at] if observed_at else [],
                confidence=_bounded_confidence(
                    observation.get("confidence"), default=0.5
                ),
                proposed_memory_text=(
                    f"Candidate temporary preference through {valid_until}: {value}"
                ),
                payload={
                    "preference_type": observation.get("preference_type"),
                    "value": value,
                    "context_scope": observation.get("context_scope"),
                    "valid_from": observation.get("valid_from"),
                    "valid_until": observation.get("valid_until"),
                    "confirmed": False,
                },
                reason_codes=["temporary_preference_candidate"],
                intended_consumers=[
                    "recommendation",
                    "chat_context",
                    "proactive",
                    "intake_clarification",
                ],
            )
        )
    return candidates


def _conversation_recall_context_candidates(
    user_id: str,
    summaries: list[dict[str, Any]],
    trace_refs: dict[str, str],
) -> list[LongTermContextCandidate]:
    if not summaries:
        return []
    observed_at = [_parse_datetime(summary.get("observed_at")) for summary in summaries]
    return [
        _candidate(
            candidate_id="conversation-recall-context-summary",
            candidate_type="conversation_recall_context",
            user_id=user_id,
            source_trace_ids=[_trace_id(summary) for summary in summaries],
            source_object_refs=[
                _source_ref(
                    summary,
                    trace_refs,
                    fallback_kind="ConversationArchive",
                    fallback_id_key="conversation_id",
                )
                for summary in summaries
            ],
            evidence_count=len(summaries),
            observed_at=[value for value in observed_at if value is not None],
            confidence=_confidence(len(summaries), threshold=3),
            proposed_memory_text="Candidate conversation recall context from summary-first archive",
            payload={
                "summary_first": True,
                "raw_transcript_included": False,
                "manager_tool_call_allowed": False,
                "retrieval_tool_allowed_later": True,
                "conversation_summaries": summaries,
            },
            reason_codes=["conversation_history_retrieval_context_candidate"],
            intended_consumers=[
                "chat_context",
                "intake_clarification",
                "recommendation",
                "calibration",
            ],
        )
    ]


def _candidate(
    *,
    candidate_id: str,
    candidate_type: str,
    user_id: str,
    source_trace_ids: list[str],
    source_object_refs: list[str],
    evidence_count: int,
    observed_at: list[datetime],
    confidence: float,
    proposed_memory_text: str,
    payload: dict[str, Any],
    reason_codes: list[str],
    intended_consumers: list[str] | None = None,
) -> LongTermContextCandidate:
    clean_observed_at = sorted(_normalize_datetime(value) for value in observed_at)
    redacted_payload, redacted_fields = _redact_secret_values(payload)
    secret_status = (
        "redacted_secret_fields_detected"
        if redacted_fields
        else "passed_no_secret_fields_detected"
    )
    return LongTermContextCandidate(
        candidate_id=candidate_id,
        candidate_type=candidate_type,
        user_id=user_id,
        source_trace_ids=_dedupe(source_trace_ids),
        source_object_refs=_dedupe(source_object_refs),
        evidence_count=evidence_count,
        evidence_window_start=clean_observed_at[0] if clean_observed_at else None,
        evidence_window_end=clean_observed_at[-1] if clean_observed_at else None,
        confidence=confidence,
        freshness_posture="recent" if clean_observed_at else "unknown",
        staleness_note=None,
        proposed_memory_text=proposed_memory_text,
        payload=redacted_payload,
        scope_keys={
            "user_id": user_id,
            "workspace_id": "fixture_workspace",
            "project_id": "fixture_project",
            "surface": "fixture_shadow_lab",
        },
        secret_scan={
            "status": secret_status,
            "raw_secret_values_stored": False,
            "redacted_fields": redacted_fields,
        },
        privacy_contract={
            "raw_secret_values_stored": False,
            "scope_keys_required": True,
            "source_refs_required": True,
            "runtime_prompt_injection_allowed": False,
        },
        retention_posture="shadow_review_artifact_only",
        injection_eligibility={
            "eligible": False,
            "reason": "shadow_lab_no_runtime_injection",
        },
        runtime_injection_allowed=False,
        intended_consumers=intended_consumers or _default_consumers(candidate_type),
        consumer_use_hints=_consumer_use_hints(
            intended_consumers or _default_consumers(candidate_type)
        ),
        risk_if_wrong=_risk_if_wrong(candidate_type),
        promotion_path=_promotion_path(candidate_type),
        why_this_is_not_runtime_truth=_candidate_non_runtime_truth_reason(
            candidate_type
        ),
        reason_codes=reason_codes,
    )


def _build_context_value_items(
    candidates: list[LongTermContextCandidate],
) -> list[ContextValueReviewItem]:
    items: list[ContextValueReviewItem] = []
    for candidate in candidates:
        if candidate.candidate_type == "golden_order":
            capabilities = ["recommendation", "intake_clarification"]
            action = "ask_user_to_confirm"
        elif candidate.candidate_type == "food_preference":
            capabilities = ["recommendation", "proactive", "intake_clarification"]
            action = "ask_user_to_confirm"
        elif candidate.candidate_type == "negative_preference":
            capabilities = ["recommendation", "proactive", "intake_clarification"]
            action = "ask_user_to_confirm"
        elif candidate.candidate_type == "temporary_preference":
            capabilities = ["recommendation", "chat_context", "proactive"]
            action = "ask_user_to_confirm"
        elif candidate.candidate_type == "user_language_pattern":
            capabilities = ["intake_clarification", "chat_context"]
            action = "keep_shadowing"
        elif candidate.candidate_type == "intake_estimation_bias":
            capabilities = ["calibration", "intake_risk_tagging"]
            action = "keep_shadowing"
        elif candidate.candidate_type == "app_usage_style":
            capabilities = ["chat_context", "proactive"]
            action = "keep_shadowing"
        elif candidate.candidate_type == "interaction_preference":
            capabilities = ["response_generation", "chat_context"]
            action = "keep_shadowing"
        elif candidate.candidate_type == "conversation_recall_context":
            capabilities = ["chat_context", "intake_clarification"]
            action = "keep_shadowing"
        elif "calibration" in candidate.reason_codes[0]:
            capabilities = ["calibration", "rescue"]
            action = "keep_shadowing"
        elif "overshoot" in candidate.reason_codes[0]:
            capabilities = ["proactive", "rescue"]
            action = "keep_shadowing"
        else:
            capabilities = ["recommendation", "proactive"]
            action = "keep_shadowing"
        strength = (
            "high"
            if candidate.confidence >= 0.8
            else "medium"
            if candidate.confidence >= 0.5
            else "low"
        )
        items.append(
            ContextValueReviewItem(
                review_item_id=f"context-value-{candidate.candidate_id}",
                source_candidate_id=candidate.candidate_id,
                context_found=candidate.proposed_memory_text or candidate.candidate_id,
                helps_capabilities=capabilities,
                why_it_may_be_useful="May reduce repeated clarification or improve shadow ranking once confirmed.",
                evidence_strength=strength,
                possible_harm_if_injected_too_early=(
                    "Could personalize or bias runtime before the user confirms the pattern."
                ),
                recommended_next_action=action,
            )
        )
    return items


def _memory_candidate_review_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    candidate_dicts = [_model_dict(candidate) for candidate in candidates]
    return _base_artifact(
        artifact_type="long_term_memory_candidate_review",
        fixture=fixture,
        extra={
            "summary": {
                "candidate_count": len(candidates),
                "pattern_candidate_count": sum(
                    1
                    for candidate in candidates
                    if candidate.candidate_type == "pattern"
                ),
                "preference_candidate_count": sum(
                    1
                    for candidate in candidates
                    if candidate.candidate_type
                    in {
                        "preference",
                        "food_preference",
                        "temporary_preference",
                    }
                ),
                "negative_preference_candidate_count": sum(
                    1
                    for candidate in candidates
                    if candidate.candidate_type == "negative_preference"
                ),
                "golden_order_candidate_count": sum(
                    1
                    for candidate in candidates
                    if candidate.candidate_type == "golden_order"
                ),
                "durable_memory_written": False,
                "domain_candidate_counts": dict(
                    sorted(
                        Counter(
                            candidate.candidate_type for candidate in candidates
                        ).items()
                    )
                ),
            },
            "candidates": candidate_dicts,
        },
    )


def _context_value_review_queue_artifact(
    fixture: dict[str, Any],
    items: list[ContextValueReviewItem],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="context_value_review_queue",
        fixture=fixture,
        extra={
            "summary": {"review_item_count": len(items)},
            "items": [_model_dict(item) for item in items],
        },
    )


def _context_signal_quality_scorecard_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    scores = [_context_signal_score(candidate) for candidate in candidates]
    return _base_artifact(
        artifact_type="context_signal_quality_scorecard",
        fixture=fixture,
        extra={
            "runtime_effect_allowed": False,
            "scorecard_used_for_runtime_ranking": False,
            "score_dimensions": [
                "evidence_strength",
                "context_value",
                "harm_if_wrong",
                "expiry_sensitivity",
                "recommended_review_action",
            ],
            "candidate_scores": scores,
            "consumer_rollups": _consumer_score_rollups(scores),
        },
    )


def _context_signal_score(candidate: LongTermContextCandidate) -> dict[str, Any]:
    evidence_strength = _evidence_strength(candidate)
    context_value_level = _context_value_level(candidate, evidence_strength)
    harm_level = _harm_if_wrong_level(candidate)
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "intended_consumers": candidate.intended_consumers,
        "evidence_count": candidate.evidence_count,
        "confidence": candidate.confidence,
        "evidence_strength": evidence_strength,
        "context_value_level": context_value_level,
        "harm_if_wrong_level": harm_level,
        "expiry_sensitive": candidate.candidate_type == "temporary_preference",
        "recommended_review_action": _scorecard_review_action(
            candidate,
            context_value_level,
            harm_level,
        ),
        "runtime_effect_allowed": False,
    }


def _evidence_strength(candidate: LongTermContextCandidate) -> str:
    if candidate.confidence >= 0.75 or candidate.evidence_count >= 3:
        return "high"
    if candidate.confidence >= 0.5 or candidate.evidence_count >= 2:
        return "medium"
    return "low"


def _context_value_level(
    candidate: LongTermContextCandidate,
    evidence_strength: str,
) -> str:
    if candidate.candidate_type in {
        "golden_order",
        "negative_preference",
        "temporary_preference",
    }:
        return "high" if evidence_strength in {"medium", "high"} else "medium"
    if candidate.candidate_type in {
        "intake_estimation_bias",
        "user_language_pattern",
        "food_preference",
    }:
        return "medium" if evidence_strength == "low" else "high"
    if candidate.candidate_type in {
        "app_usage_style",
        "interaction_preference",
        "conversation_recall_context",
    }:
        return "medium"
    return evidence_strength


def _harm_if_wrong_level(candidate: LongTermContextCandidate) -> str:
    if candidate.candidate_type in {
        "intake_estimation_bias",
        "negative_preference",
        "temporary_preference",
        "conversation_recall_context",
    }:
        return "high"
    if candidate.candidate_type in {
        "app_usage_style",
        "interaction_preference",
        "logging_adherence_pattern",
        "golden_order",
    }:
        return "medium"
    return "low"


def _scorecard_review_action(
    candidate: LongTermContextCandidate,
    context_value_level: str,
    harm_level: str,
) -> str:
    if candidate.candidate_type in {
        "negative_preference",
        "temporary_preference",
        "golden_order",
        "food_preference",
    }:
        return "ask_user_to_confirm"
    if harm_level == "high" or context_value_level == "low":
        return "keep_shadowing"
    return "keep_shadowing"


def _consumer_score_rollups(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    consumers = sorted(
        {
            consumer
            for score in scores
            for consumer in score.get("intended_consumers", [])
        }
    )
    return [
        {
            "consumer_id": consumer,
            "candidate_count": sum(
                1 for score in scores if consumer in score.get("intended_consumers", [])
            ),
            "candidate_ids": [
                score["candidate_id"]
                for score in scores
                if consumer in score.get("intended_consumers", [])
            ],
            "runtime_effect_allowed": False,
        }
        for consumer in consumers
    ]


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


def _context_value_scoring_v2_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    scores = [_context_value_score_v2(fixture, candidate) for candidate in candidates]
    action_rollups = Counter(score["recommended_action"] for score in scores)
    bucket_rollups = Counter(score["review_priority_bucket"] for score in scores)
    return _base_artifact(
        artifact_type="context_value_scoring_v2",
        fixture=fixture,
        extra={
            "runtime_effect_allowed": False,
            "scorecard_used_for_runtime_ranking": False,
            "score_dimensions": [
                "evidence_strength_score",
                "recency_score",
                "frequency_score",
                "consumer_value_score",
                "harm_if_wrong_score",
                "contradiction_penalty",
                "review_priority_score",
            ],
            "candidate_scores": scores,
            "action_rollups": dict(sorted(action_rollups.items())),
            "bucket_rollups": dict(sorted(bucket_rollups.items())),
            "all_candidates_have_product_capability_value": all(
                bool(score["product_capability_value"]) for score in scores
            ),
        },
    )


def _shadow_replay_evaluators_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    recommendation = _recommendation_shadow_replay(candidates)
    intake = _intake_clarification_shadow_replay(candidates)
    calibration = _calibration_bias_shadow_replay(candidates)
    return _base_artifact(
        artifact_type="shadow_replay_evaluators",
        fixture=fixture,
        extra={
            "recommendation_served": False,
            "intake_commit_requested": False,
            "calibration_math_changed": False,
            "manager_context_packet_written": False,
            "replays": {
                "recommendation_shadow_replay": recommendation,
                "intake_clarification_shadow_replay": intake,
                "calibration_bias_shadow_replay": calibration,
            },
            "replay_count": 3,
        },
    )


def _review_queue_reducer_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    scores = {
        score["candidate_id"]: score
        for score in (
            _context_value_score_v2(fixture, candidate) for candidate in candidates
        )
    }
    queue: dict[str, list[dict[str, Any]]] = {
        "high": [],
        "medium": [],
        "low": [],
        "rejected_or_deferred": [],
    }
    pseudo_runtime_truth_risks = 0
    for candidate in candidates:
        score = scores[candidate.candidate_id]
        if (
            candidate.runtime_effect_allowed
            or not candidate.why_this_is_not_runtime_truth
        ):
            pseudo_runtime_truth_risks += 1
        item = _review_queue_item(candidate, score)
        if score["recommended_action"] == "discard":
            queue["rejected_or_deferred"].append(item)
        else:
            queue[score["review_priority_bucket"]].append(item)

    for bucket_items in queue.values():
        bucket_items.sort(
            key=lambda item: (
                -item["review_priority_score"],
                item["candidate_type"],
                item["candidate_id"],
            )
        )

    return _base_artifact(
        artifact_type="review_queue_reducer",
        fixture=fixture,
        extra={
            "artifact_sprawl_control": {
                "new_artifact_requires_declared_consumer": True,
                "new_artifact_requires_scoring_or_replay_use": True,
                "consumerless_candidates_deferred": True,
            },
            "summary": {
                "candidate_count": len(candidates),
                "high_priority_count": len(queue["high"]),
                "medium_priority_count": len(queue["medium"]),
                "low_priority_count": len(queue["low"]),
                "rejected_or_deferred_count": len(queue["rejected_or_deferred"]),
                "pseudo_runtime_truth_risk_count": pseudo_runtime_truth_risks,
            },
            "review_queue": queue,
        },
    )


def _committed_meal_events(fixture: dict[str, Any]) -> list[CommittedMealEvent]:
    events: list[CommittedMealEvent] = []
    for meal in _list_of_dicts(fixture.get("meal_logs")):
        occurred_at = _parse_datetime(meal.get("logged_at"))
        if occurred_at is None:
            continue
        occurred_at = _normalize_datetime(occurred_at)
        events.append(
            CommittedMealEvent(
                event_id=str(meal.get("meal_id") or _trace_id(meal)),
                occurred_at=occurred_at,
                item_names=[str(item) for item in meal.get("item_names") or []],
                store_name=(
                    str(meal.get("store_name")) if meal.get("store_name") else None
                ),
                cuisine_family=(
                    str(meal.get("cuisine_family"))
                    if meal.get("cuisine_family")
                    else None
                ),
            )
        )
    return events


def _source_section_counts(fixture: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for section in DOGFOOD_EXPORT_SECTIONS:
        value = fixture.get(section)
        if isinstance(value, list):
            counts[section] = len(value)
        elif isinstance(value, dict):
            counts[section] = 1
        else:
            counts[section] = 0
    return counts


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


def _context_value_score_v2(
    fixture: dict[str, Any],
    candidate: LongTermContextCandidate,
) -> dict[str, Any]:
    evidence_strength_score = round(
        max(candidate.confidence, min(candidate.evidence_count / 3, 1.0)),
        3,
    )
    frequency_score = round(min(candidate.evidence_count / 5, 1.0), 3)
    recency_score = _recency_score(candidate)
    consumer_value_score = _consumer_value_score(candidate)
    harm_level = _harm_if_wrong_level(candidate)
    harm_if_wrong_score = _harm_score(harm_level)
    contradiction_penalty = _contradiction_penalty(fixture, candidate)
    review_priority_score = round(
        max(
            0.0,
            min(
                1.0,
                evidence_strength_score * 0.22
                + recency_score * 0.13
                + frequency_score * 0.15
                + consumer_value_score * 0.25
                + harm_if_wrong_score * 0.25
                - contradiction_penalty,
            ),
        ),
        3,
    )
    review_priority_bucket = _review_priority_bucket(review_priority_score)
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "intended_consumers": candidate.intended_consumers,
        "evidence_count": candidate.evidence_count,
        "confidence": candidate.confidence,
        "evidence_strength_score": evidence_strength_score,
        "recency_score": recency_score,
        "frequency_score": frequency_score,
        "consumer_value_score": consumer_value_score,
        "harm_if_wrong_score": harm_if_wrong_score,
        "harm_if_wrong_level": harm_level,
        "contradiction_penalty": contradiction_penalty,
        "review_priority_score": review_priority_score,
        "review_priority_bucket": review_priority_bucket,
        "recommended_action": _scoring_recommended_action(
            candidate,
            review_priority_bucket,
            contradiction_penalty,
        ),
        "product_capability_value": _product_capability_value(candidate),
        "runtime_effect_allowed": False,
    }


def _recency_score(candidate: LongTermContextCandidate) -> float:
    posture_scores = {
        "fresh": 1.0,
        "recent": 0.8,
        "unknown": 0.35,
        "stale": 0.15,
    }
    return posture_scores.get(candidate.freshness_posture, 0.35)


def _consumer_value_score(candidate: LongTermContextCandidate) -> float:
    consumers = set(candidate.intended_consumers)
    if consumers.intersection(
        {
            "recommendation",
            "intake_clarification",
            "calibration",
            "nutrition_clarify_priority",
        }
    ):
        return 0.9
    if consumers.intersection({"chat_context", "proactive", "response_generation"}):
        return 0.7
    if consumers.intersection({"rescue_later", "ux"}):
        return 0.55
    return 0.35


def _harm_score(harm_level: str) -> float:
    if harm_level == "high":
        return 0.9
    if harm_level == "medium":
        return 0.55
    return 0.2


def _contradiction_penalty(
    fixture: dict[str, Any],
    candidate: LongTermContextCandidate,
) -> float:
    if candidate.candidate_type != "negative_preference":
        return 0.0
    value = str(candidate.payload.get("value") or "").lower()
    if not value:
        return 0.0
    pool_names = [
        str(item.get("name") or "").lower()
        for item in _list_of_dicts(fixture.get("candidate_pool"))
    ]
    return 0.25 if any(value in name for name in pool_names) else 0.0


def _review_priority_bucket(score: float) -> str:
    if score >= 0.65:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _scoring_recommended_action(
    candidate: LongTermContextCandidate,
    bucket: str,
    contradiction_penalty: float,
) -> str:
    if not candidate.intended_consumers:
        return "discard"
    if contradiction_penalty > 0:
        return "ask_user_to_confirm"
    if candidate.candidate_type in {
        "negative_preference",
        "temporary_preference",
        "golden_order",
        "food_preference",
    }:
        return "ask_user_to_confirm" if bucket in {"high", "medium"} else "discard"
    if _harm_if_wrong_level(candidate) == "high":
        return "keep_shadowing"
    return "keep_shadowing" if bucket in {"high", "medium"} else "discard"


def _product_capability_value(candidate: LongTermContextCandidate) -> str:
    if candidate.candidate_type in {
        "golden_order",
        "food_preference",
        "negative_preference",
        "temporary_preference",
    }:
        return "direct_recommendation_or_intake_gain"
    if candidate.candidate_type in {
        "intake_estimation_bias",
        "logging_adherence_pattern",
    }:
        return "calibration_or_clarification_gain"
    if candidate.candidate_type in {
        "app_usage_style",
        "interaction_preference",
        "conversation_recall_context",
        "user_language_pattern",
    }:
        return "chat_or_proactive_experience_gain"
    return "broad_product_context_gain"


def _recommendation_shadow_replay(
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    used = [
        candidate
        for candidate in candidates
        if candidate.candidate_type
        in {
            "golden_order",
            "food_preference",
            "negative_preference",
            "temporary_preference",
        }
    ]
    used_ids = {candidate.candidate_id for candidate in used}
    return {
        "replay_id": "recommendation_shadow_replay",
        "expected_user_value": "better_candidate_ranking_review",
        "used_candidate_ids": sorted(used_ids),
        "ignored_candidates": _ignored_candidates(candidates, used_ids),
        "ranking_basis": [
            "preference_profile_summary_shadow",
            "golden_order_shadow",
            "negative_preference_guardrail_shadow",
        ],
        "risk_if_wrong": "Could bias ranking before user-confirmed memory exists.",
        "recommendation_served": False,
        "runtime_effect_allowed": False,
    }


def _intake_clarification_shadow_replay(
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    used = [
        candidate
        for candidate in candidates
        if candidate.candidate_type
        in {"user_language_pattern", "intake_estimation_bias", "negative_preference"}
    ]
    used_ids = {candidate.candidate_id for candidate in used}
    low_confidence_phrase = any(
        candidate.candidate_type == "user_language_pattern"
        and candidate.confidence < 0.7
        for candidate in used
    )
    return {
        "replay_id": "intake_clarification_shadow_replay",
        "expected_user_value": "fewer_but_better_followups_review",
        "used_candidate_ids": sorted(used_ids),
        "ignored_candidates": _ignored_candidates(candidates, used_ids),
        "clarification_policy": (
            "ask_targeted_followup"
            if low_confidence_phrase
            else "use_phrase_pattern_with_caution"
        ),
        "risk_if_wrong": "Could over-assume meaning of a user phrase.",
        "intake_commit_requested": False,
        "runtime_effect_allowed": False,
    }


def _calibration_bias_shadow_replay(
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    used = [
        candidate
        for candidate in candidates
        if candidate.candidate_type
        in {"intake_estimation_bias", "logging_adherence_pattern", "pattern"}
        and (
            "calibration" in candidate.intended_consumers
            or "intake_risk_tagging" in candidate.intended_consumers
        )
    ]
    used_ids = {candidate.candidate_id for candidate in used}
    return {
        "replay_id": "calibration_bias_shadow_replay",
        "expected_user_value": "better_bias_attribution_review",
        "used_candidate_ids": sorted(used_ids),
        "ignored_candidates": _ignored_candidates(candidates, used_ids),
        "does_not_change_calibration_math": True,
        "risk_if_wrong": "Could misattribute mismatch without changing the math.",
        "calibration_math_changed": False,
        "body_plan_mutated": False,
        "day_budget_mutated": False,
        "runtime_effect_allowed": False,
    }


def _ignored_candidates(
    candidates: list[LongTermContextCandidate],
    used_ids: set[str],
) -> list[dict[str, str]]:
    return [
        {
            "candidate_id": candidate.candidate_id,
            "candidate_type": candidate.candidate_type,
            "ignored_reason": "not_relevant_to_this_replay_consumer",
        }
        for candidate in candidates
        if candidate.candidate_id not in used_ids
    ]


def _review_queue_item(
    candidate: LongTermContextCandidate,
    score: dict[str, Any],
) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "review_priority_score": score["review_priority_score"],
        "review_priority_bucket": score["review_priority_bucket"],
        "recommended_action": score["recommended_action"],
        "product_capability_value": score["product_capability_value"],
        "intended_consumers": candidate.intended_consumers,
        "risk_if_wrong": candidate.risk_if_wrong,
        "promotion_path": candidate.promotion_path,
        "runtime_effect_allowed": False,
        "durable_memory_written": False,
        "manager_context_injected": False,
    }


def _context_pack_token_pressure_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    target_window = int(fixture.get("target_context_window_tokens") or 8192)
    packs = _long_term_context_pack_shadow_artifact(fixture, candidates)[
        "context_packs"
    ]
    return _base_artifact(
        artifact_type="context_pack_token_pressure_shadow_eval",
        fixture=fixture,
        extra={
            "source_spec": "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
            "runtime_effect_allowed": False,
            "target_context_window_tokens": target_window,
            "token_pressure_policy": {
                "general_compaction_threshold": 0.6,
                "aggressive_compaction_threshold": 0.8,
                "forced_trim_threshold": 0.9,
            },
            "prune_order": [
                "long_transcript",
                "raw_historical_records",
                "low_value_explanation_text",
                "non_essential_fallback_metadata",
            ],
            "preserve_first": [
                "current_task_object",
                "active_shared_views",
                "safety_guardrails",
                "schema_binding_context",
                "atomic_context_blocks",
            ],
            "atomic_blocks_split_allowed": False,
            "evaluated_packs": [
                _token_pressure_pack_eval(pack, target_window)
                for pack in packs.values()
            ],
        },
    )


def _token_pressure_pack_eval(
    pack: dict[str, Any],
    target_window: int,
) -> dict[str, Any]:
    estimated_tokens = int(pack.get("token_estimate") or 0)
    ratio = estimated_tokens / target_window if target_window > 0 else 0.0
    return {
        "pack_id": pack["pack_id"],
        "estimated_tokens": estimated_tokens,
        "target_context_window_tokens": target_window,
        "pressure_ratio": round(ratio, 4),
        "pressure_level": _token_pressure_level(ratio),
        "summary_first": pack["summary_first"],
        "structured_state_first": pack["structured_state_first"],
        "raw_full_history_dumped": pack["raw_full_history_dumped"],
        "recommended_shadow_action": _token_pressure_action(ratio),
        "runtime_effect_allowed": False,
    }


def _token_pressure_level(ratio: float) -> str:
    if ratio >= 0.9:
        return "forced_trim"
    if ratio >= 0.8:
        return "aggressive_compaction"
    if ratio >= 0.6:
        return "general_compaction"
    return "below_threshold"


def _token_pressure_action(ratio: float) -> str:
    if ratio >= 0.9:
        return "trim_low_priority_blocks_shadow_only"
    if ratio >= 0.8:
        return "aggressively_summarize_shadow_only"
    if ratio >= 0.6:
        return "summarize_non_atomic_blocks_shadow_only"
    return "keep_pack_shape"


def _product_capability_context_map_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    context_domains = _context_domain_catalog()
    candidate_types = sorted({candidate.candidate_type for candidate in candidates})
    expected_candidate_types = {
        "app_usage_style",
        "conversation_recall_context",
        "food_preference",
        "golden_order",
        "intake_estimation_bias",
        "interaction_preference",
        "logging_adherence_pattern",
        "negative_preference",
        "pattern",
        "temporary_preference",
        "user_language_pattern",
    }
    return _base_artifact(
        artifact_type="product_capability_context_map",
        fixture=fixture,
        extra={
            "runtime_effect_allowed": False,
            "canonical_truth_replaced_by_memory": False,
            "source_specs": [
                "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
                "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
                "docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md",
                "docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md",
                "docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md",
                "docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md",
                "docs/specs/L3_3B_CALIBRATION_PROPOSAL_POLICY_RUNTIME_CONTRACT_SPEC.md",
                "docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md",
            ],
            "capability_families": _capability_families(),
            "context_domains": context_domains,
            "consumer_contracts": _consumer_contracts(),
            "candidate_type_to_context_domain": _candidate_type_to_context_domain(),
            "available_candidate_types": candidate_types,
            "coverage_gaps": {
                "fixture_missing_candidate_types": sorted(
                    expected_candidate_types.difference(candidate_types)
                ),
                "runtime_not_integrated_domains": [
                    domain["context_domain_id"] for domain in context_domains
                ],
                "reason": (
                    "Fixture-only shadow lab records product capability pressure "
                    "without claiming durable memory or runtime integration."
                ),
            },
            "llm_deterministic_boundary": {
                "deterministic_role": [
                    "derive L2a statistical patterns",
                    "validate scope keys and non-claim flags",
                    "compile consumer-specific context packs",
                    "reject runtime mutation or injection",
                ],
                "llm_role_later_only": [
                    "extract L2b semantic patterns",
                    "summarize conversation recall candidates",
                    "classify nuanced interaction preference candidates",
                ],
                "human_role": [
                    "accept or reject memory candidates",
                    "confirm durable preference promotion",
                    "approve any future runtime activation",
                ],
                "do_not_override": [
                    "MealThread",
                    "DayBudgetLedger",
                    "BodyPlan",
                    "ProposalContainer",
                    "FoodDB truth",
                    "ManagerContextPacket boundary",
                ],
            },
        },
    )


def _context_domain_catalog() -> list[dict[str, Any]]:
    return [
        {
            "context_domain_id": "food_preference_context",
            "candidate_types": ["food_preference", "pattern"],
            "truth_owner": "memory_derived_from_meal_thread_history",
            "primary_consumers": ["recommendation", "intake_clarification"],
            "risk_if_wrong": "Could overfit ranking or intake defaults to weak evidence.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "negative_preference_context",
            "candidate_types": ["negative_preference"],
            "truth_owner": "human_confirmed_or_reviewed_memory",
            "primary_consumers": ["recommendation", "proactive"],
            "risk_if_wrong": "Could suppress foods or suggestions the user would accept.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "temporary_preference_context",
            "candidate_types": ["temporary_preference"],
            "truth_owner": "time_bounded_reviewed_memory",
            "primary_consumers": ["recommendation", "chat_context", "proactive"],
            "risk_if_wrong": "Could keep expired short-term constraints alive.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "golden_order_context",
            "candidate_types": ["golden_order"],
            "truth_owner": "materialized_view_from_meal_thread_history",
            "primary_consumers": ["recommendation", "intake_clarification"],
            "risk_if_wrong": "Could mistake repeated historical orders for desired defaults.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "user_language_semantic_alias_context",
            "candidate_types": ["user_language_pattern"],
            "truth_owner": "reviewed_language_observation",
            "primary_consumers": [
                "intake_clarification",
                "chat_context",
                "recommendation",
            ],
            "risk_if_wrong": "Could misread personal phrases such as small, normal, or messy eating.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "intake_estimation_bias_context",
            "candidate_types": ["intake_estimation_bias"],
            "truth_owner": "calibration_review_context",
            "primary_consumers": [
                "calibration",
                "nutrition_clarify_priority",
                "intake_risk_tagging",
            ],
            "risk_if_wrong": "Could misattribute calorie mismatch to user logging behavior.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "app_usage_style_context",
            "candidate_types": ["app_usage_style"],
            "truth_owner": "reviewed_usage_pattern",
            "primary_consumers": [
                "chat_context",
                "proactive",
                "cross_surface_experience",
            ],
            "risk_if_wrong": "Could personalize app behavior before the pattern is real.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "interaction_preference_context",
            "candidate_types": ["interaction_preference"],
            "truth_owner": "reviewed_interaction_pattern",
            "primary_consumers": ["chat_context", "proactive", "response_generation"],
            "risk_if_wrong": "Could make answers too terse, too verbose, or ask poorly timed questions.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "logging_adherence_context",
            "candidate_types": ["logging_adherence_pattern", "pattern"],
            "truth_owner": "deterministic_history_aggregation",
            "primary_consumers": ["calibration", "proactive", "rescue_later"],
            "risk_if_wrong": "Could distort confidence in calibration or reminder timing.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "conversation_recall_context",
            "candidate_types": ["conversation_recall_context"],
            "truth_owner": "summary_first_conversation_archive",
            "primary_consumers": [
                "chat_context",
                "intake_clarification",
                "recommendation",
                "calibration",
            ],
            "risk_if_wrong": "Could pull stale prior conversation into the current turn.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "proactive_suppression_context",
            "candidate_types": ["interaction_preference", "app_usage_style"],
            "truth_owner": "future_reviewed_suppression_memory",
            "primary_consumers": ["proactive"],
            "risk_if_wrong": "Could send unwanted nudges or suppress useful ones.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "rescue_history_context",
            "candidate_types": ["logging_adherence_pattern", "pattern"],
            "truth_owner": "proposal_and_budget_history_summary",
            "primary_consumers": ["rescue_later", "calibration"],
            "risk_if_wrong": "Could overstate short-term recovery viability.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "calibration_quality_context",
            "candidate_types": ["intake_estimation_bias", "logging_adherence_pattern"],
            "truth_owner": "calibration_model_context_summary",
            "primary_consumers": ["calibration", "intake_clarification"],
            "risk_if_wrong": "Could reduce trust in body/budget calibration decisions.",
            "runtime_injection_allowed": False,
        },
        {
            "context_domain_id": "cross_surface_context",
            "candidate_types": [
                "app_usage_style",
                "conversation_recall_context",
                "interaction_preference",
            ],
            "truth_owner": "runtime_surface_context_summary",
            "primary_consumers": ["cross_surface_experience", "chat_context"],
            "risk_if_wrong": "Could make chat, UI, and quick actions feel inconsistent.",
            "runtime_injection_allowed": False,
        },
    ]


def _capability_families() -> list[dict[str, Any]]:
    return [
        {
            "family_id": "F1",
            "name": "Plan Bootstrap & Fallback",
            "context_domain_ids": [
                "app_usage_style_context",
                "interaction_preference_context",
                "cross_surface_context",
            ],
            "product_objects": ["body_plan", "day_budget_ledger"],
            "memory_role": "Degraded-mode explanation and onboarding preference context only.",
            "runtime_effect_allowed": False,
        },
        {
            "family_id": "F2",
            "name": "Meal Thread Resolution",
            "context_domain_ids": [
                "user_language_semantic_alias_context",
                "intake_estimation_bias_context",
                "food_preference_context",
                "conversation_recall_context",
            ],
            "product_objects": ["meal_thread"],
            "memory_role": "Clarify better without replacing MealThread or FoodDB truth.",
            "runtime_effect_allowed": False,
        },
        {
            "family_id": "F3",
            "name": "Budget & Cross-Surface Sync",
            "context_domain_ids": [
                "logging_adherence_context",
                "cross_surface_context",
                "conversation_recall_context",
            ],
            "product_objects": ["day_budget_ledger", "meal_thread", "body_plan"],
            "memory_role": "Explain and audit sync context; never mutate ledger truth.",
            "runtime_effect_allowed": False,
        },
        {
            "family_id": "F4",
            "name": "Rescue & Proposal Negotiation",
            "context_domain_ids": [
                "rescue_history_context",
                "logging_adherence_context",
                "interaction_preference_context",
            ],
            "product_objects": ["proposal", "day_budget_ledger"],
            "memory_role": "Future rescue viability and presentation context only.",
            "runtime_effect_allowed": False,
        },
        {
            "family_id": "F5",
            "name": "Body Observation & Calibration",
            "context_domain_ids": [
                "intake_estimation_bias_context",
                "logging_adherence_context",
                "calibration_quality_context",
                "conversation_recall_context",
            ],
            "product_objects": ["body_plan", "proposal"],
            "memory_role": "Support calibration confidence and attribution; do not rewrite plan.",
            "runtime_effect_allowed": False,
        },
        {
            "family_id": "F6",
            "name": "Recommendation & Preference Learning",
            "context_domain_ids": [
                "food_preference_context",
                "negative_preference_context",
                "temporary_preference_context",
                "golden_order_context",
                "conversation_recall_context",
                "calibration_quality_context",
            ],
            "product_objects": [
                "meal_thread",
                "body_plan",
                "day_budget_ledger",
                "preference_memory",
            ],
            "memory_role": "Primary ranking and filtering context after review.",
            "runtime_effect_allowed": False,
        },
        {
            "family_id": "F7",
            "name": "Proactive Triggering",
            "context_domain_ids": [
                "proactive_suppression_context",
                "app_usage_style_context",
                "interaction_preference_context",
                "logging_adherence_context",
                "food_preference_context",
            ],
            "product_objects": ["proactive_trigger", "proposal"],
            "memory_role": "No-send timing, suppression, and candidate quality context only.",
            "runtime_effect_allowed": False,
        },
        {
            "family_id": "F8",
            "name": "Cross-Channel / Cross-Surface Experience",
            "context_domain_ids": [
                "cross_surface_context",
                "app_usage_style_context",
                "interaction_preference_context",
                "conversation_recall_context",
            ],
            "product_objects": ["meal_thread", "day_budget_ledger", "body_plan"],
            "memory_role": "Keep chat-first personalization coherent across surfaces.",
            "runtime_effect_allowed": False,
        },
    ]


def _consumer_contracts() -> list[dict[str, Any]]:
    return [
        {
            "consumer_id": "recommendation",
            "uses_context_domains": [
                "food_preference_context",
                "negative_preference_context",
                "temporary_preference_context",
                "golden_order_context",
                "calibration_quality_context",
            ],
            "allowed_use": "shadow ranking/filtering review",
            "forbidden_use": "serving recommendation or committing intake",
        },
        {
            "consumer_id": "intake_clarification",
            "uses_context_domains": [
                "user_language_semantic_alias_context",
                "intake_estimation_bias_context",
                "food_preference_context",
            ],
            "allowed_use": "shadow clarify-priority review",
            "forbidden_use": "rewriting nutrition evidence or FoodDB truth",
        },
        {
            "consumer_id": "chat_context",
            "uses_context_domains": [
                "interaction_preference_context",
                "app_usage_style_context",
                "conversation_recall_context",
            ],
            "allowed_use": "future response-context candidate review",
            "forbidden_use": "automatic prompt injection",
        },
        {
            "consumer_id": "calibration",
            "uses_context_domains": [
                "intake_estimation_bias_context",
                "logging_adherence_context",
                "calibration_quality_context",
            ],
            "allowed_use": "confidence and attribution review",
            "forbidden_use": "direct BodyPlan or DayBudgetLedger mutation",
        },
        {
            "consumer_id": "proactive",
            "uses_context_domains": [
                "proactive_suppression_context",
                "app_usage_style_context",
                "interaction_preference_context",
                "logging_adherence_context",
            ],
            "allowed_use": "no-send simulation",
            "forbidden_use": "scheduler activation or channel send",
        },
        {
            "consumer_id": "rescue_later",
            "uses_context_domains": [
                "rescue_history_context",
                "logging_adherence_context",
                "interaction_preference_context",
            ],
            "allowed_use": "future rescue viability review",
            "forbidden_use": "rescue proposal commit or budget overlay mutation",
        },
        {
            "consumer_id": "cross_surface_experience",
            "uses_context_domains": [
                "cross_surface_context",
                "app_usage_style_context",
                "conversation_recall_context",
            ],
            "allowed_use": "surface consistency review",
            "forbidden_use": "creating parallel UI/channel truth",
        },
    ]


def _candidate_type_to_context_domain() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for domain in _context_domain_catalog():
        for candidate_type in domain["candidate_types"]:
            mapping.setdefault(candidate_type, []).append(domain["context_domain_id"])
    return {key: sorted(value) for key, value in sorted(mapping.items())}


def _proactive_no_send_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    triggers = [
        {
            "trigger_id": f"trigger-{candidate.candidate_id}",
            "source_candidate_id": candidate.candidate_id,
            "trigger_type": _trigger_type(candidate),
            "reason": candidate.proposed_memory_text,
            "review_status": "pending",
            "human_review_required": True,
            "runtime_effect_allowed": False,
        }
        for candidate in candidates
        if candidate.candidate_type
        in {"pattern", "preference", "food_preference", "golden_order"}
    ]
    return _base_artifact(
        artifact_type="proactive_no_send_simulation",
        fixture=fixture,
        extra={
            "scheduler_activated": False,
            "channel_send_attempted": False,
            "would_inject_context": False,
            "injection_position": "not_applicable_shadow",
            "token_estimate": _token_estimate(
                " ".join(str(trigger.get("reason") or "") for trigger in triggers)
            ),
            "candidate_triggers": triggers,
        },
    )


def _recommendation_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    pool = _list_of_dicts(fixture.get("candidate_pool"))
    evaluations = [
        {
            "evaluation_id": f"recommendation-shadow-{item.get('candidate_id', index + 1)}",
            "candidate": item,
            "used_context_candidate_ids": [
                candidate.candidate_id
                for candidate in candidates
                if candidate.candidate_type
                in {"preference", "food_preference", "golden_order"}
            ],
            "review_only_rank_signal": index + 1,
            "review_status": "pending",
            "human_review_required": True,
            "runtime_effect_allowed": False,
        }
        for index, item in enumerate(pool or [{"candidate_id": "fixture-empty-pool"}])
    ]
    return _base_artifact(
        artifact_type="recommendation_shadow_eval",
        fixture=fixture,
        extra={
            "live_search_used": False,
            "intake_commit_requested": False,
            "candidate_evaluations": evaluations,
        },
    )


def _rescue_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    rescue_relevant = [
        candidate
        for candidate in candidates
        if any(
            "overshoot" in reason or "calibration" in reason
            for reason in candidate.reason_codes
        )
    ]
    packets = [
        {
            "packet_id": f"rescue-shadow-{candidate.candidate_id}",
            "source_candidate_id": candidate.candidate_id,
            "reason": candidate.proposed_memory_text,
            "review_status": "pending",
            "human_review_required": True,
            "runtime_effect_allowed": False,
        }
        for candidate in rescue_relevant
    ]
    return _base_artifact(
        artifact_type="rescue_shadow_candidates",
        fixture=fixture,
        extra={
            "budget_mutation_requested": False,
            "proposal_acceptance_side_effect": False,
            "candidate_packets": packets,
        },
    )


def _memory_review_action_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    actions = _list_of_dicts(fixture.get("review_actions"))
    candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    action_records: list[dict[str, Any]] = []
    candidate_results: list[dict[str, Any]] = []
    shadow_records: list[dict[str, Any]] = []
    missing_targets: list[dict[str, Any]] = []

    for action in actions:
        action_id = str(
            action.get("action_id") or f"review-action-{len(action_records) + 1}"
        )
        action_type = str(action.get("action_type") or "keep_shadowing")
        target_ids = [str(value) for value in action.get("target_candidate_ids") or []]
        action_records.append(
            {
                "action_id": action_id,
                "action_type": action_type,
                "target_candidate_ids": target_ids,
                "actor": str(action.get("actor") or "fixture_reviewer"),
                "rationale": str(action.get("rationale") or ""),
                "creates_runtime_effect": False,
                "durable_memory_write_allowed": False,
                "manager_context_injection_allowed": False,
            }
        )
        for candidate_id in target_ids:
            candidate = candidates_by_id.get(candidate_id)
            if candidate is None:
                missing_targets.append(
                    {"action_id": action_id, "candidate_id": candidate_id}
                )
                continue
            review_status_after = _review_status_for_action(action_type)
            candidate_results.append(
                {
                    "action_id": action_id,
                    "candidate_id": candidate_id,
                    "candidate_type": candidate.candidate_type,
                    "review_status_before": candidate.review_status,
                    "review_status_after": review_status_after,
                    "runtime_effect_allowed": False,
                    "durable_memory_write_allowed": False,
                    "manager_context_injection_allowed": False,
                }
            )
            if review_status_after == "accepted":
                shadow_records.append(_shadow_memory_record(candidate, action_id))

    return _base_artifact(
        artifact_type="memory_review_action_shadow_result",
        fixture=fixture,
        extra={
            "summary": {
                "action_count": len(action_records),
                "accepted_count": sum(
                    1
                    for result in candidate_results
                    if result["review_status_after"] == "accepted"
                ),
                "rejected_count": sum(
                    1
                    for result in candidate_results
                    if result["review_status_after"] == "rejected"
                ),
                "shadow_memory_record_count": len(shadow_records),
                "missing_target_count": len(missing_targets),
            },
            "action_records": action_records,
            "candidate_review_results": candidate_results,
            "shadow_memory_records": shadow_records,
            "missing_targets": missing_targets,
        },
    )


def _memory_promotion_demotion_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    action_status_by_candidate = _review_action_status_by_candidate(fixture)
    return _base_artifact(
        artifact_type="memory_promotion_demotion_shadow_eval",
        fixture=fixture,
        extra={
            "source_spec": "docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md",
            "promotion_attempted": False,
            "demotion_attempted": False,
            "durable_write_allowed": False,
            "promotion_review_items": [
                _promotion_review_item(candidate, action_status_by_candidate)
                for candidate in candidates
            ],
            "demotion_review_lanes": _demotion_review_lanes(),
        },
    )


def _review_action_status_by_candidate(fixture: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for action in _list_of_dicts(fixture.get("review_actions")):
        action_type = str(action.get("action_type") or "keep_shadowing")
        status = _review_status_for_action(action_type)
        for candidate_id in action.get("target_candidate_ids") or []:
            statuses[str(candidate_id)] = status
    return statuses


def _promotion_review_item(
    candidate: LongTermContextCandidate,
    action_status_by_candidate: dict[str, str],
) -> dict[str, Any]:
    review_action_status = action_status_by_candidate.get(
        candidate.candidate_id,
        candidate.review_status,
    )
    blockers = _promotion_blockers(candidate, review_action_status)
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "review_action_status": review_action_status,
        "human_review_required": True,
        "promotion_allowed_now": False,
        "durable_write_allowed": False,
        "runtime_context_load_allowed": False,
        "promotion_blockers": blockers,
        "temporal_validity_required": candidate.candidate_type
        == "temporary_preference",
        "source_trace_ids": candidate.source_trace_ids,
        "source_object_refs": candidate.source_object_refs,
        "confidence": candidate.confidence,
        "freshness_posture": candidate.freshness_posture,
        "candidate_summary": candidate.proposed_memory_text,
    }


def _promotion_blockers(
    candidate: LongTermContextCandidate,
    review_action_status: str,
) -> list[str]:
    blockers: list[str] = []
    if review_action_status != "accepted":
        blockers.append("human_confirmation_required")
    if candidate.candidate_type == "temporary_preference":
        blockers.append("expiry_policy_required")
    if candidate.candidate_type == "conversation_recall_context":
        blockers.append("summary_first_retrieval_contract_required")
    if candidate.candidate_type in {
        "intake_estimation_bias",
        "logging_adherence_pattern",
        "pattern",
    }:
        blockers.append("derived_pattern_not_confirmed_memory")
    return blockers


def _demotion_review_lanes() -> list[dict[str, Any]]:
    return [
        {
            "lane_id": "expired_temporary_preference",
            "trigger": "valid_until has passed",
            "human_review_required": True,
            "automatic_runtime_effect": False,
            "durable_memory_mutation_allowed": False,
        },
        {
            "lane_id": "stale_or_contradicted_pattern",
            "trigger": "freshness posture stale or contradictory source evidence appears",
            "human_review_required": True,
            "automatic_runtime_effect": False,
            "durable_memory_mutation_allowed": False,
        },
        {
            "lane_id": "user_correction_or_deletion",
            "trigger": "user corrects, deletes, or suppresses a remembered claim",
            "human_review_required": True,
            "automatic_runtime_effect": False,
            "durable_memory_mutation_allowed": False,
        },
    ]


def _semantic_pattern_extraction_shadow_artifact(
    fixture: dict[str, Any],
) -> dict[str, Any]:
    meals = _list_of_dicts(fixture.get("meal_logs"))
    committed_count = len(meals)
    extraction_allowed = committed_count >= 21
    return _base_artifact(
        artifact_type="semantic_pattern_extraction_shadow_plan",
        fixture=fixture,
        extra={
            "source_spec": "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
            "llm_extraction_called": False,
            "semantic_memory_written": False,
            "runtime_effect_allowed": False,
            "readiness_gate": {
                "required_new_committed_meal_items": 21,
                "required_days_since_last_extraction": 7,
                "fixture_committed_meal_items": committed_count,
                "extraction_allowed_now": extraction_allowed,
                "block_reason": None
                if extraction_allowed
                else "insufficient_committed_meal_items",
            },
            "planned_output_schema": {
                "pattern_type_values": [
                    "contextual_preference",
                    "temporal_preference",
                    "trend_shift",
                    "situational_avoidance",
                ],
                "required_fields": [
                    "pattern_type",
                    "description",
                    "evidence_window_days",
                    "evidence_meal_count",
                    "confidence",
                    "content_hash",
                    "extracted_at",
                ],
                "optional_fields": [
                    "time_condition",
                    "food_category",
                    "trend_direction",
                ],
            },
            "intended_consumers": [
                "recommendation",
                "nightly_insight",
                "confirmed_memory_candidate_review",
            ],
            "shadow_extraction_candidates": _semantic_shadow_candidates(meals),
        },
    )


def _semantic_shadow_candidates(meals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not meals:
        return []
    time_buckets = Counter(_time_bucket(meal.get("logged_at")) for meal in meals)
    bucket, count = _most_common(time_buckets)
    return [
        {
            "candidate_id": f"semantic-shadow-temporal-{_slug(bucket)}",
            "pattern_type": "temporal_preference",
            "description": f"Shadow-only temporal pattern pressure around {bucket} logging.",
            "evidence_meal_count": count,
            "confidence": _confidence(count, threshold=21),
            "llm_extraction_required_later": True,
            "durable_memory_write_allowed": False,
            "runtime_effect_allowed": False,
        }
    ]


def _conversation_recall_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    recall_candidates = [
        candidate
        for candidate in candidates
        if candidate.candidate_type == "conversation_recall_context"
    ]
    selected = [
        {
            "candidate_id": candidate.candidate_id,
            "candidate_type": candidate.candidate_type,
            "source_trace_ids": candidate.source_trace_ids,
            "source_object_refs": candidate.source_object_refs,
            "summary_preview": _conversation_summary_preview(candidate),
            "would_load_full_history": False,
            "manager_tool_call_allowed": False,
            "runtime_effect_allowed": False,
        }
        for candidate in recall_candidates
    ]
    return _base_artifact(
        artifact_type="conversation_recall_shadow_eval",
        fixture=fixture,
        extra={
            "summary_first": True,
            "raw_transcript_included": False,
            "retrieval_tool_called": False,
            "manager_tool_call_allowed": False,
            "selected_context_candidates": selected,
            "rejected_context_candidates": [],
            "omission_trace": {
                "raw_transcript_omitted": True,
                "full_history_dump_omitted": True,
                "runtime_packet_injection_omitted": True,
            },
        },
    )


def _conversation_recall_tool_shadow_plan_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    recall_candidates = [
        candidate
        for candidate in candidates
        if candidate.candidate_type == "conversation_recall_context"
    ]
    selected_refs = [
        {
            "candidate_id": candidate.candidate_id,
            "candidate_type": candidate.candidate_type,
            "source_trace_ids": candidate.source_trace_ids,
            "source_object_refs": candidate.source_object_refs,
            "summary_preview": _conversation_summary_preview(candidate),
            "freshness_posture": candidate.freshness_posture,
            "confidence": candidate.confidence,
            "raw_transcript_returned": False,
            "runtime_effect_allowed": False,
        }
        for candidate in recall_candidates
    ]
    return _base_artifact(
        artifact_type="conversation_recall_tool_shadow_plan",
        fixture=fixture,
        extra={
            "context_entry_mode": "future_tool_mediated_retrieval_candidate",
            "manager_tool_registered": False,
            "manager_tool_called": False,
            "runtime_tool_available": False,
            "retrieval_tool_call_allowed_now": False,
            "raw_transcript_access_allowed_now": False,
            "runtime_effect_allowed": False,
            "future_tool_contract": {
                "tool_name": "conversation_recall.search",
                "tool_owner": "future_manager_context_retrieval",
                "request_schema": {
                    "required": [
                        "user_id",
                        "retrieval_query",
                        "scope",
                        "reason_for_recall",
                    ],
                    "properties": {
                        "user_id": "stable scoped user identifier",
                        "retrieval_query": "natural-language recall need",
                        "scope": "project/session/surface boundary",
                        "reason_for_recall": "why current turn needs old context",
                        "time_window": "optional bounded date range",
                        "max_summaries": "optional cap; default future tool should stay small",
                        "raw_transcript_allowed": "must remain false by default",
                    },
                },
                "response_contract": {
                    "summary_first": True,
                    "structured_state_first": True,
                    "source_refs_required": True,
                    "freshness_required": True,
                    "omission_trace_required": True,
                    "raw_transcript_returned": False,
                    "manager_context_injection_allowed": False,
                },
            },
            "selected_conversation_refs": selected_refs,
            "safety_boundaries": [
                "ManagerContextPacket injection remains forbidden",
                "No raw transcript dump",
                "No durable memory write",
                "No runtime tool registration",
                "No provider or embedding call",
            ],
            "omission_trace": {
                "raw_transcript_omitted": True,
                "full_history_dump_omitted": True,
                "manager_tool_registration_omitted": True,
                "runtime_packet_injection_omitted": True,
            },
        },
    )


def _conversation_recall_retrieval_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    recall_candidates = [
        candidate
        for candidate in candidates
        if candidate.candidate_type == "conversation_recall_context"
    ]
    ranked = [
        {
            "rank": index + 1,
            "candidate_id": candidate.candidate_id,
            "candidate_type": candidate.candidate_type,
            "source_class": "conversation_history_summary",
            "retrieval_mode": "metadata_scope_filter",
            "scope_keys": candidate.scope_keys,
            "freshness_posture": candidate.freshness_posture,
            "source_trace_ids": candidate.source_trace_ids,
            "source_object_refs": candidate.source_object_refs,
            "summary_preview": _conversation_summary_preview(candidate),
            "raw_transcript_returned": False,
            "would_load_full_history": False,
            "runtime_effect_allowed": False,
        }
        for index, candidate in enumerate(
            sorted(
                recall_candidates,
                key=lambda item: (-item.confidence, item.candidate_id),
            )
        )
    ]
    return _base_artifact(
        artifact_type="conversation_recall_retrieval_shadow_eval",
        fixture=fixture,
        extra={
            "source_spec": "docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md",
            "summary_first": True,
            "retrieval_tool_registered": False,
            "retrieval_tool_called": False,
            "manager_tool_call_allowed": False,
            "live_vector_search_used": False,
            "raw_transcript_returned": False,
            "source_classes": [
                "conversation_history_summary",
                "memory_candidate_review_artifact",
            ],
            "routing_policy": {
                "deterministic_scope_filter_first": True,
                "metadata_filter_before_semantic_search": True,
                "full_document_read_fallback_allowed": False,
                "stale_result_requires_review": True,
            },
            "ranked_results": ranked,
            "negative_cases": [
                {
                    "case_id": "missing_user_scope",
                    "retrieval_allowed": False,
                    "reason": "scope_keys_required_before_recall",
                },
                {
                    "case_id": "raw_transcript_request",
                    "retrieval_allowed": False,
                    "reason": "summary_first_shadow_lab_forbids_raw_transcript",
                },
            ],
        },
    )


def _entity_normalization_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="entity_normalization_shadow_plan",
        fixture=fixture,
        extra={
            "entity_store_written": False,
            "fooddb_truth_changed": False,
            "canonical_objects_replaced": False,
            "entity_types": [
                "food_item",
                "store",
                "user_phrase",
                "preference_value",
                "conversation_topic",
            ],
            "normalization_review_lanes": [
                {
                    "lane_id": "alias_link_review",
                    "human_review_required": True,
                    "runtime_effect_allowed": False,
                },
                {
                    "lane_id": "canonical_truth_conflict_review",
                    "human_review_required": True,
                    "runtime_effect_allowed": False,
                },
                {
                    "lane_id": "entity_merge_split_review",
                    "human_review_required": True,
                    "runtime_effect_allowed": False,
                },
            ],
            "proposed_entities": _proposed_normalized_entities(candidates),
            "source_candidate_ids": [
                candidate.candidate_id for candidate in candidates
            ],
        },
    )


def _context_quality_contradiction_review_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    review_items = _contradiction_review_items(fixture, candidates)
    return _base_artifact(
        artifact_type="context_quality_contradiction_review_queue",
        fixture=fixture,
        extra={
            "runtime_blocking_claimed": False,
            "contradiction_count": sum(
                1 for item in review_items if item["contradiction_detected"]
            ),
            "quality_dimensions": [
                "evidence_strength",
                "freshness",
                "consumer_scope",
                "contradiction_risk",
                "promotion_readiness",
            ],
            "review_items": review_items,
        },
    )


def _capability_scenario_fixture_pack_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    available_types = {candidate.candidate_type for candidate in candidates}
    scenarios = [
        _capability_scenario(
            scenario_id="recommendation_with_preferences",
            consumer_id="recommendation",
            expected_artifact_ids=[
                "long_term_memory_candidate_review",
                "recommendation_shadow_eval",
                "long_term_context_pack_shadow_eval",
            ],
            candidate_types=["food_preference", "negative_preference", "golden_order"],
        ),
        _capability_scenario(
            scenario_id="intake_clarification_with_user_language",
            consumer_id="intake_clarification",
            expected_artifact_ids=[
                "long_term_memory_candidate_review",
                "context_value_review_queue",
            ],
            candidate_types=["user_language_pattern", "intake_estimation_bias"],
        ),
        _capability_scenario(
            scenario_id="chat_context_style_shadow",
            consumer_id="chat_context",
            expected_artifact_ids=[
                "long_term_context_pack_shadow_eval",
                "conversation_recall_shadow_eval",
            ],
            candidate_types=["app_usage_style", "interaction_preference"],
        ),
        _capability_scenario(
            scenario_id="calibration_bias_attribution_shadow",
            consumer_id="calibration",
            expected_artifact_ids=[
                "context_quality_contradiction_review_queue",
                "long_term_context_pack_shadow_eval",
            ],
            candidate_types=["intake_estimation_bias", "logging_adherence_pattern"],
        ),
        _capability_scenario(
            scenario_id="proactive_no_send_timing_shadow",
            consumer_id="proactive",
            expected_artifact_ids=[
                "proactive_no_send_simulation",
                "long_term_context_pack_shadow_eval",
            ],
            candidate_types=["app_usage_style", "logging_adherence_pattern"],
        ),
        _capability_scenario(
            scenario_id="rescue_later_viability_shadow",
            consumer_id="rescue_later",
            expected_artifact_ids=[
                "rescue_shadow_candidates",
                "long_term_context_pack_shadow_eval",
            ],
            candidate_types=["logging_adherence_pattern", "intake_estimation_bias"],
        ),
        _capability_scenario(
            scenario_id="conversation_recall_tool_shadow",
            consumer_id="conversation_recall",
            expected_artifact_ids=[
                "conversation_recall_tool_shadow_plan",
                "conversation_recall_retrieval_shadow_eval",
            ],
            candidate_types=["conversation_recall_context"],
        ),
    ]
    return _base_artifact(
        artifact_type="capability_scenario_fixture_pack",
        fixture=fixture,
        extra={
            "fixture_only": True,
            "runtime_scenarios_executed": False,
            "scenario_count": len(scenarios),
            "available_candidate_types": sorted(available_types),
            "scenarios": scenarios,
        },
    )


def _pr_review_autopilot_closeout_artifact(fixture: dict[str, Any]) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="pr_review_autopilot_closeout",
        fixture=fixture,
        extra={
            "draft_pr_only": True,
            "auto_merge_allowed": False,
            "human_approval_required_for_merge": True,
            "continue_without_gate_after_batch2": False,
            "review_loop_allowed_actions": [
                "push_offline_shadow_fixes",
                "update_draft_pr_body",
                "inspect_ci",
                "inspect_review_comments",
            ],
            "review_loop_forbidden_actions": [
                "merge_main",
                "mark_ready_for_review",
                "register_runtime_tool",
                "add_startup_or_scheduler_hook",
                "write_durable_memory",
            ],
        },
    )


def _long_term_context_pack_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    packs = {
        "recommendation": _context_pack(
            pack_id="recommendation",
            candidates=candidates,
            allowed_consumers={"recommendation", "recommendation_presentation"},
            allowed_candidate_types={
                "food_preference",
                "golden_order",
                "negative_preference",
                "temporary_preference",
                "user_language_pattern",
                "conversation_recall_context",
            },
        ),
        "intake_chat_context": _context_pack(
            pack_id="intake_chat_context",
            candidates=candidates,
            allowed_consumers={
                "chat_context",
                "intake_clarification",
                "response_context",
                "response_generation",
                "nutrition_clarify_priority",
            },
            allowed_candidate_types={
                "app_usage_style",
                "conversation_recall_context",
                "food_preference",
                "golden_order",
                "intake_estimation_bias",
                "interaction_preference",
                "negative_preference",
                "pattern",
                "temporary_preference",
                "user_language_pattern",
            },
        ),
        "calibration_context": _context_pack(
            pack_id="calibration_context",
            candidates=candidates,
            allowed_consumers={
                "calibration",
                "intake_risk_tagging",
                "nutrition_clarify_priority",
            },
            allowed_candidate_types={
                "conversation_recall_context",
                "intake_estimation_bias",
                "logging_adherence_pattern",
                "pattern",
            },
        ),
        "proactive_context": _context_pack(
            pack_id="proactive_context",
            candidates=candidates,
            allowed_consumers={
                "proactive",
                "proactive_message_style",
                "recommendation",
                "rescue_later",
            },
            allowed_candidate_types={
                "app_usage_style",
                "food_preference",
                "golden_order",
                "interaction_preference",
                "logging_adherence_pattern",
                "negative_preference",
                "pattern",
                "temporary_preference",
            },
        ),
        "rescue_context": _context_pack(
            pack_id="rescue_context",
            candidates=candidates,
            allowed_consumers={"rescue_later", "calibration", "proactive"},
            allowed_candidate_types={
                "intake_estimation_bias",
                "interaction_preference",
                "logging_adherence_pattern",
                "pattern",
            },
        ),
        "cross_surface_context": _context_pack(
            pack_id="cross_surface_context",
            candidates=candidates,
            allowed_consumers={
                "chat_context",
                "intake_clarification",
                "proactive",
                "response_generation",
                "ux",
            },
            allowed_candidate_types={
                "app_usage_style",
                "conversation_recall_context",
                "interaction_preference",
                "user_language_pattern",
            },
        ),
    }
    return _base_artifact(
        artifact_type="long_term_context_pack_shadow_eval",
        fixture=fixture,
        extra={
            "runtime_context_loaded": False,
            "manager_context_packet_written": False,
            "manager_context_packet_injection_allowed": False,
            "summary_first": True,
            "structured_state_first": True,
            "context_packs": packs,
        },
    )


def _context_pack(
    *,
    pack_id: str,
    candidates: list[LongTermContextCandidate],
    allowed_consumers: set[str],
    allowed_candidate_types: set[str],
) -> dict[str, Any]:
    selected = [
        candidate
        for candidate in candidates
        if candidate.candidate_type in allowed_candidate_types
        and allowed_consumers.intersection(candidate.intended_consumers)
    ]
    selected.sort(
        key=lambda candidate: (
            _context_pack_rank(pack_id, candidate),
            -candidate.confidence,
            candidate.candidate_id,
        )
    )
    selected_text = " ".join(
        str(candidate.proposed_memory_text or "") for candidate in selected
    )
    return {
        "pack_id": pack_id,
        "summary_first": True,
        "structured_state_first": True,
        "raw_full_history_dumped": False,
        "runtime_effect_allowed": False,
        "manager_context_injection_allowed": False,
        "selected_candidate_ids": [candidate.candidate_id for candidate in selected],
        "selected_candidate_summaries": [
            _context_candidate_summary(candidate) for candidate in selected
        ],
        "token_estimate": _token_estimate(selected_text),
        "omission_trace": {
            "raw_transcript_omitted": True,
            "full_history_dump_omitted": True,
            "unselected_candidates_omitted": max(
                0,
                len(candidates) - len(selected),
            ),
        },
    }


def _context_pack_rank(
    pack_id: str,
    candidate: LongTermContextCandidate,
) -> int:
    ranking = {
        "recommendation": {
            "golden_order": 0,
            "food_preference": 1,
            "negative_preference": 2,
            "temporary_preference": 3,
            "user_language_pattern": 4,
            "conversation_recall_context": 5,
        },
        "intake_chat_context": {
            "user_language_pattern": 0,
            "interaction_preference": 1,
            "app_usage_style": 2,
            "intake_estimation_bias": 3,
            "negative_preference": 4,
            "temporary_preference": 5,
            "conversation_recall_context": 6,
            "golden_order": 7,
            "food_preference": 8,
            "pattern": 9,
        },
        "calibration_context": {
            "intake_estimation_bias": 0,
            "logging_adherence_pattern": 1,
            "pattern": 2,
            "conversation_recall_context": 3,
        },
        "proactive_context": {
            "app_usage_style": 0,
            "interaction_preference": 1,
            "logging_adherence_pattern": 2,
            "negative_preference": 3,
            "temporary_preference": 4,
            "food_preference": 5,
            "golden_order": 6,
            "pattern": 7,
        },
        "rescue_context": {
            "logging_adherence_pattern": 0,
            "intake_estimation_bias": 1,
            "pattern": 2,
            "interaction_preference": 3,
        },
        "cross_surface_context": {
            "app_usage_style": 0,
            "interaction_preference": 1,
            "conversation_recall_context": 2,
            "user_language_pattern": 3,
        },
    }
    return ranking.get(pack_id, {}).get(candidate.candidate_type, 99)


def _proposed_normalized_entities(
    candidates: list[LongTermContextCandidate],
) -> list[dict[str, Any]]:
    entities: dict[str, dict[str, Any]] = {}

    def add_entity(
        *,
        entity_type: str,
        label: str,
        source_candidate_id: str,
    ) -> None:
        if not label:
            return
        entity_id = f"{entity_type}-{_slug(label)}"
        entity = entities.setdefault(
            entity_id,
            {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "label": label,
                "source_candidate_ids": [],
                "canonical_truth_write_allowed": False,
                "runtime_effect_allowed": False,
            },
        )
        entity["source_candidate_ids"] = _dedupe(
            [*entity["source_candidate_ids"], source_candidate_id]
        )

    for candidate in candidates:
        payload = candidate.payload
        if candidate.candidate_type == "golden_order":
            add_entity(
                entity_type="store",
                label=str(payload.get("store_name") or ""),
                source_candidate_id=candidate.candidate_id,
            )
            for item in payload.get("item_names") or []:
                add_entity(
                    entity_type="food",
                    label=str(item),
                    source_candidate_id=candidate.candidate_id,
                )
        elif candidate.candidate_type == "food_preference":
            add_entity(
                entity_type="food",
                label=str(payload.get("value") or ""),
                source_candidate_id=candidate.candidate_id,
            )
        elif candidate.candidate_type in {
            "negative_preference",
            "temporary_preference",
        }:
            add_entity(
                entity_type="preference-value",
                label=str(payload.get("value") or ""),
                source_candidate_id=candidate.candidate_id,
            )
        elif candidate.candidate_type == "user_language_pattern":
            add_entity(
                entity_type="user-phrase",
                label=str(payload.get("user_phrase") or ""),
                source_candidate_id=candidate.candidate_id,
            )
        elif candidate.candidate_type == "conversation_recall_context":
            summaries = payload.get("conversation_summaries")
            if isinstance(summaries, list):
                for summary in summaries:
                    if not isinstance(summary, dict):
                        continue
                    for tag in summary.get("topic_tags") or []:
                        add_entity(
                            entity_type="conversation-topic",
                            label=str(tag),
                            source_candidate_id=candidate.candidate_id,
                        )

    return sorted(entities.values(), key=lambda item: item["entity_id"])


def _contradiction_review_items(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> list[dict[str, Any]]:
    pool_names = [
        str(item.get("name") or "").lower()
        for item in _list_of_dicts(fixture.get("candidate_pool"))
    ]
    negative_candidates = [
        candidate
        for candidate in candidates
        if candidate.candidate_type == "negative_preference"
    ]
    conflicting_negative_ids: list[str] = []
    for candidate in negative_candidates:
        value = str(candidate.payload.get("value") or "").lower()
        if value and any(value in name for name in pool_names):
            conflicting_negative_ids.append(candidate.candidate_id)

    items = [
        {
            "check_id": "negative_preference_vs_candidate_pool",
            "candidate_ids": conflicting_negative_ids,
            "contradiction_detected": bool(conflicting_negative_ids),
            "review_status": "pending",
            "recommended_action": "keep_shadowing",
            "risk_if_wrong": (
                "Could recommend or suppress a food based on conflicting preference evidence."
            ),
            "runtime_effect_allowed": False,
        },
        {
            "check_id": "temporary_preference_expiry_review",
            "candidate_ids": [
                candidate.candidate_id
                for candidate in candidates
                if candidate.candidate_type == "temporary_preference"
            ],
            "contradiction_detected": False,
            "review_status": "pending",
            "recommended_action": "verify_expiry_before_future_promotion",
            "risk_if_wrong": "Could keep expired temporary context active too long.",
            "runtime_effect_allowed": False,
        },
    ]
    return items


def _capability_scenario(
    *,
    scenario_id: str,
    consumer_id: str,
    expected_artifact_ids: list[str],
    candidate_types: list[str],
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "consumer_id": consumer_id,
        "candidate_types": candidate_types,
        "expected_artifact_ids": expected_artifact_ids,
        "runtime_effect_allowed": False,
        "forbidden_runtime_effects": [
            "manager_context_injection",
            "durable_memory_write",
            "db_mutation",
            "live_provider_call",
            "proactive_send",
            "recommendation_served",
            "rescue_commit",
        ],
        "acceptance_focus": "review_artifact_shape_only",
    }


def _context_candidate_summary(
    candidate: LongTermContextCandidate,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "proposed_memory_text": candidate.proposed_memory_text,
        "confidence": candidate.confidence,
        "freshness_posture": candidate.freshness_posture,
        "source_trace_ids": candidate.source_trace_ids,
        "source_object_refs": candidate.source_object_refs,
        "intended_consumers": candidate.intended_consumers,
        "consumer_use_hints": candidate.consumer_use_hints,
        "risk_if_wrong": candidate.risk_if_wrong,
        "promotion_path": candidate.promotion_path,
        "why_this_is_not_runtime_truth": candidate.why_this_is_not_runtime_truth,
        "runtime_effect_allowed": False,
    }


def _review_status_for_action(action_type: str) -> str:
    if action_type == "accept_candidate":
        return "accepted"
    if action_type == "reject_candidate":
        return "rejected"
    if action_type == "expire_candidate":
        return "expired"
    return "pending"


def _shadow_memory_record(
    candidate: LongTermContextCandidate,
    action_id: str,
) -> dict[str, Any]:
    return {
        "memory_record_id": f"shadow-memory-record-{candidate.candidate_id}",
        "source_candidate_id": candidate.candidate_id,
        "source_action_id": action_id,
        "record_state": "accepted_shadow",
        "memory_text": candidate.proposed_memory_text,
        "candidate_type": candidate.candidate_type,
        "scope_keys": candidate.scope_keys,
        "intended_consumers": candidate.intended_consumers,
        "can_be_runtime_loaded": False,
        "durable_memory_written": False,
        "runtime_effect_allowed": False,
        "provenance": {
            "source_trace_ids": candidate.source_trace_ids,
            "source_object_refs": candidate.source_object_refs,
            "evidence_count": candidate.evidence_count,
        },
    }


def _conversation_summary_preview(candidate: LongTermContextCandidate) -> str:
    summaries = candidate.payload.get("conversation_summaries")
    if isinstance(summaries, list) and summaries and isinstance(summaries[0], dict):
        return str(summaries[0].get("summary") or "")[:280]
    return str(candidate.proposed_memory_text or "")[:280]


def _trigger_type(candidate: LongTermContextCandidate) -> str:
    reason = " ".join(candidate.reason_codes)
    if "overshoot" in reason:
        return "overshoot_risk"
    if "weight" in reason:
        return "weight_logging_consistency"
    if candidate.candidate_type == "golden_order":
        return "weekly_insight_candidate"
    return "high_risk_time_window"


def _default_consumers(candidate_type: str) -> list[str]:
    if candidate_type == "golden_order":
        return ["recommendation", "intake_clarification", "chat_context"]
    if candidate_type == "food_preference":
        return ["recommendation", "proactive", "intake_clarification"]
    if candidate_type == "negative_preference":
        return ["recommendation", "proactive", "intake_clarification"]
    if candidate_type == "temporary_preference":
        return [
            "recommendation",
            "chat_context",
            "proactive",
            "intake_clarification",
        ]
    if candidate_type == "logging_adherence_pattern":
        return ["calibration", "proactive", "rescue_later"]
    if candidate_type == "intake_estimation_bias":
        return [
            "calibration",
            "intake_risk_tagging",
            "nutrition_clarify_priority",
            "response_context",
        ]
    if candidate_type == "user_language_pattern":
        return ["intake_clarification", "chat_context", "recommendation"]
    if candidate_type == "app_usage_style":
        return ["chat_context", "proactive", "ux", "recommendation_presentation"]
    if candidate_type == "interaction_preference":
        return ["response_generation", "chat_context", "proactive_message_style"]
    if candidate_type == "conversation_recall_context":
        return ["chat_context", "intake_clarification", "recommendation", "calibration"]
    return ["recommendation", "proactive"]


def _consumer_use_hints(consumers: list[str]) -> dict[str, str]:
    hints: dict[str, str] = {}
    for consumer in consumers:
        if consumer == "calibration":
            hints[consumer] = (
                "Use only as confidence or attribution context; never rewrite calibration truth."
            )
        elif consumer in {"intake_clarification", "nutrition_clarify_priority"}:
            hints[consumer] = (
                "Use to prioritize clarification in shadow review, not to default food truth."
            )
        elif consumer in {"chat_context", "response_generation", "response_context"}:
            hints[consumer] = (
                "Use as future response-context candidate only after human review."
            )
        elif consumer.startswith("proactive"):
            hints[consumer] = (
                "Use only for no-send simulation until proactive activation is approved."
            )
        elif consumer == "rescue_later":
            hints[consumer] = (
                "Secondary rescue input only; no rescue proposal or budget mutation."
            )
        else:
            hints[consumer] = "Use as review-only context value signal."
    return hints


def _risk_if_wrong(candidate_type: str) -> str:
    if candidate_type == "intake_estimation_bias":
        return "Could misattribute calibration mismatch to user behavior and change clarification priority too early."
    if candidate_type == "user_language_pattern":
        return "Could misunderstand the user's phrasing and bias intake clarification."
    if candidate_type == "app_usage_style":
        return "Could personalize chat or reminders in a way the user did not actually prefer."
    if candidate_type == "interaction_preference":
        return "Could alter response style before the preference is confirmed."
    if candidate_type in {"food_preference", "golden_order"}:
        return (
            "Could overfit recommendations or intake defaults to a weak food pattern."
        )
    if candidate_type == "negative_preference":
        return "Could suppress acceptable foods or recommendations before a dislike is confirmed."
    if candidate_type == "temporary_preference":
        return "Could keep a short-term preference active after it should expire."
    if candidate_type == "logging_adherence_pattern":
        return "Could overstate adherence or logging quality and distort calibration confidence."
    if candidate_type == "conversation_recall_context":
        return "Could retrieve stale or irrelevant conversation history and pollute current-turn context."
    return "Could inject unconfirmed context into future runtime behavior."


def _promotion_path(candidate_type: str) -> str:
    if candidate_type == "temporary_preference":
        return "human_review_then_time_bounded_l3_confirmed_memory_later"
    if candidate_type in {
        "golden_order",
        "food_preference",
        "negative_preference",
        "user_language_pattern",
        "intake_estimation_bias",
        "app_usage_style",
        "interaction_preference",
    }:
        return "human_review_then_l3_confirmed_memory_later"
    if candidate_type == "conversation_recall_context":
        return "future_tool_mediated_recall_contract_review_only"
    return "keep_shadowing_until_consumer_value_review"


def _candidate_non_runtime_truth_reason(candidate_type: str) -> str:
    if candidate_type == "golden_order":
        return (
            "Golden orders are materialized review views over MealThread history; "
            "they do not replace canonical MealThread or FoodDB truth."
        )
    if candidate_type == "intake_estimation_bias":
        return (
            "Bias posture is calibration context only; it cannot rewrite calorie, "
            "BodyPlan, or DayBudgetLedger truth."
        )
    if candidate_type == "conversation_recall_context":
        return (
            "Conversation recall remains summary-first future retrieval context; "
            "no transcript is injected into ManagerContextPacket."
        )
    return (
        "This is an offline shadow candidate derived from fixture/export evidence "
        "for human review; runtime truth and mutation authority stay unchanged."
    )


def _artifact_risk_if_wrong(artifact_type: str) -> str:
    if artifact_type == "artifact_registry_manifest":
        return "Could hide an unowned or pseudo-runtime artifact from reviewer triage."
    if "recommendation" in artifact_type:
        return "Could overstate recommendation readiness or ranking value before runtime review."
    if "proactive" in artifact_type:
        return "Could make no-send trigger candidates look like approved sends."
    if "rescue" in artifact_type:
        return "Could imply rescue viability or budget mutation authority too early."
    if "context_pack" in artifact_type:
        return "Could make shadow context packs look ready for ManagerContextPacket injection."
    if "framework" in artifact_type:
        return "Could over-adopt external framework patterns over canonical L4A/L4C/L4D specs."
    return "Could overstate unconfirmed long-term context as product or runtime truth."


def _artifact_promotion_path(artifact_type: str) -> str:
    if artifact_type == "artifact_registry_manifest":
        return "review_manifest_then_keep_or_defer_each_artifact"
    if "context_pack" in artifact_type:
        return "human_review_then_future_context_pack_contract_slice"
    if "recommendation" in artifact_type:
        return "human_review_then_future_recommendation_shadow_eval_slice"
    if "proactive" in artifact_type:
        return "human_review_then_future_no_send_scheduler_eval_slice"
    if "rescue" in artifact_type:
        return "human_review_then_future_rescue_shadow_eval_slice"
    if "framework" in artifact_type:
        return "research_review_only_no_runtime_adoption"
    return "human_review_then_keep_shadowing_or_defer"


def _artifact_non_runtime_truth_reason(artifact_type: str) -> str:
    return (
        f"{artifact_type} is generated by the offline shadow lab for review only; "
        "it cannot write durable memory, mutate canonical product objects, or inject "
        "ManagerContextPacket context."
    )


def _trace_refs(fixture: dict[str, Any]) -> dict[str, str]:
    refs: dict[str, str] = {}
    for item in _list_of_dicts(fixture.get("trace_metadata")):
        trace_id = item.get("trace_id")
        source_ref = item.get("source_object_ref")
        if trace_id and source_ref:
            refs[str(trace_id)] = str(source_ref)
    return refs


def _source_refs_for_meals(
    meals: list[dict[str, Any]], trace_refs: dict[str, str]
) -> list[str]:
    return [
        _source_ref(
            meal, trace_refs, fallback_kind="MealThread", fallback_id_key="meal_id"
        )
        for meal in meals
    ]


def _source_refs_matching(
    meals: list[dict[str, Any]],
    trace_refs: dict[str, str],
    key: str,
    value: str,
) -> list[str]:
    return _source_refs_for_meals(
        [
            meal
            for meal in meals
            if value in [str(item) for item in meal.get(key) or []]
        ],
        trace_refs,
    )


def _trace_ids_matching(meals: list[dict[str, Any]], key: str, value: str) -> list[str]:
    return [
        _trace_id(meal)
        for meal in meals
        if value in [str(item) for item in meal.get(key) or []]
    ]


def _source_ref(
    item: dict[str, Any],
    trace_refs: dict[str, str],
    *,
    fallback_kind: str,
    fallback_id_key: str,
) -> str:
    trace_id = _trace_id(item)
    if trace_id in trace_refs:
        return trace_refs[trace_id]
    fallback_id = str(item.get(fallback_id_key) or trace_id)
    return f"{fallback_kind}:{fallback_id}"


def _trace_id(item: dict[str, Any]) -> str:
    return str(item.get("trace_id") or item.get("id") or "fixture-trace")


def _time_bucket(value: Any) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        return "unknown"
    hour = parsed.hour
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 15:
        return "midday"
    if 15 <= hour < 20:
        return "evening"
    return "late"


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_date_as_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    parsed = _parse_datetime(value)
    if parsed:
        return parsed
    try:
        return datetime.fromisoformat(str(value) + "T00:00:00+00:00")
    except ValueError:
        return None


def _most_common(counter: Counter[str]) -> tuple[str, int]:
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0]


def _confidence(count: int, *, threshold: int) -> float:
    if threshold <= 0:
        return 0.0
    return min(1.0, round(count / threshold, 2))


def _bounded_confidence(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0.0, min(1.0, round(parsed, 2)))


def _float_value(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _token_estimate(text: str) -> int:
    return max(0, len(text) // 4)


def _redact_secret_values(value: Any) -> tuple[Any, list[str]]:
    redacted_fields: list[str] = []

    def redact(current: Any, path: str) -> Any:
        if isinstance(current, dict):
            result: dict[str, Any] = {}
            for key, item in current.items():
                key_text = str(key)
                child_path = f"{path}.{key_text}" if path else key_text
                if _is_secret_key(key_text):
                    result[key_text] = "[REDACTED]"
                    redacted_fields.append(child_path)
                else:
                    result[key_text] = redact(item, child_path)
            return result
        if isinstance(current, list):
            return [
                redact(item, f"{path}[{index}]") for index, item in enumerate(current)
            ]
        return current

    return redact(value, ""), redacted_fields


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(
        token in lowered
        for token in (
            "api_key",
            "apikey",
            "token",
            "secret",
            "password",
            "credential",
            "authorization",
        )
    )


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _slug(value: str) -> str:
    return "-".join(
        "".join(char.lower() if char.isalnum() else "-" for char in value).split("-")
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _model_dict(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json")


def _json_safe(value: Any) -> dict[str, Any]:
    payload = json.loads(json.dumps(value, ensure_ascii=False, default=str))
    if not isinstance(payload, dict):
        raise ValueError("Shadow lab artifact must be a JSON object")
    return payload


__all__ = [
    "SHADOW_NON_CLAIM_FLAGS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "artifact_review_contract",
    "build_artifact_registry_manifest",
    "build_shadow_lab_artifacts",
]
