from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction_artifact import (
    base_extraction_artifact,
    empty_grade_summary,
    finalize_extraction_live_status,
    model_output_summary,
    trace_summary,
)
from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction_cases import (
    memory_record_grokfast_extraction_provider_payload,
)
from app.advanced_shadow_lab.product_lab_memory_record_grokfast_extraction_grade import (
    grade_memory_record_grokfast_extraction,
)
from app.shared.infra.json_artifacts import write_json_artifact


STAGE = "advanced_product_lab_memory_record_grokfast_extraction"
SYSTEM_PROMPT = (
    "Return JSON only for a MemoryRecord extraction diagnostic. For each case, "
    "return case_id, candidate_type, polarity, strength, promotion_allowed_now, "
    "human_review_required, rejection_reason, source_refs, and reasoning_notes. "
    "Use the exact allowed enum values from output_contract; map stable positive "
    "preferences to candidate_type=preference and strength=boost. "
    "For negative dislikes, use candidate_type=negative_preference and "
    "polarity=negative; use strength=block only for absolute exclusions and "
    "strength=downrank for softer dislikes. If the user says not to remember a "
    "subject or reverses the memory request, return candidate_type=none and a "
    "non-empty rejection_reason. "
    "Do not confirm durable memory, mutate product truth, schedule delivery, or "
    "claim product readiness."
)


def run_memory_record_grokfast_extraction_diagnostic(
    *,
    cases: list[Mapping[str, Any]],
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
    case_suite: str = "golden",
) -> dict[str, Any]:
    provider_result: dict[str, Any] = {"case_results": []}
    provider_traces: list[dict[str, Any]] = []
    provider_error: dict[str, Any] = {}
    provider_invoked = False
    for case in cases:
        try:
            provider_invoked = True
            case_result, case_trace = asyncio.run(_invoke_provider(provider, [case]))
            provider_result["case_results"].extend(_case_results(case_result))
            provider_traces.append(case_trace)
        except Exception as exc:
            provider_error = {
                "case_id": str(case.get("case_id") or ""),
                "type": type(exc).__name__,
                "message": str(exc)[:300],
            }
            break
    grade = (
        {"summary": empty_grade_summary(cases), "case_reports": [], "blockers": []}
        if provider_error
        else grade_memory_record_grokfast_extraction(
            cases=cases,
            provider_result=provider_result,
        )
    )
    blockers = list(grade["blockers"])
    status = "provider_error" if provider_error else "blocked" if blockers else "pass"
    artifact = base_extraction_artifact(
        status=status,
        cases=cases,
        provider_mode=provider_mode,
        provider_profile_id=provider_profile_id,
        live_invoked=live_invoked,
        case_suite=case_suite,
    )
    artifact.update(
        {
            "provider_invoked": provider_invoked,
            "live_provider_used": bool(live_invoked and provider_invoked),
            "provider_readiness": _mapping(provider.readiness())
            if hasattr(provider, "readiness")
            else {},
            "provider_trace_summary": trace_summary(provider_traces),
            "provider_error": provider_error,
            "model_output_summary": model_output_summary(provider_result),
            "case_reports": grade["case_reports"],
            "grader_summary": grade["summary"],
            "blockers": blockers,
        }
    )
    finalize_extraction_live_status(artifact)
    if output_path:
        write_json_artifact(output_path, artifact)
    return artifact


def blocked_not_invoked_extraction_artifact(
    *,
    reason: str,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
    case_suite: str = "golden",
) -> dict[str, Any]:
    artifact = base_extraction_artifact(
        status="blocked",
        cases=[],
        provider_mode="not_invoked",
        provider_profile_id=provider_profile_id,
        live_invoked=False,
        case_suite=case_suite,
    )
    artifact.update(
        {
            "provider_invoked": False,
            "live_provider_used": False,
            "provider_readiness": {},
            "provider_trace_summary": {"stage": "not_invoked", "provider": "not_invoked"},
            "provider_error": {},
            "model_output_summary": {},
            "case_reports": [],
            "grader_summary": empty_grade_summary([]),
            "blockers": [reason],
        }
    )
    finalize_extraction_live_status(artifact)
    if output_path:
        write_json_artifact(output_path, artifact)
    return artifact


async def _invoke_provider(
    provider: Any,
    cases: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload=memory_record_grokfast_extraction_provider_payload(
            cases,
            constraints={
                "claim_scope_required": "diagnostic_only",
                "semantic_hardening_allowed": False,
                "durable_memory_write_allowed": False,
            },
        ),
        stage=STAGE,
        max_tokens=1600,
    )
    return _mapping(result), _mapping(trace)


def _case_results(provider_result: Mapping[str, Any]) -> list[dict[str, Any]]:
    case_results = provider_result.get("case_results")
    if isinstance(case_results, list):
        return [dict(item) for item in case_results if isinstance(item, Mapping)]
    if provider_result.get("case_id"):
        return [dict(provider_result)]
    return []


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
