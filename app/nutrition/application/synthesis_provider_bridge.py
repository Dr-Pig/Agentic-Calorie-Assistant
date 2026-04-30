from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from typing import Any, Protocol

from app.runtime.contracts.trace import MANAGER_LOOP_STAGE

from .evidence_packet_consumption import EvidencePacketConsumptionResult
from .retrieval_intent import RetrievalIntent
from .small_anchor_store import GenericClarifySupport

SYNTHESIS_MANAGER_PASS_ROLE = "pass_2_synthesis"
SYNTHESIS_TASK_PAYLOAD_ID = "nutrition_synthesis_provider_seam_audit_v1"
SYNTHESIS_INPUT_CONTRACT_VERSION = "evidence_packet_consumption_v1"
SYNTHESIS_PROMPT_MARKER = "nutrition_synthesis_provider_seam_audit_v1"
PASS_2_FORBIDDEN_MUTATION_FIELDS = (
    "mutation_result",
    "ledger_delta",
    "canonical_ledger_entry",
)
PROVIDER_PARAM_KEYS = (
    "provider",
    "model",
    "temperature",
    "max_tokens",
    "response_format",
    "timeout",
    "retry_policy",
    "tool_choice",
    "request_id",
)


class SynthesisPassProvider(Protocol):
    async def complete_with_trace(self, **kwargs: Any) -> tuple[object, dict[str, object]]: ...


def build_synthesis_manager_request_payload(
    intent: RetrievalIntent,
    consumption: EvidencePacketConsumptionResult,
    *,
    clarify_support: GenericClarifySupport | None = None,
) -> dict[str, object]:
    return {
        "intent": _json_safe(asdict(intent)),
        "accepted_packets": _json_safe([dict(packet) for packet in consumption.accepted_packets]),
        "rejected_candidates": _json_safe([dict(candidate) for candidate in consumption.rejected_candidates]),
        "clarify_support": _json_safe(asdict(clarify_support)) if clarify_support is not None else None,
        "query_only": intent.retrieval_goal == "query_only_answer",
        "mutation_forbidden": True,
        "round_index": 1,
        "constraints": {
            "synthesis_manager_role": SYNTHESIS_MANAGER_PASS_ROLE,
            "synthesis_retrieval_goal": intent.retrieval_goal,
            "synthesis_task_payload_id": SYNTHESIS_TASK_PAYLOAD_ID,
            "synthesis_input_contract_version": SYNTHESIS_INPUT_CONTRACT_VERSION,
        },
    }


async def run_synthesis_manager_with_provider(
    provider: SynthesisPassProvider,
    intent: RetrievalIntent,
    consumption: EvidencePacketConsumptionResult,
    *,
    clarify_support: GenericClarifySupport | None = None,
    max_tokens: int = 900,
) -> dict[str, object]:
    request_payload = build_synthesis_manager_request_payload(
        intent,
        consumption,
        clarify_support=clarify_support,
    )
    payload, trace = await provider.complete_with_trace(
        system_prompt=SYNTHESIS_PROMPT_MARKER,
        user_payload=request_payload,
        stage=MANAGER_LOOP_STAGE,
        max_tokens=max_tokens,
    )
    trace_dict = trace if isinstance(trace, dict) else {}
    payload_shape_valid = isinstance(payload, dict)
    payload_dict = payload if isinstance(payload, dict) else {}
    item_results = _item_results_from_provider_payload(payload_dict)
    return {
        "manager_round": 1,
        "manager_role": SYNTHESIS_MANAGER_PASS_ROLE,
        "prompt_hash": hashlib.sha256(SYNTHESIS_PROMPT_MARKER.encode("utf-8")).hexdigest(),
        "started_at_utc": trace_dict.get("started_at_utc"),
        "ended_at_utc": trace_dict.get("ended_at_utc"),
        "latency_ms": trace_dict.get("latency_ms"),
        "usage": _json_safe(trace_dict.get("usage")) if trace_dict.get("usage") is not None else None,
        "provider_params": _provider_params(trace_dict),
        "synthesis_task_payload_id": SYNTHESIS_TASK_PAYLOAD_ID,
        "decision_payload_type": _observed_type_name(payload),
        "payload_shape_valid": payload_shape_valid,
        "payload_shape_error": None if payload_shape_valid else "manager_pass_2_payload_must_be_object",
        "item_results": item_results,
        "item_results_source": "manager_pass_2_payload" if item_results else "none",
        "item_results_owner_class": "runtime_payload" if item_results else "none",
        "mutation_attempted": False,
        "mutation_authority": False,
        "ledger_truth_authority": False,
        "source_priority_authority": False,
        "product_semantic_authority": False,
        "forbidden_mutation_fields_present": _forbidden_mutation_fields(payload_dict),
    }


def _forbidden_mutation_fields(payload: dict[str, object]) -> list[str]:
    return [field for field in PASS_2_FORBIDDEN_MUTATION_FIELDS if field in payload]


def _item_results_from_provider_payload(payload: dict[str, object]) -> list[dict[str, object]]:
    raw_item_results = payload.get("item_results")
    if not isinstance(raw_item_results, list):
        return []
    return [_json_safe(dict(item)) for item in raw_item_results if isinstance(item, dict)]


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _observed_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, tuple):
        return "tuple"
    return type(value).__name__


def _provider_params(trace: dict[str, object]) -> dict[str, object]:
    return {key: trace.get(key) for key in PROVIDER_PARAM_KEYS}


__all__ = [
    "SYNTHESIS_MANAGER_PASS_ROLE",
    "SYNTHESIS_INPUT_CONTRACT_VERSION",
    "SYNTHESIS_TASK_PAYLOAD_ID",
    "SynthesisPassProvider",
    "build_synthesis_manager_request_payload",
    "run_synthesis_manager_with_provider",
]
