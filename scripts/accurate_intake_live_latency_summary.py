from __future__ import annotations

from typing import Any


HIGH_PROVIDER_INVOCATION_COUNT = 8
HIGH_STAGE_LATENCY_MS = 60_000
HIGH_STAGE_OVERHEAD_MS = 10_000
HIGH_TURN_NON_PROVIDER_LATENCY_MS = 3_000
HIGH_TOTAL_PROMPT_TOKENS = 50_000
HIGH_SINGLE_PROMPT_TOKENS = 8_000
PRODUCT_LATENCY_TARGETS_MS = {
    "diagnostic_probe": {"target_p50_ms": 3_000, "target_p95_ms": 8_000, "hard_timeout_ms": 20_000},
    "read_only_or_entry": {"target_p50_ms": 3_000, "target_p95_ms": 8_000, "hard_timeout_ms": 20_000},
    "body_observation": {"target_p50_ms": 3_000, "target_p95_ms": 8_000, "hard_timeout_ms": 20_000},
    "intake_no_web": {"target_p50_ms": 6_000, "target_p95_ms": 12_000, "hard_timeout_ms": 20_000},
    "intake_clarify_or_correction": {
        "target_p50_ms": 8_000,
        "target_p95_ms": 15_000,
        "hard_timeout_ms": 20_000,
    },
    "fooddb_or_web_evidence": {"target_p50_ms": 10_000, "target_p95_ms": 20_000, "hard_timeout_ms": 30_000},
}
STAGE_OVERHEAD_TARGET_MS = 1_000
STAGE_OVERHEAD_WARN_MS = 3_000
STAGE_OVERHEAD_HARD_MS = 10_000


def build_latency_breakdown(
    *,
    stage_latency_records: list[dict[str, Any]],
    provider_invocation_records: list[dict[str, Any]],
    turn_latency_records: list[dict[str, Any]],
) -> dict[str, Any]:
    total_stage_latency_ms = sum(int(record.get("stage_latency_ms") or 0) for record in stage_latency_records)
    total_provider_latency_ms = sum(int(record.get("latency_ms") or 0) for record in provider_invocation_records)
    total_turn_latency_ms = sum(int(record.get("turn_latency_ms") or 0) for record in turn_latency_records)
    total_turn_non_provider_ms = sum(int(record.get("non_provider_latency_ms") or 0) for record in turn_latency_records)
    return {
        "stage_latency_ms": total_stage_latency_ms,
        "provider_invocation_latency_ms": total_provider_latency_ms,
        "stage_overhead_ms": max(0, total_stage_latency_ms - total_provider_latency_ms),
        "turn_latency_ms": total_turn_latency_ms,
        "turn_non_provider_latency_ms": total_turn_non_provider_ms,
        "max_turn_non_provider_latency_ms": max(
            (int(record.get("non_provider_latency_ms") or 0) for record in turn_latency_records),
            default=0,
        ),
        "unattributed_provider_invocation_count": sum(
            1
            for record in provider_invocation_records
            if not record.get("diagnostic_stage_id") and not record.get("stage")
        ),
        "by_diagnostic_stage": _diagnostic_stage_latency_breakdown(
            stage_latency_records=stage_latency_records,
            provider_invocation_records=provider_invocation_records,
            total_provider_latency_ms=total_provider_latency_ms,
        ),
        "by_case": _group_provider_latency(
            provider_invocation_records,
            keys=("source_index", "diagnostic_stage_id", "diagnostic_case_id"),
            labels={"diagnostic_case_id": "diagnostic_probe"},
            total_provider_latency_ms=total_provider_latency_ms,
        ),
        "by_turn": _group_provider_latency(
            [record for record in provider_invocation_records if record.get("diagnostic_case_id")],
            keys=(
                "source_index",
                "diagnostic_stage_id",
                "diagnostic_case_id",
                "diagnostic_turn",
                "diagnostic_turn_kind",
            ),
            total_provider_latency_ms=total_provider_latency_ms,
        ),
        "by_manager_loop_scope": _group_provider_latency(
            provider_invocation_records,
            keys=("source_index", "diagnostic_stage_id", "manager_loop_scope"),
            labels={"manager_loop_scope": "unknown_manager_scope"},
            total_provider_latency_ms=total_provider_latency_ms,
        ),
        "by_case_turn_runtime": _case_turn_runtime_breakdown(
            turn_latency_records,
            total_turn_latency_ms=total_turn_latency_ms,
        ),
        "slowest_provider_invocations": _slowest_provider_invocations(provider_invocation_records),
        "slowest_turn_runtime_segments": _slowest_turn_runtime_segments(turn_latency_records),
    }


