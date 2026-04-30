from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.providers.builderspace_adapter import BuilderSpaceAdapter, BuilderSpaceResponseError
from app.providers.builderspace_runtime_contract import response_schema_for_stage
from app.providers.builderspace_transport import response_format_request_for_stage
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE
from app.shared.contracts.readiness_claim import build_readiness_claim
from scripts.run_wave1_phase_b_minimal_tool_loop_smoke import (
    CORE_SMOKE_CASE_MAP,
    NATURAL_MODE,
    PASS_2_COMMON_COMMERCIAL_MEAL_COMPACT_JSON_FIRST_PAYLOAD,
    SINGLE_MANAGER_SYSTEM_PROMPT,
    _fixture_packet,
    _food_names_for_message,
    _hash,
    _phase_b1_case_family_for_message,
    _raw_stub_output,
)


ARTIFACT_PATH = ROOT / "artifacts" / "b1_pass2_manager_contract_diagnostic.json"
B1_003_CASE_ID = "B1-003"
CURRENT_VARIANT = "current"
TIGHTENED_VARIANT = "tightened_top_level_item_results"
DEFAULT_VARIANTS = (CURRENT_VARIANT, TIGHTENED_VARIANT)
DEFAULT_PROFILES = ("builderspace-deepseek-default", "builderspace-grok-4-fast-b1-pass2-probe")


@dataclass(frozen=True)
class Pass2Profile:
    profile_id: str
    model: str
    provider: str = "builderspace"
    role: str = "pass2_manager_contract_probe"
    production_selected: bool = False


PROFILES: dict[str, Pass2Profile] = {
    "builderspace-deepseek-default": Pass2Profile(
        profile_id="builderspace-deepseek-default",
        model="deepseek",
        role="default_build_loop_pass2_probe",
    ),
    "builderspace-grok-4-fast-b1-pass2-probe": Pass2Profile(
        profile_id="builderspace-grok-4-fast-b1-pass2-probe",
        model="grok-4-fast",
        role="low_cost_contract_probe",
    ),
}


