from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from app.memory.domain.long_term_context_candidates import (
    ContextValueReviewItem,
    LongTermContextCandidate,
)
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


def build_shadow_lab_artifacts(
    fixture_payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    fixture = dict(fixture_payload or {})
    candidates = _build_candidates(fixture)
    context_items = _build_context_value_items(candidates)

    return {
        "long_term_memory_candidate_review": _memory_candidate_review_artifact(
            fixture,
            candidates,
        ),
        "context_value_review_queue": _context_value_review_queue_artifact(
            fixture,
            context_items,
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
        "long_term_context_pack_shadow_eval": _long_term_context_pack_shadow_artifact(
            fixture,
            candidates,
        ),
        "product_capability_context_map": _product_capability_context_map_artifact(
            fixture,
            candidates,
        ),
    }


def _base_artifact(
    *,
    artifact_type: str,
    fixture: dict[str, Any],
    extra: dict[str, Any],
) -> dict[str, Any]:
    generated_at = str(fixture.get("generated_at_utc") or "1970-01-01T00:00:00+00:00")
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
        **SHADOW_NON_CLAIM_FLAGS,
        **extra,
    }
    return _json_safe(payload)


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
    "build_shadow_lab_artifacts",
]