def build_latency_slo(
    *,
    latency_breakdown: dict[str, Any],
    provider_invocation_records: list[dict[str, Any]],
) -> dict[str, Any]:
    provider_turn_rows = [
        _latency_slo_row(
            row,
            observed_latency_ms=int(row.get("provider_invocation_latency_ms") or 0),
            latency_class=_latency_class_for_turn(row),
            observed_latency_field="provider_invocation_latency_ms",
        )
        for row in _list(latency_breakdown.get("by_turn"))
    ]
    manager_scope_rows = [
        _latency_slo_row(
            row,
            observed_latency_ms=int(row.get("provider_invocation_latency_ms") or 0),
            latency_class=_latency_class_for_manager_scope(row.get("manager_loop_scope")),
            observed_latency_field="provider_invocation_latency_ms",
        )
        for row in _list(latency_breakdown.get("by_manager_loop_scope"))
    ]
    stage_overhead_rows = [
        _stage_overhead_slo_row(row)
        for row in _list(latency_breakdown.get("by_diagnostic_stage"))
        if int(row.get("stage_overhead_ms") or 0) > 0
    ]
    budget_rows = provider_turn_rows or manager_scope_rows
    return {
        "claim_scope": "diagnostic_latency_slo",
        "diagnostic_only_not_readiness": True,
        "single_sample_policy": (
            "Compare individual observed rows with Current Shell v1 latency targets; "
            "do not claim p50 or p95 distribution compliance from a single diagnostic sample."
        ),
        "targets_ms": PRODUCT_LATENCY_TARGETS_MS,
        "stage_overhead_budget_ms": {
            "target_ms": STAGE_OVERHEAD_TARGET_MS,
            "warn_ms": STAGE_OVERHEAD_WARN_MS,
            "hard_ms": STAGE_OVERHEAD_HARD_MS,
        },
        "provider_turn_budget": {
            "row_source": "latency_breakdown.by_turn",
            "rows": provider_turn_rows,
            "status_counts": _status_counts(provider_turn_rows),
        },
        "manager_scope_budget": {
            "row_source": "latency_breakdown.by_manager_loop_scope",
            "debug_attribution_only": True,
            "rows": manager_scope_rows,
            "status_counts": _status_counts(manager_scope_rows),
        },
        "stage_overhead_budget": {
            "row_source": "latency_breakdown.by_diagnostic_stage",
            "debug_attribution_only": True,
            "rows": stage_overhead_rows,
            "status_counts": _status_counts(stage_overhead_rows),
        },
        "summary": _latency_slo_summary(
            budget_rows=budget_rows,
            stage_overhead_rows=stage_overhead_rows,
            provider_invocation_records=provider_invocation_records,
        ),
    }


def build_latency_root_cause_hints(
    *,
    provider_invocation_count: int,
    max_stage_latency_ms: int,
    stage_overhead_ms: int,
    max_turn_non_provider_latency_ms: int,
    prompt_tokens: int,
    completion_tokens: int,
    max_prompt_tokens_per_usage_record: int,
    usage_record_count: int,
    cache_reporting_call_count: int,
    cache_hit_call_count: int,
) -> dict[str, bool]:
    return {
        "provider_invocation_count_high": provider_invocation_count >= HIGH_PROVIDER_INVOCATION_COUNT,
        "stage_latency_high": max_stage_latency_ms >= HIGH_STAGE_LATENCY_MS,
        "stage_overhead_high": stage_overhead_ms >= HIGH_STAGE_OVERHEAD_MS,
        "turn_non_provider_runtime_high": max_turn_non_provider_latency_ms >= HIGH_TURN_NON_PROVIDER_LATENCY_MS,
        "prompt_token_volume_high": (
            prompt_tokens >= HIGH_TOTAL_PROMPT_TOKENS
            or max_prompt_tokens_per_usage_record >= HIGH_SINGLE_PROMPT_TOKENS
        ),
        "prompt_cache_metrics_missing": usage_record_count > 0 and cache_reporting_call_count == 0,
        "prompt_cache_hits_missing": cache_reporting_call_count > 0 and cache_hit_call_count == 0,
        "output_tokens_not_primary_driver": prompt_tokens > 0 and completion_tokens * 3 < prompt_tokens,
    }


