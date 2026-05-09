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

from scripts.accurate_intake_live_latency_summary import (  # noqa: E402
    build_latency_breakdown,
    build_latency_root_cause_hints,
    build_latency_slo,
    build_prompt_cache_identity_summary,
    latency_optimization_priorities,
)


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
_CACHE_REPORTING_FIELD_CANDIDATES = [
    "prompt_tokens_details.cached_tokens",
    "input_tokens_details.cached_tokens",
    "cached_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
]


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
    cached_prompt_tokens_observed = cached_prompt_tokens if cache_reporting_call_count > 0 else None
    cached_prompt_tokens_known = bool(usage_records) and cache_reporting_call_count == len(usage_records)
    max_prompt_tokens_per_usage_record = max((int(record.get("prompt_tokens") or 0) for record in usage_records), default=0)
    reported_cost_usd = sum(float(record["cost_usd"]) for record in cost_records) if cost_records else None
    cost_unavailable = bool(usage_records) and not cost_records
    latency_breakdown = build_latency_breakdown(
        stage_latency_records=stage_latency_records,
        provider_invocation_records=provider_invocation_records,
        turn_latency_records=turn_latency_records,
    )
    latency_slo = build_latency_slo(
        latency_breakdown=latency_breakdown,
        provider_invocation_records=provider_invocation_records,
    )
    prompt_cache_identity_summary = build_prompt_cache_identity_summary(provider_invocation_records)
    provider_request_footprint_summary = _provider_request_footprint_summary(provider_invocation_records)
    latency_root_cause_hints = build_latency_root_cause_hints(
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
            "prompt_cache_identity_summary": prompt_cache_identity_summary,
            "prompt_cache_reporting_capability": _prompt_cache_reporting_capability(
                usage_records=usage_records,
                cache_reporting_call_count=cache_reporting_call_count,
                cache_hit_call_count=cache_hit_call_count,
                cached_prompt_tokens=cached_prompt_tokens,
            ),
            "provider_request_footprint_summary": provider_request_footprint_summary,
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
                "cached_prompt_tokens_observed": cached_prompt_tokens_observed,
                "cached_prompt_tokens_known": cached_prompt_tokens_known,
                "cache_reporting_call_count": cache_reporting_call_count,
                "cache_hit_call_count": cache_hit_call_count,
                "reported_cost_record_count": len(cost_records),
                "reported_cost_usd": reported_cost_usd,
                "cost_unavailable_without_pricing": cost_unavailable,
            },
            "latency_root_cause_hints": latency_root_cause_hints,
            "latency_optimization_priorities": latency_optimization_priorities(latency_root_cause_hints),
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
        prompt_cache_request = _dict(provider_trace.get("prompt_cache_request"))
        cached_tokens = _cached_tokens(usage)
        transport_summary = _transport_attempt_summary(provider_trace)
        latency_ms = _int(invocation.get("latency_ms"))
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
                "latency_ms": latency_ms,
                "timeout_budget_ms": _int(invocation.get("timeout_budget_ms")),
                "prompt_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
                "completion_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
                "cached_tokens_reported": cached_tokens is not None,
                "cached_tokens": int(cached_tokens or 0),
                "prompt_cache_identity_version": _optional_string(prompt_cache_request.get("identity_version")),
                "prompt_cache_stable_prefix_sha256": _optional_string(
                    prompt_cache_request.get("stable_prefix_sha256")
                ),
                "prompt_cache_stable_prefix_component_sha256": _dict(
                    prompt_cache_request.get("stable_prefix_component_sha256")
                ),
                "prompt_cache_dynamic_suffix_sha256": _optional_string(
                    prompt_cache_request.get("dynamic_suffix_sha256")
                ),
                "request_payload_utf8_bytes": _int(prompt_cache_request.get("request_payload_utf8_bytes")),
                "stable_prefix_utf8_bytes": _int(prompt_cache_request.get("stable_prefix_utf8_bytes")),
                "stable_prefix_component_utf8_bytes": _dict(
                    prompt_cache_request.get("stable_prefix_component_utf8_bytes")
                ),
                "dynamic_suffix_utf8_bytes": _int(prompt_cache_request.get("dynamic_suffix_utf8_bytes")),
                "dynamic_suffix_component_utf8_bytes": _dict(
                    prompt_cache_request.get("dynamic_suffix_component_utf8_bytes")
                ),
                "prompt_cache_key_present": prompt_cache_request.get("provider_request_includes_prompt_cache_key")
                is True,
                "provider_wrapper_overhead_ms": _provider_wrapper_overhead_ms(
                    latency_ms,
                    transport_summary,
                ),
                **transport_summary,
            }
        )
    return records


def _transport_attempt_summary(provider_trace: dict[str, Any]) -> dict[str, Any]:
    attempts = [_dict(item) for item in _list(provider_trace.get("transport_attempts"))]
    durations = [_int(attempt.get("duration_ms")) for attempt in attempts]
    statuses = [
        str(attempt.get("status"))
        for attempt in attempts
        if attempt.get("status") is not None
    ]
    return {
        "transport_attempt_count": len(attempts),
        "transport_attempt_latency_ms": sum(durations),
        "slowest_transport_attempt_ms": max(durations, default=0),
        "transport_attempt_statuses": statuses,
    }


