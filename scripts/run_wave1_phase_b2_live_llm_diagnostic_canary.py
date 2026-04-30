from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.live_diagnostic_decision_pack import (
    B2_LIVE_CONTRACT_CASE_IDS,
    VERDICT_READINESS_BLOCKER,
    build_live_diagnostic_readiness_claim,
    build_b2_live_llm_diagnostic_contract_report,
)


DEFAULT_BASE_URL = "https://space.ai-builders.com/backend/v1"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
DEFAULT_STABLE_B2_ARTIFACT = DEFAULT_OUTPUT_DIR / "wave1_phase_b2_evidence_synthesis_smoke.json"
DEFAULT_LATEST_REPORT = DEFAULT_OUTPUT_DIR / "wave1_phase_b2_live_llm_diagnostic_canary.json"
DEFAULT_B2_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID = "builderspace-grok-4-fast-b2-diagnostic"
APPROVED_ASK_FIRST_POLICY_IDS = ("self_selected_basket_without_listed_items",)

_PROVIDER_PROFILES: dict[str, dict[str, Any]] = {
    DEFAULT_B2_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID: {
        "provider_profile_id": DEFAULT_B2_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID,
        "provider": "builderspace",
        "model": "grok-4-fast",
        "provider_profile_role": "b2_live_diagnostic_primary",
        "cost_tier": "low",
        "manual_only": False,
        "allow_expensive_model_probe": False,
        "production_selected": False,
        "not_production_selection": True,
        "not_readiness_evidence": True,
        "temperature": 0.0,
        "max_tokens": 900,
        "schema_mode": "json_object",
    },
    "builderspace-deepseek-b2-comparison": {
        "provider_profile_id": "builderspace-deepseek-b2-comparison",
        "provider": "builderspace",
        "model": "deepseek",
        "provider_profile_role": "b2_live_diagnostic_comparison",
        "cost_tier": "low",
        "manual_only": False,
        "allow_expensive_model_probe": False,
        "production_selected": False,
        "not_production_selection": True,
        "not_readiness_evidence": True,
        "temperature": 0.0,
        "max_tokens": 900,
        "schema_mode": "json_object",
    },
    "builderspace-kimi-k2.5-b2-comparison": {
        "provider_profile_id": "builderspace-kimi-k2.5-b2-comparison",
        "provider": "builderspace",
        "model": "kimi-k2.5",
        "provider_profile_role": "b2_live_diagnostic_comparison",
        "cost_tier": "medium-low",
        "manual_only": False,
        "allow_expensive_model_probe": False,
        "production_selected": False,
        "not_production_selection": True,
        "not_readiness_evidence": True,
        "temperature": 1.0,
        "max_tokens": 900,
        "schema_mode": "json_object",
    },
    "builderspace-gpt-5-b2-manual": {
        "provider_profile_id": "builderspace-gpt-5-b2-manual",
        "provider": "builderspace",
        "model": "gpt-5",
        "provider_profile_role": "expensive_manual_baseline",
        "cost_tier": "high",
        "manual_only": True,
        "allow_expensive_model_probe": False,
        "production_selected": False,
        "not_production_selection": True,
        "not_readiness_evidence": True,
        "temperature": 1.0,
        "max_tokens": 1200,
        "schema_mode": "json_object",
    },
}


def provider_profile(provider_profile_id: str) -> dict[str, Any]:
    if provider_profile_id not in _PROVIDER_PROFILES:
        supported = ", ".join(sorted(_PROVIDER_PROFILES))
        raise ValueError(f"Unsupported B2 live diagnostic provider profile: {provider_profile_id}. Supported: {supported}")
    return dict(_PROVIDER_PROFILES[provider_profile_id])


def build_missing_token_report(
    *,
    phase_b2_report: dict[str, Any],
    provider_profile_id: str,
    payload_artifact_id: str,
) -> dict[str, Any]:
    profile = provider_profile(provider_profile_id)
    return _decorate_report(
        build_b2_live_llm_diagnostic_contract_report(
            phase_b2_report=phase_b2_report,
            provider_outputs_by_case_id={},
            provider_mode="not_invoked",
            payload_artifact_id=payload_artifact_id,
            model_profile=provider_profile_id,
            schema_mode=str(profile["schema_mode"]),
            approved_ask_first_policy_ids=APPROVED_ASK_FIRST_POLICY_IDS,
        ),
        profile=profile,
        provider_mode="not_invoked",
        live_invoked=False,
        failure_family="missing_provider_token",
        force_verdict=VERDICT_READINESS_BLOCKER,
    )