class _Pass2DiagnosticAdapter(BuilderSpaceAdapter):
    def __init__(self, *, manager_model_override: str, schema_variant: str) -> None:
        super().__init__(manager_model_override=manager_model_override)
        self.schema_variant = schema_variant

    def _response_format_request_for_stage(
        self,
        stage: str,
        constraints: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        schema = response_schema_for_stage(stage, constraints)
        if self.schema_variant == TIGHTENED_VARIANT:
            schema = _tightened_top_level_item_results_schema(schema)
        return response_format_request_for_stage(stage, constraints=constraints, schema=schema)


def classify_pass2_probe_result(raw_result: dict[str, Any]) -> dict[str, Any]:
    result = dict(raw_result)
    trace = result.get("trace") if isinstance(result.get("trace"), dict) else {}
    parsed = result.get("parsed_object")
    if not isinstance(parsed, dict):
        parsed = trace.get("parsed_object") if isinstance(trace.get("parsed_object"), dict) else {}
    top_level_item_results = parsed.get("item_results")
    answer_contract = parsed.get("answer_contract") if isinstance(parsed.get("answer_contract"), dict) else {}
    answer_contract_item_results = answer_contract.get("item_results") if isinstance(answer_contract, dict) else None
    top_level_present = _has_non_empty_list(top_level_item_results)
    answer_contract_present = _has_non_empty_list(answer_contract_item_results)
    if top_level_present:
        item_results_source = "manager_pass_2_payload"
        item_results_owner_class = "runtime_payload"
    elif answer_contract_present:
        item_results_source = "answer_contract_bridge"
        item_results_owner_class = "compatibility_bridge"
    else:
        item_results_source = "none"
        item_results_owner_class = "none"
    failure_family = result.get("failure_family") or _failure_family(
        status=str(result.get("status") or ""),
        trace=trace,
        top_level_present=top_level_present,
        answer_contract_present=answer_contract_present,
    )
    result.update(
        {
            "failure_family": failure_family,
            "raw_payload_keys": sorted(parsed.keys()),
            "top_level_item_results_present": top_level_present,
            "answer_contract_item_results_present": answer_contract_present,
            "item_results_source": item_results_source,
            "item_results_owner_class": item_results_owner_class,
            "schema_validation_result": "accepted" if result.get("status") == "success" else "failed_or_not_reached",
            "bounded_repair_attempted": False,
            "runner_promoted_bridge_to_runtime_payload": False,
            "trace": _compact_trace(trace),
        }
    )
    return _json_safe(result)


def build_pass2_contract_artifact(
    *,
    results: list[dict[str, Any]],
    generated_at_utc: str,
) -> dict[str, Any]:
    classified_results = [classify_pass2_probe_result(result) for result in results]
    failure_families = sorted(
        {
            str(result.get("failure_family"))
            for result in classified_results
            if result.get("failure_family")
        }
    )
    artifact = {
        "artifact_type": "b1_pass2_manager_contract_diagnostic",
        "generated_at_utc": generated_at_utc,
        "current_mainline": "Wave 1 Manager-style Agent B1/B2 re-entry",
        "scope": "b1_pass2_manager_contract_diagnostic",
        "case_id": B1_003_CASE_ID,
        "provider": "builderspace",
        "live_llm_invoked": True,
        "tavily_live_invoked": False,
        "readiness_claimed": False,
        "not_b1_readiness_evidence": True,
        "semantic_owner": "manager_llm_structured_output",
        "deterministic_role": "validation_and_trace_classification_only",
        "runner_inferred_semantics": False,
        "bridge_promoted_to_runtime_truth": False,
        "best_practice_sources": [
            "https://developers.openai.com/api/docs/guides/function-calling",
            "https://developers.openai.com/api/docs/guides/structured-outputs",
            "https://developers.openai.com/api/docs/guides/evaluation-best-practices",
        ],
        "cases": classified_results,
        "summary": {
            "case_count": len(classified_results),
            "pass_count": sum(1 for result in classified_results if not result.get("failure_family")),
            "fail_count": sum(1 for result in classified_results if result.get("failure_family")),
            "failure_families": failure_families,
            "failure_family_counts": dict(Counter(str(result.get("failure_family")) for result in classified_results if result.get("failure_family"))),
            "root_cause": _root_cause(classified_results),
            "next_repair_hint": _next_repair_hint(classified_results),
        },
        "readiness_claim": build_readiness_claim(
            claim_scope="live_diagnostic",
            activation_stage="live_diagnostic",
            semantic_authority_source="live_manager_structured_output",
            producer_honesty={
                "runner_inferred_semantics": False,
                "fake_provider_simulated_manager": False,
                "final_mapping_fabricated": False,
                "mutation_fabricated": False,
                "readiness_overclaim_prevented": True,
                "bridge_promoted_to_runtime_truth": False,
            },
            evidence_lineage={
                "artifacts": ["artifacts/b1_pass2_manager_contract_diagnostic.json"],
                "producers": ["scripts/run_b1_pass2_manager_contract_diagnostic.py"],
                "not_b1_readiness_evidence": True,
            },
            allowed_next_stage=None,
            forbidden_claims=["b1_ready", "b2_ready", "product_ready", "mutation_ready"],
            readiness_claimed=False,
        ),
    }
    return _json_safe(artifact)


async def run_pass2_contract_diagnostic(
    *,
    profile_ids: list[str],
    variants: list[str],
    output_path: Path,
    write_latest: bool = True,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for profile_id in profile_ids:
        profile = PROFILES[profile_id]
        for variant in variants:
            results.append(await _run_single_probe(profile=profile, variant=variant))
    artifact = build_pass2_contract_artifact(
        results=results,
        generated_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    specific_path = _specific_artifact_path(output_path)
    specific_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    artifact["artifact_path"] = _project_relative(specific_path)
    specific_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    if write_latest:
        output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return artifact


async def _run_single_probe(*, profile: Pass2Profile, variant: str) -> dict[str, Any]:
    case_id = B1_003_CASE_ID
    message = str(CORE_SMOKE_CASE_MAP[case_id])
    case_family = _phase_b1_case_family_for_message(message)
    constraints = {
        "phase": "B-1",
        "scope": "b1_pass2_manager_contract_diagnostic",
        "manager_pass_contract": "pass1_requests_tools_pass2_synthesizes",
        "phase_b1_case_id": case_id,
        "phase_b1_manager_role": "pass_2_synthesis",
        "phase_b1_pass1_mode": NATURAL_MODE,
        "phase_b1_case_family": case_family,
        "phase_b1_task_payload_id": "phase_b1_pass_2_common_commercial_meal_contract_probe",
        "phase_b1_pass2_prompt_variant": variant,
        "phase_b1_pass2_schema_variant": variant,
    }
    packets = _packetizer_outputs(case_id=case_id, message=message)
    adapter = _Pass2DiagnosticAdapter(manager_model_override=profile.model, schema_variant=variant)
    raw_result: dict[str, Any] = {
        "case_id": case_id,
        "input_message": message,
        "case_family": case_family,
        "profile_id": profile.profile_id,
        "profile_role": profile.role,
        "provider": profile.provider,
        "model": profile.model,
        "production_selected": profile.production_selected,
        "prompt_variant": variant,
        "schema_variant": variant,
        "status": "not_run",
        "bounded_repair_attempted": False,
    }
    try:
        parsed, trace = await adapter.complete_with_trace(
            system_prompt=f"{_pass2_prompt(variant)}\n\n{SINGLE_MANAGER_SYSTEM_PROMPT}",
            user_payload={
                "raw_user_input": message,
                "round_index": 1,
                "tool_results": [
                    {
                        "tool_name": "packetize_food_evidence",
                        "truth_level": "hint",
                        "packetizer_outputs": _json_safe(packets),
                    }
                ],
                "constraints": constraints,
                "pass2_contract_diagnostic": True,
            },
            stage=MANAGER_LOOP_STAGE,
            max_tokens=900,
        )
        raw_result.update({"status": "success", "parsed_object": parsed, "trace": trace})
    except BuilderSpaceResponseError as exc:
        raw_result.update({"status": "error", "error": str(exc), "trace": dict(exc.trace or {})})
    except Exception as exc:
        raw_result.update(
            {
                "status": "error",
                "error": str(exc),
                "trace": {
                    "failure_family": "provider_runtime_or_transport_blocker",
                    "error_type": type(exc).__name__,
                    "raw_response_excerpt": getattr(exc, "raw_response_excerpt", None),
                },
            }
        )
    return classify_pass2_probe_result(raw_result)


def _pass2_prompt(variant: str) -> str:
    if variant == TIGHTENED_VARIANT:
        return (
            "Phase B-1 common-commercial-meal Pass 2 top-level item_results diagnostic mode.\n"
            "This is Manager Pass 2: consume packetized tool_results only and return manager_action='final'.\n"
            "Output exactly one compact JSON object.\n"
            "The first non-whitespace character of your response must be '{'.\n"
            "Do not write evidence essay, markdown, or fenced code.\n"
            "Required result surface: top-level item_results.\n"
            "Do not put item_results, kcal_range, likely_kcal, uncertainty, or evidence_used inside answer_contract.\n"
            "Use answer_contract={}.\n"
            "Retain response_mode, intent, workflow_effect, target_attachment, exactness, confidence, evidence_posture, repair_ack, and operations.\n"
            "Use operations=[].\n"
            "Do not output mutation_result, ledger_delta, canonical_ledger_entry, or renderer final response.\n"
            "Compact JSON example:\n"
            "{\"manager_action\":\"final\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"intent\":\"estimate_calories\",\"workflow_effect\":\"complete\",\"target_attachment\":{\"kind\":\"common_commercial_meal\"},\"exactness\":\"approximate\",\"confidence\":\"medium\",\"evidence_posture\":\"packetized_generic_db\",\"repair_ack\":false,\"item_results\":[{\"food_name\":\"bento\",\"kcal_range\":[550,960],\"likely_kcal\":750,\"uncertainty\":\"medium\",\"evidence_used\":[\"generic_food_db:bento\"]}],\"operations\":[],\"answer_contract\":{}}"
        )
    return PASS_2_COMMON_COMMERCIAL_MEAL_COMPACT_JSON_FIRST_PAYLOAD


def _tightened_top_level_item_results_schema(schema: dict[str, Any] | None) -> dict[str, Any] | None:
    if schema is None:
        return None
    tightened = deepcopy(schema)
    required = list(tightened.get("required") or [])
    if "item_results" not in required:
        required.append("item_results")
    tightened["required"] = required
    properties = tightened.setdefault("properties", {})
    properties["answer_contract"] = {"type": "object"}
    return tightened


def _packetizer_outputs(*, case_id: str, message: str) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for food_name in _food_names_for_message(message):
        tool_name = "lookup_generic_food"
        _raw_stub_output(case_id=case_id, tool_name=tool_name, food_name=food_name)
        packets.append(_fixture_packet(case_id=case_id, tool_name=tool_name, food_name=food_name))
    return packets


def _failure_family(
    *,
    status: str,
    trace: dict[str, Any],
    top_level_present: bool,
    answer_contract_present: bool,
) -> str | None:
    trace_family = trace.get("failure_family") or trace.get("request_failure_family")
    if status == "error":
        return str(trace_family or "provider_runtime_or_transport_blocker")
    if top_level_present:
        return None
    if answer_contract_present:
        return "answer_contract_bridge_item_results"
    return "pass2_no_item_results"


def _root_cause(results: list[dict[str, Any]]) -> str:
    current_deepseek = _first_result(results, model="deepseek", variant=CURRENT_VARIANT)
    current_grok = _first_result(results, model="grok-4-fast", variant=CURRENT_VARIANT)
    tightened = [item for item in results if item.get("prompt_variant") == TIGHTENED_VARIANT]
    if any(item.get("status") == "error" for item in results):
        return "provider_runtime_or_transport_blocker"
    if current_deepseek and current_grok:
        if not current_deepseek.get("top_level_item_results_present") and current_grok.get("top_level_item_results_present"):
            return "deepseek_pass2_contract_non_adherence"
        if (
            current_deepseek.get("item_results_source") == "answer_contract_bridge"
            and current_grok.get("item_results_source") == "answer_contract_bridge"
        ):
            if tightened and any(item.get("top_level_item_results_present") for item in tightened):
                return "pass2_prompt_contract_mismatch"
            if tightened and all(item.get("item_results_source") == "answer_contract_bridge" for item in tightened):
                return "schema_not_enforced_or_provider_contract_gap"
            return "pass2_prompt_contract_mismatch"
    if any(item.get("top_level_item_results_present") for item in results) and any(
        item.get("item_results_source") == "answer_contract_bridge" for item in results
    ):
        return "mixed_model_or_prompt_contract_behavior"
    if all(not item.get("top_level_item_results_present") for item in results):
        return "pass2_no_runtime_owned_item_results"
    return "unknown"


def _next_repair_hint(results: list[dict[str, Any]]) -> str:
    root_cause = _root_cause(results)
    hints = {
        "deepseek_pass2_contract_non_adherence": "add explicit B1 Pass 2 GrokFast diagnostic profile; do not globally switch provider",
        "pass2_prompt_contract_mismatch": "tighten common-commercial-meal Pass 2 prompt/schema to require top-level item_results",
        "schema_not_enforced_or_provider_contract_gap": "add bounded repair or provider/profile route; do not accept bridge output as readiness",
        "provider_runtime_or_transport_blocker": "inspect provider trace before B1/B2 readiness",
        "pass2_no_runtime_owned_item_results": "repair Pass 2 manager contract surface before readiness",
    }
    return hints.get(root_cause, "inspect diagnostic cases before runtime repair")


def _first_result(results: list[dict[str, Any]], *, model: str, variant: str) -> dict[str, Any] | None:
    for result in results:
        if result.get("model") == model and result.get("prompt_variant") == variant:
            return result
    return None


def _has_non_empty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _compact_trace(trace: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "provider",
        "model",
        "response_status",
        "failure_family",
        "request_failure_family",
        "failing_component",
        "structured_output_transport_attempted",
        "structured_output_transport_mode",
        "structured_output_transport_accepted",
        "structured_output_transport_fallback",
        "fallback_reason",
        "effective_response_format_type",
        "raw_response_excerpt",
        "raw_content_excerpt",
        "transport_attempts",
        "parse_attempts",
        "request_payload",
    )
    return {key: _json_safe(trace.get(key)) for key in keys if key in trace}


def _specific_artifact_path(output_path: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    return output_path.with_name(f"{output_path.stem}_{timestamp}_{uuid4().hex[:6]}{output_path.suffix}")


def _project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _parse_csv(value: str | None, *, default: tuple[str, ...]) -> list[str]:
    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


async def _async_main() -> int:
    parser = argparse.ArgumentParser(description="Run the B1 Pass 2 manager contract diagnostic.")
    parser.add_argument("--profiles", default=",".join(DEFAULT_PROFILES), help="Comma-separated provider profile IDs.")
    parser.add_argument("--variants", default=",".join(DEFAULT_VARIANTS), help="Comma-separated prompt/schema variants.")
    parser.add_argument("--output-path", default=str(ARTIFACT_PATH), help="Latest artifact output path.")
    parser.add_argument("--no-latest", action="store_true", help="Only write the timestamped artifact.")
    args = parser.parse_args()

    profile_ids = _parse_csv(args.profiles, default=DEFAULT_PROFILES)
    variants = _parse_csv(args.variants, default=DEFAULT_VARIANTS)
    unknown_profiles = [profile_id for profile_id in profile_ids if profile_id not in PROFILES]
    unknown_variants = [variant for variant in variants if variant not in DEFAULT_VARIANTS]
    if unknown_profiles or unknown_variants:
        raise SystemExit(
            json.dumps(
                {
                    "unknown_profiles": unknown_profiles,
                    "unknown_variants": unknown_variants,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    artifact = await run_pass2_contract_diagnostic(
        profile_ids=profile_ids,
        variants=variants,
        output_path=Path(args.output_path),
        write_latest=not args.no_latest,
    )
    print(
        json.dumps(
            {
                "artifact_path": artifact.get("artifact_path"),
                "case_count": artifact["summary"]["case_count"],
                "failure_families": artifact["summary"]["failure_families"],
                "root_cause": artifact["summary"]["root_cause"],
                "next_repair_hint": artifact["summary"]["next_repair_hint"],
                "readiness_claimed": artifact["readiness_claimed"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> int:
    return asyncio.run(_async_main())


if __name__ == "__main__":
    raise SystemExit(main())