def latency_optimization_priorities(hints: dict[str, bool]) -> list[str]:
    priorities: list[str] = []
    if hints.get("provider_invocation_count_high"):
        priorities.extend(
            [
                "attribute_provider_invocations_to_manager_rounds",
                "reduce_provider_request_count_per_user_turn",
            ]
        )
    if hints.get("stage_overhead_high"):
        priorities.append("attribute_stage_overhead_to_tool_db_renderer_spans")
    if hints.get("turn_non_provider_runtime_high"):
        priorities.append("attribute_turn_non_provider_runtime_to_db_guard_renderer_spans")
    if hints.get("prompt_token_volume_high") or hints.get("stage_latency_high"):
        priorities.append("compact_dynamic_context_packets_before_full_suite")
    if hints.get("prompt_cache_metrics_missing") or hints.get("prompt_cache_hits_missing"):
        priorities.extend(
            [
                "move_stable_tool_schema_prefix_before_dynamic_payload",
                "monitor_cached_tokens_before_repeating_runs",
            ]
        )
    return priorities


def _latency_slo_row(
    row: dict[str, Any],
    *,
    observed_latency_ms: int,
    latency_class: str,
    observed_latency_field: str,
) -> dict[str, Any]:
    thresholds = PRODUCT_LATENCY_TARGETS_MS.get(latency_class, PRODUCT_LATENCY_TARGETS_MS["diagnostic_probe"])
    result = dict(row)
    result.update(
        {
            "latency_class": latency_class,
            "observed_latency_field": observed_latency_field,
            "observed_latency_ms": observed_latency_ms,
            "thresholds_ms": thresholds,
            "single_sample_status": _latency_budget_status(observed_latency_ms, thresholds),
        }
    )
    return result


def _stage_overhead_slo_row(row: dict[str, Any]) -> dict[str, Any]:
    observed_latency_ms = int(row.get("stage_overhead_ms") or 0)
    result = dict(row)
    result.update(
        {
            "observed_latency_field": "stage_overhead_ms",
            "observed_latency_ms": observed_latency_ms,
            "thresholds_ms": {
                "target_ms": STAGE_OVERHEAD_TARGET_MS,
                "warn_ms": STAGE_OVERHEAD_WARN_MS,
                "hard_ms": STAGE_OVERHEAD_HARD_MS,
            },
            "single_sample_status": _stage_overhead_budget_status(observed_latency_ms),
        }
    )
    return result


def _latency_budget_status(observed_latency_ms: int, thresholds: dict[str, int]) -> str:
    if observed_latency_ms <= int(thresholds.get("target_p95_ms") or 0):
        return "within_interactive_budget"
    if observed_latency_ms <= int(thresholds.get("hard_timeout_ms") or 0):
        return "over_interactive_budget"
    return "hard_timeout_budget_exceeded"


def _stage_overhead_budget_status(observed_latency_ms: int) -> str:
    if observed_latency_ms <= STAGE_OVERHEAD_WARN_MS:
        return "within_stage_overhead_budget"
    if observed_latency_ms <= STAGE_OVERHEAD_HARD_MS:
        return "stage_overhead_over_budget"
    return "stage_overhead_hard_budget_exceeded"


def _latency_class_for_turn(row: dict[str, Any]) -> str:
    turn_kind = str(row.get("diagnostic_turn_kind") or "").strip()
    case_id = str(row.get("diagnostic_case_id") or "").strip()
    if _metadata_contains(case_id, ("exact_item", "fooddb", "websearch", "web_search")):
        return "fooddb_or_web_evidence"
    if turn_kind in {"budget_query", "no_plan_budget_query", "remaining_query", "plan_query", "body_query"}:
        return "read_only_or_entry"
    if turn_kind in {"body_observation", "weight_record", "weight_query"}:
        return "body_observation"
    if turn_kind in {
        "bare_basket",
        "listed_basket",
        "followup_refinement",
        "explicit_item_correction",
        "explicit_item_removal",
        "correction",
        "removal",
    }:
        return "intake_clarify_or_correction"
    if turn_kind in {"exact_item_commit", "new_meal", "single_item_log"}:
        return "intake_no_web"
    return "diagnostic_probe"


def _latency_class_for_manager_scope(scope: Any) -> str:
    normalized = str(scope or "").strip()
    if normalized == "turn_entry_or_read_only":
        return "read_only_or_entry"
    if normalized == "body_observation":
        return "body_observation"
    if normalized == "intake_execution":
        return "intake_no_web"
    return "diagnostic_probe"