def build_provider_request_payload_for_case(deterministic_case: dict[str, Any]) -> dict[str, Any]:
    accepted_packets, rejected_candidates = _packet_lanes(deterministic_case)
    accepted_usage = _accepted_usage(accepted_packets)
    allowed_exactness = "exact" if accepted_usage == "exact" else "estimated" if accepted_usage == "anchor" else "none"
    base_payload: dict[str, Any] = {
        "diagnostic_scope": "b2_packet_synthesis_only",
        "case_id": deterministic_case.get("case_id"),
        "case_label_only": True,
        "input_message": deterministic_case.get("input_message"),
        "source_selection": _dict(deterministic_case.get("source_selection")),
        "accepted_packets": accepted_packets,
        "rejected_candidates": rejected_candidates,
        "query_only": _dict(deterministic_case.get("source_selection")).get("read_only") is True,
        "mutation_forbidden": True,
        "authority": {
            "mutation_authority": False,
            "ledger_truth_authority": False,
            "product_semantic_authority": False,
            "source_priority_authority": False,
        },
        "final_mapping": "not_provided_to_live_diagnostic",
    }
    if _is_ask_first_deterministic_case(deterministic_case):
        base_payload.update(
            {
                "contract_type": "clarify_only",
                "ask_first_required": True,
                "synthesis_allowed": False,
                "item_results_allowed": False,
                "item_results_required": False,
                "min_item_results": 0,
                "accepted_packets_count": len(accepted_packets),
                "accepted_usage": accepted_usage,
                "allowed_exactness": "none",
                "estimate_allowed": False,
                "kcal_range_allowed": False,
                "expected_output": "ask_followup_for_items_and_portions",
                "required_output": {
                    "top_level_key": "clarification",
                    "item_results_allowed": False,
                    "estimate_allowed": False,
                    "kcal_range_allowed": False,
                    "expected_output": "ask_followup_for_items_and_portions",
                    "allowed_fields": [
                        "clarification_question",
                        "followup_question",
                        "uncertainty_reason",
                    ],
                    "forbidden_fields": [
                        "item_results",
                        "likely_kcal",
                        "kcal_range",
                        "evidence_used",
                        "evidence_refs",
                        "logged",
                        "draft",
                        "ledger_update",
                        "mutation_result",
                        "source_priority_decision",
                        "product_semantic_decision",
                    ],
                },
            }
        )
        return base_payload
    base_payload.update(
        {
            "contract_type": "item_results_synthesis",
            "ask_first_required": False,
            "synthesis_allowed": True,
            "item_results_allowed": True,
            "item_results_required": True,
            "min_item_results": 1,
            "accepted_packets_count": len(accepted_packets),
            "accepted_usage": accepted_usage,
            "allowed_exactness": allowed_exactness,
            "estimate_allowed": True,
            "kcal_range_allowed": True,
            "required_output": {
                "top_level_key": "item_results",
                "item_results_required": True,
                "min_item_results": 1,
                "item_result_fields": [
                    "interpreted_food_identity",
                    "exactness_posture",
                    "kcal_range",
                    "likely_kcal",
                    "evidence_used",
                    "uncertainty_reason",
                    "suggested_followup_question",
                ],
                "forbidden_fields": [
                    "logged",
                    "draft",
                    "ledger_update",
                    "mutation_result",
                    "source_priority_decision",
                    "product_semantic_decision",
                ],
            },
        }
    )
    return base_payload


async def run_b2_live_llm_diagnostic_canary(
    *,
    phase_b2_report: dict[str, Any],
    token: str,
    provider_profile_id: str = DEFAULT_B2_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID,
    selected_case_ids: tuple[str, ...] = B2_LIVE_CONTRACT_CASE_IDS,
    payload_artifact_id: str = "deterministic_b2_artifact",
    base_url: str = DEFAULT_BASE_URL,
    timeout_seconds: int = 45,
    async_client_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    profile = provider_profile(provider_profile_id)
    if profile.get("manual_only") and not profile.get("allow_expensive_model_probe"):
        raise ValueError("expensive B2 diagnostic profile requires --allow-expensive-model-probe")
    if async_client_factory is None:
        import httpx

        async_client_factory = httpx.AsyncClient
    provider_outputs: dict[str, dict[str, Any]] = {}
    provider_case_traces: dict[str, dict[str, Any]] = {}
    async with async_client_factory(timeout=timeout_seconds) as client:
        for case_id in selected_case_ids:
            deterministic_case = _case_by_id(phase_b2_report, case_id)
            request_payload = build_provider_request_payload_for_case(deterministic_case)
            output, trace = await _invoke_builderspace_case(
                client=client,
                base_url=base_url,
                token=token,
                profile=profile,
                request_payload=request_payload,
            )
            provider_outputs[case_id] = output
            provider_case_traces[case_id] = trace
    report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=phase_b2_report,
        provider_outputs_by_case_id=provider_outputs,
        provider_mode="live",
        payload_artifact_id=payload_artifact_id,
        model_profile=provider_profile_id,
        schema_mode=str(profile["schema_mode"]),
        selected_case_ids=selected_case_ids,
        approved_ask_first_policy_ids=APPROVED_ASK_FIRST_POLICY_IDS,
        provider_traces_by_case_id=provider_case_traces,
    )
    report = _decorate_report(
        report,
        profile=profile,
        provider_mode="live",
        live_invoked=True,
        failure_family=None,
    )
    _attach_provider_traces(report, provider_case_traces)
    return report


async def _invoke_builderspace_case(
    *,
    client: Any,
    base_url: str,
    token: str,
    profile: dict[str, Any],
    request_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    response = await client.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "model": profile["model"],
            "temperature": profile["temperature"],
            "max_tokens": profile["max_tokens"],
            "response_format": {"type": profile["schema_mode"]},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a B2 packet synthesis diagnostic model. Return only JSON that follows the request contract. "
                        "For item_results_synthesis contracts, return at least one item_result using accepted_packets. "
                        "For clarify_only contracts, ask for the missing items or portions and do not return item_results. "
                        "Do not return logged, draft, ledger, mutation, source-priority, or product-semantic decisions."
                    ),
                },
                {"role": "user", "content": json.dumps(request_payload, ensure_ascii=False)},
            ],
        },
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    response.raise_for_status()
    data = response.json()
    parsed, schema_status, parse_trace = _parse_provider_json(data)
    return (
        parsed,
        {
            "provider": "builderspace",
            "model": profile["model"],
            "provider_profile_id": profile["provider_profile_id"],
            "provider_profile_role": profile["provider_profile_role"],
            "schema_status": schema_status,
            "latency_ms": latency_ms,
            "usage": _dict(data.get("usage")),
            "response_status": getattr(response, "status_code", None),
            "failure_family": None,
            **parse_trace,
        },
    )


def _parse_provider_json(data: dict[str, Any]) -> tuple[dict[str, Any], str, dict[str, Any]]:
    content = _extract_content(data)
    trace: dict[str, Any] = {
        "raw_provider_output_excerpt": _redacted_excerpt(content),
        "raw_top_level_keys": [],
        "raw_item_results_count": 0,
        "normalized_item_results_count": 0,
    }
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"item_results": [], "payload_shape_valid": False}, "fail", trace
    if isinstance(parsed, dict):
        normalized = _normalize_provider_payload(parsed)
        trace["raw_top_level_keys"] = sorted(str(key) for key in parsed)
        trace["raw_item_results_count"] = len(_list(parsed.get("item_results")))
        trace["normalized_item_results_count"] = len(_list(normalized.get("item_results")))
        return normalized, "strict_pass", trace
    return {"item_results": [], "payload_shape_valid": False}, "fail", trace