def _provider_wrapper_overhead_ms(latency_ms: int, transport_summary: dict[str, Any]) -> int:
    if int(transport_summary.get("transport_attempt_count") or 0) <= 0:
        return 0
    return max(0, latency_ms - int(transport_summary.get("transport_attempt_latency_ms") or 0))


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


def _provider_request_footprint_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    measured = [record for record in records if int(record.get("request_payload_utf8_bytes") or 0) > 0]
    stable_component_totals: dict[str, int] = {}
    dynamic_component_totals: dict[str, int] = {}
    for record in measured:
        for key, value in _dict(record.get("stable_prefix_component_utf8_bytes")).items():
            stable_component_totals[str(key)] = stable_component_totals.get(str(key), 0) + _int(value)
        for key, value in _dict(record.get("dynamic_suffix_component_utf8_bytes")).items():
            dynamic_component_totals[str(key)] = dynamic_component_totals.get(str(key), 0) + _int(value)
    return {
        "measurement": "json_utf8_bytes_trace_only",
        "provider_usage_is_token_truth": True,
        "record_count": len(measured),
        "total_request_payload_utf8_bytes": sum(_int(record.get("request_payload_utf8_bytes")) for record in measured),
        "max_request_payload_utf8_bytes": max(
            (_int(record.get("request_payload_utf8_bytes")) for record in measured),
            default=0,
        ),
        "total_stable_prefix_utf8_bytes": sum(_int(record.get("stable_prefix_utf8_bytes")) for record in measured),
        "total_dynamic_suffix_utf8_bytes": sum(_int(record.get("dynamic_suffix_utf8_bytes")) for record in measured),
        "max_dynamic_suffix_utf8_bytes": max(
            (_int(record.get("dynamic_suffix_utf8_bytes")) for record in measured),
            default=0,
        ),
        "stable_prefix_component_utf8_bytes": dict(sorted(stable_component_totals.items())),
        "dynamic_suffix_component_utf8_bytes": dict(sorted(dynamic_component_totals.items())),
        "largest_stable_prefix_component": _largest_utf8_component(stable_component_totals),
        "largest_dynamic_suffix_component": _largest_utf8_component(dynamic_component_totals),
    }


def _largest_utf8_component(totals: dict[str, int]) -> dict[str, Any] | None:
    if not totals:
        return None
    key, utf8_bytes = max(totals.items(), key=lambda item: item[1])
    return {"component": key, "utf8_bytes": utf8_bytes}


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
    if "cache_read_input_tokens" in usage:
        return _int(usage.get("cache_read_input_tokens"))
    return None


def _prompt_cache_reporting_capability(
    *,
    usage_records: list[dict[str, Any]],
    cache_reporting_call_count: int,
    cache_hit_call_count: int,
    cached_prompt_tokens: int,
) -> dict[str, Any]:
    usage_record_count = len(usage_records)
    return {
        "truth_source": "provider_reported_usage_only",
        "cache_reporting_status": _cache_reporting_status(
            usage_record_count=usage_record_count,
            cache_reporting_call_count=cache_reporting_call_count,
            cache_hit_call_count=cache_hit_call_count,
        ),
        "cached_token_count_status": _cached_token_count_status(
            usage_record_count=usage_record_count,
            cache_reporting_call_count=cache_reporting_call_count,
            cache_hit_call_count=cache_hit_call_count,
        ),
        "usage_record_count": usage_record_count,
        "cache_reporting_call_count": cache_reporting_call_count,
        "cache_hit_call_count": cache_hit_call_count,
        "cached_prompt_tokens": cached_prompt_tokens,
        "cached_prompt_tokens_observed": cached_prompt_tokens if cache_reporting_call_count > 0 else None,
        "cached_tokens_unknown": usage_record_count > cache_reporting_call_count,
        "cache_hit_claim_allowed": cache_hit_call_count > 0,
        "cache_miss_claim_allowed": (
            usage_record_count > 0
            and cache_reporting_call_count == usage_record_count
            and cache_hit_call_count == 0
        ),
        "zero_cached_tokens_claim_allowed": (
            usage_record_count > 0
            and cache_reporting_call_count == usage_record_count
            and cache_hit_call_count == 0
        ),
        "latency_may_infer_cache_hit": False,
        "provider_passthrough_gap_possible": usage_record_count > 0 and cache_reporting_call_count == 0,
        "requires_provider_usage_passthrough": usage_record_count > 0 and cache_reporting_call_count == 0,
        "official_usage_field_candidates": list(_CACHE_REPORTING_FIELD_CANDIDATES),
    }


def _cache_reporting_status(
    *,
    usage_record_count: int,
    cache_reporting_call_count: int,
    cache_hit_call_count: int,
) -> str:
    if usage_record_count <= 0:
        return "no_usage_records"
    if cache_hit_call_count > 0:
        return "cache_hit_reported"
    if cache_reporting_call_count > 0:
        return "zero_cached_tokens_reported"
    return "not_reported"


def _cached_token_count_status(
    *,
    usage_record_count: int,
    cache_reporting_call_count: int,
    cache_hit_call_count: int,
) -> str:
    if usage_record_count <= 0:
        return "no_usage_records"
    if cache_reporting_call_count <= 0:
        return "unknown_provider_not_reported"
    if cache_reporting_call_count < usage_record_count:
        return "partial_provider_reported"
    if cache_hit_call_count > 0:
        return "reported_with_cache_hit"
    return "reported_zero_cached_tokens"


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
