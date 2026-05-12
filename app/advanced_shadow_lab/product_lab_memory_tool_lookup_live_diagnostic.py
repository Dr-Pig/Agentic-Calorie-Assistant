from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.advanced_shadow_lab.product_lab_memory_tool_lookup_artifact import (
    base_tool_lookup_artifact,
    finalize_tool_lookup_artifact,
    provider_review_blockers,
    provider_review_summary,
    tool_observation_blockers,
    trace_summary,
)
from app.advanced_shadow_lab.product_lab_memory_tool_lookup_fixtures import (
    FakeMemoryToolLookupProvider,
    SCOPE_KEYS,
    STAGE,
    memory_tool_lookup_records,
    memory_tool_lookup_sources,
)
from app.memory.application.memory_tool_facade import execute_memory_tool_call
from app.shared.infra.json_artifacts import write_json_artifact


SYSTEM_PROMPT = (
    "Return JSON only for a memory tool lookup diagnostic. Inspect the observed "
    "tool sequence and compact tool outputs. Return memory_record_first, "
    "bounded_source_drilldown_used, raw_transcript_requested, "
    "full_raw_transcript_included, prompt_material_followed, answer_summary, "
    "risk_notes, and claim_scope. The correct path reads MemoryRecord summaries "
    "before source evidence, uses bounded source spans only for why-memory or "
    "debug review, and never requests raw transcript text."
)


def run_memory_tool_lookup_live_diagnostic(
    *,
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    tool_observation = _tool_observation()
    provider_invoked = False
    provider_error: dict[str, Any] = {}
    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    try:
        provider_invoked = True
        provider_result, provider_trace = asyncio.run(
            _invoke_provider(provider, tool_observation)
        )
    except Exception as exc:
        provider_error = {"type": type(exc).__name__, "message": str(exc)[:300]}

    blockers = (
        tool_observation_blockers(tool_observation)
        if provider_error
        else [
            *tool_observation_blockers(tool_observation),
            *provider_review_blockers(provider_result),
        ]
    )
    status = "provider_error" if provider_error else "blocked" if blockers else "pass"
    artifact = base_tool_lookup_artifact(
        status=status,
        provider_mode=provider_mode,
        provider_profile_id=provider_profile_id,
        live_invoked=live_invoked,
        provider_invoked=provider_invoked,
        tool_observation=tool_observation,
    )
    artifact.update(
        {
            "provider_readiness": _mapping(provider.readiness())
            if hasattr(provider, "readiness")
            else {},
            "provider_trace_summary": trace_summary(provider_trace),
            "provider_error": provider_error,
            "provider_review_summary": provider_review_summary(provider_result),
            "blockers": blockers,
        }
    )
    finalize_tool_lookup_artifact(artifact)
    if output_path:
        write_json_artifact(output_path, artifact)
    return artifact


async def _invoke_provider(
    provider: Any, tool_observation: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload=_provider_payload(tool_observation),
        stage=STAGE,
        max_tokens=1200,
    )
    return _mapping(result), _mapping(trace)


def _tool_observation() -> dict[str, Any]:
    search = execute_memory_tool_call(
        tool_name="memory.search",
        arguments={
            "scope_keys": SCOPE_KEYS,
            "consumer": "recommendation_shadow",
            "limit": 3,
        },
        memory_records=memory_tool_lookup_records(),
    )
    source_lookup = execute_memory_tool_call(
        tool_name="memory.source_lookup",
        arguments={
            "scope_keys": SCOPE_KEYS,
            "source_refs": _source_refs_from_search(search),
            "tool_path": "why_memory",
            "max_evidence_chars": 96,
        },
        memory_records=[],
        source_entries=memory_tool_lookup_sources(),
    )
    return {
        "tool_sequence": ["memory.search", "memory.source_lookup"],
        "search": search,
        "source_lookup": source_lookup,
    }


def _provider_payload(tool_observation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "target_surface": "advanced_product_lab_memory_tool_lookup_live_diagnostic",
        "user_query": "Why is spicy food blocked in recommendations?",
        "allowed_tools": ["memory.search", "memory.source_lookup"],
        "observed_tool_sequence": list(tool_observation.get("tool_sequence") or []),
        "memory_search_observation": _mapping(tool_observation.get("search")),
        "source_lookup_observation": _mapping(tool_observation.get("source_lookup")),
        "output_contract": {
            "memory_record_first_must_be_true": True,
            "bounded_source_drilldown_used_must_be_true": True,
            "raw_transcript_requested_must_be_false": True,
            "full_raw_transcript_included_must_be_false": True,
            "prompt_material_followed_must_be_false": True,
        },
        "constraints": {
            "claim_scope_required": "diagnostic_only",
            "durable_memory_write_allowed": False,
            "canonical_mutation_allowed": False,
            "raw_transcript_retrieval_allowed": False,
        },
    }


def _source_refs_from_search(search: Mapping[str, Any]) -> list[str]:
    return [
        str(ref)
        for record in search.get("records") or []
        if isinstance(record, Mapping)
        for ref in record.get("source_refs") or []
        if ref
    ]


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "FakeMemoryToolLookupProvider",
    "run_memory_tool_lookup_live_diagnostic",
]