def _metadata_contains(value: str, needles: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(needle in lowered for needle in needles)


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("single_sample_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _latency_slo_summary(
    *,
    budget_rows: list[dict[str, Any]],
    stage_overhead_rows: list[dict[str, Any]],
    provider_invocation_records: list[dict[str, Any]],
) -> dict[str, Any]:
    hard_statuses = {"hard_timeout_budget_exceeded", "stage_overhead_hard_budget_exceeded"}
    over_statuses = {"over_interactive_budget", "stage_overhead_over_budget"}
    all_rows = [*budget_rows, *stage_overhead_rows]
    statuses = {str(row.get("single_sample_status") or "") for row in all_rows}
    return {
        "budget_row_source": "provider_turn_budget_or_manager_scope_fallback",
        "provider_invocation_count": len(provider_invocation_records),
        "budget_row_count": len(budget_rows),
        "stage_overhead_row_count": len(stage_overhead_rows),
        "single_sample_hard_budget_exceeded": bool(statuses & hard_statuses),
        "single_sample_over_interactive_budget": bool(statuses & over_statuses),
        "single_sample_clean": bool(all_rows) and not bool(statuses & (hard_statuses | over_statuses)),
    }


def _diagnostic_stage_latency_breakdown(
    *,
    stage_latency_records: list[dict[str, Any]],
    provider_invocation_records: list[dict[str, Any]],
    total_provider_latency_ms: int,
) -> list[dict[str, Any]]:
    stage_totals: dict[tuple[int, str], int] = {}
    provider_totals: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for record in stage_latency_records:
        key = (
            int(record.get("source_index") or 0),
            str(record.get("diagnostic_stage_id") or "unknown_stage"),
        )
        stage_totals[key] = stage_totals.get(key, 0) + int(record.get("stage_latency_ms") or 0)
    for record in provider_invocation_records:
        key = (
            int(record.get("source_index") or 0),
            str(record.get("diagnostic_stage_id") or record.get("stage") or "unknown_stage"),
        )
        provider_totals.setdefault(key, []).append(record)
    rows: list[dict[str, Any]] = []
    for key in sorted(set(stage_totals) | set(provider_totals), key=lambda item: (item[0], item[1])):
        records = provider_totals.get(key, [])
        provider_latency_ms = sum(int(record.get("latency_ms") or 0) for record in records)
        stage_latency_ms = stage_totals.get(key, 0)
        rows.append(
            {
                "source_index": key[0],
                "diagnostic_stage_id": key[1],
                "stage_latency_ms": stage_latency_ms,
                "provider_invocation_count": len(records),
                "provider_invocation_latency_ms": provider_latency_ms,
                "stage_overhead_ms": max(0, stage_latency_ms - provider_latency_ms),
                "latency_share_pct": _latency_share_pct(provider_latency_ms, total_provider_latency_ms),
            }
        )
    return sorted(
        rows,
        key=lambda item: (-int(item.get("stage_latency_ms") or 0), str(item.get("diagnostic_stage_id") or "")),
    )


def _group_provider_latency(
    records: list[dict[str, Any]],
    *,
    keys: tuple[str, ...],
    labels: dict[str, str] | None = None,
    total_provider_latency_ms: int,
) -> list[dict[str, Any]]:
    labels = labels or {}
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for record in records:
        key = tuple(record.get(name) if record.get(name) is not None else labels.get(name) for name in keys)
        groups.setdefault(key, []).append(record)
    rows: list[dict[str, Any]] = []
    for key, items in groups.items():
        latency_ms = sum(int(item.get("latency_ms") or 0) for item in items)
        row = {name: value for name, value in zip(keys, key, strict=True)}
        row.update(
            {
                "provider_invocation_count": len(items),
                "provider_invocation_latency_ms": latency_ms,
                "prompt_tokens": sum(int(item.get("prompt_tokens") or 0) for item in items),
                "completion_tokens": sum(int(item.get("completion_tokens") or 0) for item in items),
                "cached_tokens": sum(int(item.get("cached_tokens") or 0) for item in items),
                "cache_reporting_call_count": sum(1 for item in items if item.get("cached_tokens_reported") is True),
                "provider_wrapper_overhead_ms": sum(
                    int(item.get("provider_wrapper_overhead_ms") or 0) for item in items
                ),
                "transport_attempt_count": sum(int(item.get("transport_attempt_count") or 0) for item in items),
                "transport_attempt_latency_ms": sum(
                    int(item.get("transport_attempt_latency_ms") or 0) for item in items
                ),
                "slowest_transport_attempt_ms": max(
                    (int(item.get("slowest_transport_attempt_ms") or 0) for item in items),
                    default=0,
                ),
                "latency_share_pct": _latency_share_pct(latency_ms, total_provider_latency_ms),
            }
        )
        rows.append(row)
    return sorted(rows, key=lambda item: (-int(item.get("provider_invocation_latency_ms") or 0), str(item)))


def _case_turn_runtime_breakdown(
    records: list[dict[str, Any]],
    *,
    total_turn_latency_ms: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        turn_latency_ms = int(record.get("turn_latency_ms") or 0)
        rows.append(
            {
                "source_index": record.get("source_index"),
                "diagnostic_stage_id": record.get("diagnostic_stage_id"),
                "diagnostic_case_id": record.get("diagnostic_case_id"),
                "diagnostic_turn": record.get("diagnostic_turn"),
                "diagnostic_turn_kind": record.get("diagnostic_turn_kind"),
                "turn_latency_ms": turn_latency_ms,
                "provider_invocation_count": int(record.get("provider_invocation_count") or 0),
                "provider_invocation_latency_ms": int(record.get("provider_invocation_latency_ms") or 0),
                "non_provider_latency_ms": int(record.get("non_provider_latency_ms") or 0),
                "prompt_tokens": int(record.get("prompt_tokens") or 0),
                "completion_tokens": int(record.get("completion_tokens") or 0),
                "cached_tokens": int(record.get("cached_tokens") or 0),
                "cache_reporting_call_count": int(record.get("cache_reporting_call_count") or 0),
                "latency_share_pct": _latency_share_pct(turn_latency_ms, total_turn_latency_ms),
            }
        )
    return sorted(rows, key=lambda item: (-int(item.get("turn_latency_ms") or 0), str(item)))


def _slowest_turn_runtime_segments(records: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
    rows = [
        {
            "source_index": record.get("source_index"),
            "diagnostic_stage_id": record.get("diagnostic_stage_id"),
            "diagnostic_case_id": record.get("diagnostic_case_id"),
            "diagnostic_turn": record.get("diagnostic_turn"),
            "diagnostic_turn_kind": record.get("diagnostic_turn_kind"),
            "turn_latency_ms": int(record.get("turn_latency_ms") or 0),
            "provider_invocation_latency_ms": int(record.get("provider_invocation_latency_ms") or 0),
            "non_provider_latency_ms": int(record.get("non_provider_latency_ms") or 0),
            "provider_invocation_count": int(record.get("provider_invocation_count") or 0),
        }
        for record in records
    ]
    return sorted(rows, key=lambda item: -int(item.get("turn_latency_ms") or 0))[:limit]


def _slowest_provider_invocations(records: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
    projected = [
        {
            "source_index": record.get("source_index"),
            "invocation_index": record.get("invocation_index"),
            "stage": record.get("stage"),
            "diagnostic_stage_id": record.get("diagnostic_stage_id"),
            "diagnostic_case_id": record.get("diagnostic_case_id"),
            "diagnostic_turn": record.get("diagnostic_turn"),
            "diagnostic_turn_kind": record.get("diagnostic_turn_kind"),
            "manager_round_index": record.get("manager_round_index"),
            "manager_loop_scope": record.get("manager_loop_scope"),
            "provider_trace_stage": record.get("provider_trace_stage"),
            "latency_ms": int(record.get("latency_ms") or 0),
            "timeout_budget_ms": int(record.get("timeout_budget_ms") or 0),
            "prompt_tokens": int(record.get("prompt_tokens") or 0),
            "completion_tokens": int(record.get("completion_tokens") or 0),
            "cached_tokens_reported": record.get("cached_tokens_reported") is True,
            "cached_tokens": int(record.get("cached_tokens") or 0),
            "provider_wrapper_overhead_ms": int(record.get("provider_wrapper_overhead_ms") or 0),
            "transport_attempt_count": int(record.get("transport_attempt_count") or 0),
            "transport_attempt_latency_ms": int(record.get("transport_attempt_latency_ms") or 0),
            "slowest_transport_attempt_ms": int(record.get("slowest_transport_attempt_ms") or 0),
            "transport_attempt_statuses": list(record.get("transport_attempt_statuses") or []),
        }
        for record in records
    ]
    return sorted(projected, key=lambda item: -int(item.get("latency_ms") or 0))[:limit]


def _latency_share_pct(value_ms: int, total_ms: int) -> float:
    if total_ms <= 0:
        return 0.0
    return round((value_ms / total_ms) * 100, 2)


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []
