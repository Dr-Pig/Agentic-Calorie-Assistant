from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
DEFAULT_ARTIFACTS = (
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_provider_health.json",
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_schema_probe.json",
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_fake_runtime_gate.json",
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_seeded_removal.json",
    ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic_single_case.json",
)
_FORBIDDEN_TRUE_FLAGS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_selected",
    "mutation_rollout_approved",
    "runtime_web_activation_approved",
    "live_provider_used_as_truth",
)
_COST_KEYS = (
    "estimated_cost_usd",
    "total_cost_usd",
    "cost_usd",
)
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


def build_accurate_intake_live_cost_summary(
    artifacts: list[dict[str, Any]],
    *,
    source_paths: list[Path] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    source_artifacts: list[dict[str, Any]] = []
    usage_records: list[dict[str, Any]] = []
    cost_records: list[dict[str, Any]] = []
    provider_invocation_records: list[dict[str, Any]] = []
    stage_latency_records: list[dict[str, Any]] = []
    turn_latency_records: list[dict[str, Any]] = []
    stage_count = 0
    provider_invocation_count = 0
    total_stage_latency_ms = 0
    max_stage_latency_ms = 0
    total_provider_invocation_latency_ms = 0
    max_provider_invocation_latency_ms = 0

    for index, artifact in enumerate(artifacts):
        if artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
            blockers.append(f"source_{index}_artifact_type_invalid")
        for flag in _FORBIDDEN_TRUE_FLAGS:
            if artifact.get(flag) is True:
                blockers.append(f"source_{index}_{flag}")
        stages = [_dict(item) for item in _list(artifact.get("stages"))]
        invocations = [_dict(item) for item in _list(artifact.get("provider_invocations"))]
        stage_count += len(stages)
        provider_invocation_count += len(invocations)
        stage_latencies = [_int(stage.get("latency_ms")) for stage in stages]
        invocation_latencies = [_int(invocation.get("latency_ms")) for invocation in invocations]
        total_stage_latency_ms += sum(stage_latencies)
        max_stage_latency_ms = max([max_stage_latency_ms, *stage_latencies], default=max_stage_latency_ms)
        total_provider_invocation_latency_ms += sum(invocation_latencies)
        max_provider_invocation_latency_ms = max(
            [max_provider_invocation_latency_ms, *invocation_latencies],
            default=max_provider_invocation_latency_ms,
        )
        stage_latency_records.extend(_stage_latency_records(stages, source_index=index))
        turn_latency_records.extend(_turn_latency_records(_list(artifact.get("cases")), source_index=index))
        path = source_paths[index] if source_paths and index < len(source_paths) else None
        source_artifacts.append(
            {
                "index": index,
                "path": str(path) if path is not None else None,
                "artifact_type": _optional_string(artifact.get("artifact_type")),
                "generated_at_utc": _optional_string(artifact.get("generated_at_utc")),
                "provider_profile_id": _optional_string(artifact.get("provider_profile_id")),
                "model": _optional_string(artifact.get("provider_profile_model")),
                "stage_ids": [str(stage.get("stage_id") or "") for stage in stages],
                "sha256": _source_hash(artifact, path=path),
                "sha256_kind": "source_file_bytes" if path is not None and path.exists() else "canonical_json_payload",
            }
        )
        provider_invocation_records.extend(_provider_invocation_records(invocations, source_index=index))
        invocation_usage_records = _usage_records_from_invocations(invocations, source_index=index)
        usage_records.extend(invocation_usage_records or _usage_records(artifact, source_index=index))
        invocation_cost_records = _cost_records_from_invocations(invocations, source_index=index)
        cost_records.extend(invocation_cost_records or _cost_records(artifact, source_index=index))

    prompt_tokens = sum(int(record.get("prompt_tokens") or 0) for record in usage_records)
    completion_tokens = sum(int(record.get("completion_tokens") or 0) for record in usage_records)
    total_tokens = sum(int(record.get("total_tokens") or 0) for record in usage_records)
    cached_prompt_tokens = sum(int(record.get("cached_tokens") or 0) for record in usage_records)
    cache_reporting_call_count = sum(1 for record in usage_records if record.get("cached_tokens_reported") is True)
    cache_hit_call_count = sum(1 for record in usage_records if int(record.get("cached_tokens") or 0) > 0)
    max_prompt_tokens_per_usage_record = max((int(record.get("prompt_tokens") or 0) for record in usage_records), default=0)
    reported_cost_usd = sum(float(record["cost_usd"]) for record in cost_records) if cost_records else None
    cost_unavailable = bool(usage_records) and not cost_records
    latency_breakdown = _latency_breakdown(
        stage_latency_records=stage_latency_records,
        provider_invocation_records=provider_invocation_records,
        turn_latency_records=turn_latency_records,
    )
    latency_slo = _latency_slo(
        latency_breakdown=latency_breakdown,
        provider_invocation_records=provider_invocation_records,
    )
    latency_root_cause_hints = _latency_root_cause_hints(
        provider_invocation_count=provider_invocation_count,
        max_stage_latency_ms=max_stage_latency_ms,
        stage_overhead_ms=int(latency_breakdown.get("stage_overhead_ms") or 0),
        max_turn_non_provider_latency_ms=int(latency_breakdown.get("max_turn_non_provider_latency_ms") or 0),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        max_prompt_tokens_per_usage_record=max_prompt_tokens_per_usage_record,
        usage_record_count=len(usage_records),
        cache_reporting_call_count=cache_reporting_call_count,
        cache_hit_call_count=cache_hit_call_count,
    )
    return _json_safe(
        {
            "artifact_type": "accurate_intake_mvp_live_cost_summary",
            "artifact_schema_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "claim_scope": "live_diagnostic_cost_summary",
            "generated_artifact_policy": {
                "commit_as_repo_truth": False,
                "local_diagnostic_evidence_only": True,
            },
            "input_integrity": {"passed": not blockers, "blockers": sorted(set(blockers))},
            "source_artifacts": source_artifacts,
            "provider_invocation_records": provider_invocation_records,
            "latency_breakdown": latency_breakdown,
            "latency_slo": latency_slo,
            "usage_records": usage_records,
            "cost_records": cost_records,
            "summary": {
                "source_artifact_count": len(artifacts),
                "stage_count": stage_count,
                "provider_invocation_count": provider_invocation_count,
                "total_stage_latency_ms": total_stage_latency_ms,
                "max_stage_latency_ms": max_stage_latency_ms,
                "total_provider_invocation_latency_ms": total_provider_invocation_latency_ms,
                "max_provider_invocation_latency_ms": max_provider_invocation_latency_ms,
                "usage_record_count": len(usage_records),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "max_prompt_tokens_per_usage_record": max_prompt_tokens_per_usage_record,
                "cached_prompt_tokens": cached_prompt_tokens,
                "cache_reporting_call_count": cache_reporting_call_count,
                "cache_hit_call_count": cache_hit_call_count,
                "reported_cost_record_count": len(cost_records),
                "reported_cost_usd": reported_cost_usd,
                "cost_unavailable_without_pricing": cost_unavailable,
            },
            "latency_root_cause_hints": latency_root_cause_hints,
            "latency_optimization_priorities": _latency_optimization_priorities(latency_root_cause_hints),
            "cost_policy": {
                "billing_truth_source": "provider_reported_artifact_fields_only",
                "token_counts_are_not_billing_truth": True,
                "pricing_table_applied": False,
                "cost_unavailable_without_pricing": cost_unavailable,
            },
        }
    )


def write_accurate_intake_live_cost_summary(
    *,
    artifact_paths: list[Path] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    output_path: Path | None = None,
) -> Path:
    paths = list(artifact_paths or DEFAULT_ARTIFACTS)
    artifacts = [_dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    summary = build_accurate_intake_live_cost_summary(artifacts, source_paths=paths)
    path = output_path or output_dir / "accurate_intake_mvp_live_cost_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _usage_records(value: Any, *, source_index: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path, usage in _walk_usage(value):
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or usage.get("total_token") or 0)
        if total_tokens <= 0:
            total_tokens = prompt_tokens + completion_tokens
        if prompt_tokens <= 0 and completion_tokens <= 0 and total_tokens <= 0:
            continue
        cached_tokens = _cached_tokens(usage)
        records.append(
            {
                "source_index": source_index,
                "json_path": path,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cached_tokens_reported": cached_tokens is not None,
                "cached_tokens": int(cached_tokens or 0),
            }
        )
    return records


def _provider_invocation_records(invocations: list[dict[str, Any]], *, source_index: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, invocation in enumerate(invocations):
        provider_trace = _dict(invocation.get("provider_trace"))
        usage = _dict(provider_trace.get("usage"))
        cached_tokens = _cached_tokens(usage)
        diagnostic_stage_id = _optional_string(invocation.get("diagnostic_stage_id"))
        stage = _optional_string(invocation.get("stage"))
        records.append(
            {
                "source_index": source_index,
                "invocation_index": index,
                "stage": stage,
                "diagnostic_stage_id": diagnostic_stage_id,
                "diagnostic_case_id": _optional_string(invocation.get("diagnostic_case_id")),
                "diagnostic_turn": _optional_int(invocation.get("diagnostic_turn")),
                "diagnostic_turn_kind": _optional_string(invocation.get("diagnostic_turn_kind")),
                "manager_round_index": _optional_int(invocation.get("manager_round_index")),
                "manager_loop_scope": _optional_string(invocation.get("manager_loop_scope")),
                "provider_trace_stage": _optional_string(
                    invocation.get("provider_trace_stage") or provider_trace.get("stage")
                ),
                "provider_profile_id": _optional_string(invocation.get("provider_profile_id")),
                "model": _optional_string(invocation.get("provider_profile_model")),
                "latency_ms": _int(invocation.get("latency_ms")),
                "timeout_budget_ms": _int(invocation.get("timeout_budget_ms")),
                "prompt_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
                "completion_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
                "cached_tokens_reported": cached_tokens is not None,
                "cached_tokens": int(cached_tokens or 0),
            }
        )
    return records


def _stage_latency_records(stages: list[dict[str, Any]], *, source_index: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, stage in enumerate(stages):
        records.append(
            {
                "source_index": source_index,
                "stage_index": index,
                "diagnostic_stage_id": _optional_string(stage.get("stage_id")),
                "stage_latency_ms": _int(stage.get("latency_ms")),
                "timeout_budget_ms": _int(stage.get("timeout_budget_ms")),
                "status": _optional_string(stage.get("status")),
                "result_kind": _optional_string(stage.get("result_kind")),
            }
        )
    return records


def _turn_latency_records(cases: list[Any], *, source_index: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for case_index, case_value in enumerate(cases):
        case = _dict(case_value)
        case_id = _optional_string(case.get("case_id"))
        stage_id = _optional_string(case.get("stage_id"))
        for turn_index, turn_value in enumerate(_list(case.get("turns"))):
            turn = _dict(turn_value)
            invocation_summary = _dict(turn.get("provider_invocation_summary"))
            total_ms = _int(turn.get("latency_ms"))
            provider_ms = _int(invocation_summary.get("provider_invocation_latency_ms"))
            non_provider_ms = _int(turn.get("non_provider_latency_ms"))
            if non_provider_ms <= 0 and total_ms > 0:
                non_provider_ms = max(0, total_ms - provider_ms)
            records.append(
                {
                    "source_index": source_index,
                    "case_index": case_index,
                    "turn_index": turn_index,
                    "diagnostic_stage_id": stage_id,
                    "diagnostic_case_id": case_id,
                    "diagnostic_turn": _optional_int(turn.get("turn")),
                    "diagnostic_turn_kind": _optional_string(turn.get("kind")),
                    "turn_latency_ms": total_ms,
                    "provider_invocation_latency_ms": provider_ms,
                    "non_provider_latency_ms": non_provider_ms,
                    "provider_invocation_count": _int(invocation_summary.get("provider_invocation_count")),
                    "prompt_tokens": _int(invocation_summary.get("prompt_tokens")),
                    "completion_tokens": _int(invocation_summary.get("completion_tokens")),
                    "cached_tokens": _int(invocation_summary.get("cached_tokens")),
                    "cache_reporting_call_count": _int(invocation_summary.get("cache_reporting_call_count")),
                }
            )
    return records


def _latency_breakdown(
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


def _latency_slo(
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
    return sorted(rows, key=lambda item: (-int(item.get("stage_latency_ms") or 0), str(item.get("diagnostic_stage_id") or "")))


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
        }
        for record in records
    ]
    return sorted(projected, key=lambda item: -int(item.get("latency_ms") or 0))[:limit]


def _latency_share_pct(value_ms: int, total_ms: int) -> float:
    if total_ms <= 0:
        return 0.0
    return round((value_ms / total_ms) * 100, 2)


def _usage_records_from_invocations(invocations: list[dict[str, Any]], *, source_index: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, invocation in enumerate(invocations):
        usage = _dict(_dict(invocation.get("provider_trace")).get("usage"))
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or usage.get("total_token") or 0)
        if total_tokens <= 0:
            total_tokens = prompt_tokens + completion_tokens
        if prompt_tokens <= 0 and completion_tokens <= 0 and total_tokens <= 0:
            continue
        cached_tokens = _cached_tokens(usage)
        records.append(
            {
                "source_index": source_index,
                "json_path": f"$.provider_invocations[{index}].provider_trace.usage",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cached_tokens_reported": cached_tokens is not None,
                "cached_tokens": int(cached_tokens or 0),
            }
        )
    return records


def _cost_records_from_invocations(invocations: list[dict[str, Any]], *, source_index: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, invocation in enumerate(invocations):
        payload = _dict(invocation.get("provider_trace"))
        for key in _COST_KEYS:
            if key not in payload:
                continue
            try:
                cost = float(payload[key])
            except (TypeError, ValueError):
                continue
            records.append(
                {
                    "source_index": source_index,
                    "json_path": f"$.provider_invocations[{index}].provider_trace.{key}",
                    "cost_usd": cost,
                }
            )
    return records


def _cost_records(value: Any, *, source_index: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path, payload in _walk_dicts(value):
        for key in _COST_KEYS:
            if key not in payload:
                continue
            try:
                cost = float(payload[key])
            except (TypeError, ValueError):
                continue
            records.append({"source_index": source_index, "json_path": f"{path}.{key}", "cost_usd": cost})
    return records


def _walk_usage(value: Any, path: str = "$") -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        usage = value.get("usage")
        if isinstance(usage, dict):
            records.append((f"{path}.usage", dict(usage)))
        for key, item in value.items():
            if key == "usage":
                continue
            records.extend(_walk_usage(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            records.extend(_walk_usage(item, f"{path}[{index}]"))
    return records


def _walk_dicts(value: Any, path: str = "$") -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        records.append((path, dict(value)))
        for key, item in value.items():
            records.extend(_walk_dicts(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            records.extend(_walk_dicts(item, f"{path}[{index}]"))
    return records


def _cached_tokens(usage: dict[str, Any]) -> int | None:
    prompt_details = usage.get("prompt_tokens_details")
    if isinstance(prompt_details, dict) and "cached_tokens" in prompt_details:
        return _int(prompt_details.get("cached_tokens"))
    input_details = usage.get("input_tokens_details")
    if isinstance(input_details, dict) and "cached_tokens" in input_details:
        return _int(input_details.get("cached_tokens"))
    if "cached_tokens" in usage:
        return _int(usage.get("cached_tokens"))
    return None


def _latency_root_cause_hints(
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


def _latency_optimization_priorities(hints: dict[str, bool]) -> list[str]:
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


def _artifact_hash(artifact: dict[str, Any]) -> str:
    encoded = json.dumps(artifact, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_hash(artifact: dict[str, Any], *, path: Path | None) -> str:
    if path is not None and path.exists():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return _artifact_hash(artifact)


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None


def _int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return 0
    return 0


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Accurate Intake MVP live diagnostic cost summary.")
    parser.add_argument("--artifact", action="append", dest="artifacts")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output")
    args = parser.parse_args()
    paths = [Path(item) for item in (args.artifacts or [str(path) for path in DEFAULT_ARTIFACTS])]
    output = write_accurate_intake_live_cost_summary(
        artifact_paths=paths,
        output_dir=Path(args.output_dir),
        output_path=Path(args.output) if args.output else None,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
