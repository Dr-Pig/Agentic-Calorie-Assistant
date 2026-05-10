from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.proactive_copy_live_policy import (
    ARTIFACT_TYPE,
    FALSE_FLAGS,
    NON_CLAIMS,
    STAGE,
    SYSTEM_PROMPT,
    control_summary,
    input_blockers,
    mapping,
    model_output_summary,
    output_guard,
    provider_payload,
    records,
    trace_summary,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.proactive_copy_live_diagnostic"
)


def run_proactive_copy_live_diagnostic(
    *,
    no_send_review_sink: Mapping[str, Any],
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    output_path: Path | None = None,
) -> dict[str, Any]:
    sink_records = records(no_send_review_sink)
    blockers = input_blockers(no_send_review_sink, sink_records)
    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    provider_invoked = False
    if not blockers:
        provider_invoked = True
        provider_result, provider_trace = asyncio.run(
            _invoke_provider(provider, no_send_review_sink, sink_records)
        )
    guard = {"status": "not_run", "blockers": []} if blockers else output_guard(provider_result)
    blockers = [*blockers, *guard["blockers"]]
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab",
        "consumer": "future_advanced_shadow_comparison_or_proactive_quality_review",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "target_surface": "proactive_chat_copy_posture",
        "source_review_sink_artifact_type": no_send_review_sink.get("artifact_type"),
        "source_record_count": len(sink_records),
        "control_path_summary": control_summary(no_send_review_sink),
        "provider_mode": str(provider_mode),
        "live_invoked": bool(live_invoked),
        "live_provider_used": bool(live_invoked and provider_invoked),
        "provider_invoked": provider_invoked,
        "provider_readiness": mapping(provider.readiness()) if hasattr(provider, "readiness") else {},
        "provider_trace_summary": trace_summary(provider_trace),
        "model_output_summary": model_output_summary(provider_result),
        "output_guard": guard,
        "blockers": blockers,
        "runtime_connected": False,
        "runtime_truth_changed": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return artifact


async def _invoke_provider(
    provider: Any,
    sink: Mapping[str, Any],
    sink_records: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload=provider_payload(sink, sink_records),
        stage=STAGE,
        max_tokens=600,
    )
    return mapping(payload), mapping(trace)


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_proactive_copy_live_diagnostic"]