def _extract_content(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return "{}"
    message = _dict(_dict(choices[0]).get("message"))
    content = message.get("content")
    return content if isinstance(content, str) else "{}"


def _decorate_report(
    report: dict[str, Any],
    *,
    profile: dict[str, Any],
    provider_mode: str,
    live_invoked: bool,
    failure_family: str | None,
    force_verdict: str | None = None,
) -> dict[str, Any]:
    decorated = dict(report)
    decorated.update(
        {
            "provider_mode": provider_mode,
            "live_invoked": live_invoked,
            "live_provider_diagnostic_complete": live_invoked and force_verdict is None,
            "provider_profile_id": profile["provider_profile_id"],
            "provider_profile_model": profile["model"],
            "candidate_model": profile["model"],
            "provider_profile_role": profile["provider_profile_role"],
            "production_selected": False,
            "not_production_selection": True,
            "not_readiness_evidence": True,
            "diagnostic_scope": "b2_packet_synthesis_only",
            "readiness_scope": "none",
            "readiness_claimed": False,
            "readiness_claim": build_live_diagnostic_readiness_claim(
                provider_mode=provider_mode,
                live_invoked=live_invoked,
            ),
            "user_facing_enabled": False,
            "mutation_enabled": False,
            "failure_family": failure_family,
        }
    )
    if force_verdict:
        decorated["verdict_category"] = force_verdict
        decorated["verdict"] = {
            "category": force_verdict,
            "reason": failure_family,
            "canonicalizes_product_semantics": False,
        }
    return decorated


def _attach_provider_traces(report: dict[str, Any], traces: dict[str, dict[str, Any]]) -> None:
    for case in report.get("case_results", []):
        if not isinstance(case, dict):
            continue
        trace = _dict(traces.get(str(case.get("case_id"))))
        case["schema_status"] = trace.get("schema_status", "fail")
        case["usage"] = trace.get("usage", {})
        case["latency_ms"] = trace.get("latency_ms")
        case["raw_failure_family"] = trace.get("failure_family")
        case["provider_profile_id"] = trace.get("provider_profile_id")
        case["provider_profile_model"] = trace.get("model")
        case["raw_provider_output_excerpt"] = trace.get("raw_provider_output_excerpt", "")
        case["raw_top_level_keys"] = trace.get("raw_top_level_keys", [])
        case["raw_item_results_count"] = trace.get("raw_item_results_count", 0)
        case["normalized_item_results_count"] = trace.get("normalized_item_results_count", case.get("item_result_count", 0))


def _packet_lanes(deterministic_case: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    item_results = [_dict(item) for item in _list(_dict(deterministic_case.get("manager_pass_2")).get("item_results"))]
    rejected_ids = {
        str(candidate.get("packet_id"))
        for item in item_results
        for candidate in _list(item.get("rejected_candidates"))
        if _dict(candidate).get("packet_id")
    }
    evidence_usage_by_id = {
        str(evidence.get("packet_id")): str(evidence.get("usage") or "")
        for item in item_results
        for evidence in _list(item.get("evidence_used"))
        if _dict(evidence).get("packet_id")
    }
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for packet in _list(deterministic_case.get("packets")):
        packet_dict = _dict(packet)
        packet_id = str(packet_dict.get("packet_id") or "")
        if packet_id in rejected_ids:
            rejected.append({"packet_id": packet_id, **packet_dict})
        elif packet_id in evidence_usage_by_id:
            accepted_packet = dict(packet_dict)
            accepted_packet["accepted_usage"] = evidence_usage_by_id[packet_id]
            accepted.append(accepted_packet)
    if not rejected:
        rejected = [
            _dict(candidate)
            for item in item_results
            for candidate in _list(item.get("rejected_candidates"))
            if isinstance(candidate, dict)
        ]
    return accepted, rejected


def _accepted_usage(accepted_packets: list[dict[str, Any]]) -> str:
    usages = {str(packet.get("accepted_usage") or "") for packet in accepted_packets}
    if "exact" in usages:
        return "exact"
    if "anchor" in usages or "fallback" in usages:
        return "anchor"
    return "none"


def _normalize_provider_payload(parsed: dict[str, Any]) -> dict[str, Any]:
    return dict(parsed)


def _redacted_excerpt(content: str, limit: int = 500) -> str:
    excerpt = content[:limit]
    for marker in ("Authorization", "Bearer", "AI_BUILDER_TOKEN"):
        excerpt = excerpt.replace(marker, "[redacted]")
    return excerpt


def _is_ask_first_deterministic_case(deterministic_case: dict[str, Any]) -> bool:
    source_selection = _dict(deterministic_case.get("source_selection"))
    packets = [_dict(packet) for packet in _list(deterministic_case.get("packets"))]
    item_results = [_dict(item) for item in _list(_dict(deterministic_case.get("manager_pass_2")).get("item_results"))]
    source_requires_ask = source_selection.get("source_path") == "ask_user"
    semantic_rule_requires_ask = any(
        packet.get("rule_id") == "self_selected_basket_without_ingredients"
        or packet.get("semantic_problem") == "composition_unknown"
        for packet in packets
    )
    unresolved_without_evidence_or_kcal = bool(item_results) and all(
        item.get("exactness_posture") == "unresolved"
        and item.get("likely_kcal") is None
        and item.get("kcal_range") is None
        and not _list(item.get("evidence_used"))
        for item in item_results
    )
    return (source_requires_ask or semantic_rule_requires_ask) and unresolved_without_evidence_or_kcal


def _case_by_id(report: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in _list(report.get("cases")):
        candidate = _dict(case)
        if candidate.get("case_id") == case_id:
            return candidate
    raise KeyError(f"B2 deterministic artifact missing case_id={case_id}")


def _artifact_path(*, output_dir: Path, provider_profile_id: str, case_ids: tuple[str, ...]) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    suffix = uuid4().hex[:6]
    case_slug = "-".join(case_ids)
    return output_dir / f"wave1_phase_b2_live_llm_diagnostic_{timestamp}_{provider_profile_id}_{case_slug}_{suffix}.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _load_local_env(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path)
        return
    except ModuleNotFoundError:
        pass
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> int:
    _load_local_env(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Run B2 live LLM diagnostic canary.")
    parser.add_argument("--phase-b2-report", default=str(DEFAULT_STABLE_B2_ARTIFACT))
    parser.add_argument("--provider-profile-id", default=DEFAULT_B2_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)
    parser.add_argument("--base-url", default=os.getenv("AI_BUILDER_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-expensive-model-probe", action="store_true")
    args = parser.parse_args()

    provider_profile_id = str(args.provider_profile_id)
    profile = provider_profile(provider_profile_id)
    if profile["cost_tier"] == "high" and not args.allow_expensive_model_probe:
        raise SystemExit("expensive B2 diagnostic profile requires --allow-expensive-model-probe")
    if args.allow_expensive_model_probe:
        profile["allow_expensive_model_probe"] = True

    phase_b2_path = Path(args.phase_b2_report)
    phase_b2_report = _read_json(phase_b2_path)
    token = os.getenv("AI_BUILDER_TOKEN", "").strip()
    payload_artifact_id = phase_b2_path.as_posix()
    if not token:
        report = build_missing_token_report(
            phase_b2_report=phase_b2_report,
            provider_profile_id=provider_profile_id,
            payload_artifact_id=payload_artifact_id,
        )
    else:
        report = asyncio.run(
            run_b2_live_llm_diagnostic_canary(
                phase_b2_report=phase_b2_report,
                token=token,
                provider_profile_id=provider_profile_id,
                payload_artifact_id=payload_artifact_id,
                base_url=str(args.base_url),
            )
        )
    output_path = _artifact_path(
        output_dir=Path(args.output_dir),
        provider_profile_id=provider_profile_id,
        case_ids=B2_LIVE_CONTRACT_CASE_IDS,
    )
    _write_json(output_path, report)
    _write_json(DEFAULT_LATEST_REPORT, report)
    print(
        json.dumps(
            {
                "report_path": output_path.as_posix(),
                "latest_report_path": DEFAULT_LATEST_REPORT.as_posix(),
                "provider_mode": report.get("provider_mode"),
                "live_invoked": report.get("live_invoked"),
                "provider_profile_model": report.get("provider_profile_model"),
                "verdict_category": report.get("verdict_category"),
                "readiness_claimed": report.get("readiness_claimed"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


__all__ = [
    "DEFAULT_B2_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID",
    "APPROVED_ASK_FIRST_POLICY_IDS",
    "build_missing_token_report",
    "build_provider_request_payload_for_case",
    "provider_profile",
    "run_b2_live_llm_diagnostic_canary",
]


if __name__ == "__main__":
    raise SystemExit(main())
