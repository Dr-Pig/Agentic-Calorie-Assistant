from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.consumer_context_packs import (
    _consumer_context_packs,
)
from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _context_pack_token_pressure_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    target_window = int(fixture.get("target_context_window_tokens") or 8192)
    packs = _long_term_context_pack_shadow_artifact(fixture, candidates)[
        "context_packs"
    ]
    return _base_artifact(
        artifact_type="context_pack_token_pressure_shadow_eval",
        fixture=fixture,
        extra={
            "source_spec": "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
            "runtime_effect_allowed": False,
            "target_context_window_tokens": target_window,
            "token_pressure_policy": {
                "general_compaction_threshold": 0.6,
                "aggressive_compaction_threshold": 0.8,
                "forced_trim_threshold": 0.9,
            },
            "prune_order": [
                "long_transcript",
                "raw_historical_records",
                "low_value_explanation_text",
                "non_essential_fallback_metadata",
            ],
            "preserve_first": [
                "current_task_object",
                "active_shared_views",
                "safety_guardrails",
                "schema_binding_context",
                "atomic_context_blocks",
            ],
            "atomic_blocks_split_allowed": False,
            "evaluated_packs": [
                _token_pressure_pack_eval(pack, target_window)
                for pack in packs.values()
            ],
        },
    )


def _token_pressure_pack_eval(
    pack: dict[str, Any],
    target_window: int,
) -> dict[str, Any]:
    estimated_tokens = int(pack.get("token_estimate") or 0)
    ratio = estimated_tokens / target_window if target_window > 0 else 0.0
    return {
        "pack_id": pack["pack_id"],
        "estimated_tokens": estimated_tokens,
        "target_context_window_tokens": target_window,
        "pressure_ratio": round(ratio, 4),
        "pressure_level": _token_pressure_level(ratio),
        "summary_first": pack["summary_first"],
        "structured_state_first": pack["structured_state_first"],
        "raw_full_history_dumped": pack["raw_full_history_dumped"],
        "recommended_shadow_action": _token_pressure_action(ratio),
        "runtime_effect_allowed": False,
    }


def _token_pressure_level(ratio: float) -> str:
    if ratio >= 0.9:
        return "forced_trim"
    if ratio >= 0.8:
        return "aggressive_compaction"
    if ratio >= 0.6:
        return "general_compaction"
    return "below_threshold"


def _token_pressure_action(ratio: float) -> str:
    if ratio >= 0.9:
        return "trim_low_priority_blocks_shadow_only"
    if ratio >= 0.8:
        return "aggressively_summarize_shadow_only"
    if ratio >= 0.6:
        return "summarize_non_atomic_blocks_shadow_only"
    return "keep_pack_shape"


def _long_term_context_pack_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="long_term_context_pack_shadow_eval",
        fixture=fixture,
        extra={
            "runtime_context_loaded": False,
            "manager_context_packet_written": False,
            "manager_context_packet_injection_allowed": False,
            "summary_first": True,
            "structured_state_first": True,
            "context_packs": _consumer_context_packs(candidates),
        },
    )


__all__ = [
    "_context_pack_token_pressure_shadow_artifact",
    "_long_term_context_pack_shadow_artifact",
]
