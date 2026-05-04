from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.utils import (
    _conversation_summary_preview,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _conversation_recall_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    recall_candidates = [
        candidate
        for candidate in candidates
        if candidate.candidate_type == "conversation_recall_context"
    ]
    selected = [
        {
            "candidate_id": candidate.candidate_id,
            "candidate_type": candidate.candidate_type,
            "source_trace_ids": candidate.source_trace_ids,
            "source_object_refs": candidate.source_object_refs,
            "summary_preview": _conversation_summary_preview(candidate),
            "would_load_full_history": False,
            "manager_tool_call_allowed": False,
            "runtime_effect_allowed": False,
        }
        for candidate in recall_candidates
    ]
    return _base_artifact(
        artifact_type="conversation_recall_shadow_eval",
        fixture=fixture,
        extra={
            "summary_first": True,
            "raw_transcript_included": False,
            "retrieval_tool_called": False,
            "manager_tool_call_allowed": False,
            "selected_context_candidates": selected,
            "rejected_context_candidates": [],
            "omission_trace": {
                "raw_transcript_omitted": True,
                "full_history_dump_omitted": True,
                "runtime_packet_injection_omitted": True,
            },
        },
    )


def _conversation_recall_tool_shadow_plan_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    recall_candidates = [
        candidate
        for candidate in candidates
        if candidate.candidate_type == "conversation_recall_context"
    ]
    selected_refs = [
        {
            "candidate_id": candidate.candidate_id,
            "candidate_type": candidate.candidate_type,
            "source_trace_ids": candidate.source_trace_ids,
            "source_object_refs": candidate.source_object_refs,
            "summary_preview": _conversation_summary_preview(candidate),
            "freshness_posture": candidate.freshness_posture,
            "confidence": candidate.confidence,
            "raw_transcript_returned": False,
            "runtime_effect_allowed": False,
        }
        for candidate in recall_candidates
    ]
    return _base_artifact(
        artifact_type="conversation_recall_tool_shadow_plan",
        fixture=fixture,
        extra={
            "context_entry_mode": "future_tool_mediated_retrieval_candidate",
            "manager_tool_registered": False,
            "manager_tool_called": False,
            "runtime_tool_available": False,
            "retrieval_tool_call_allowed_now": False,
            "raw_transcript_access_allowed_now": False,
            "runtime_effect_allowed": False,
            "future_tool_contract": {
                "tool_name": "conversation_recall.search",
                "tool_owner": "future_manager_context_retrieval",
                "request_schema": {
                    "required": [
                        "user_id",
                        "retrieval_query",
                        "scope",
                        "reason_for_recall",
                    ],
                    "properties": {
                        "user_id": "stable scoped user identifier",
                        "retrieval_query": "natural-language recall need",
                        "scope": "project/session/surface boundary",
                        "reason_for_recall": "why current turn needs old context",
                        "time_window": "optional bounded date range",
                        "max_summaries": "optional cap; default future tool should stay small",
                        "raw_transcript_allowed": "must remain false by default",
                    },
                },
                "response_contract": {
                    "summary_first": True,
                    "structured_state_first": True,
                    "source_refs_required": True,
                    "freshness_required": True,
                    "omission_trace_required": True,
                    "raw_transcript_returned": False,
                    "manager_context_injection_allowed": False,
                },
            },
            "selected_conversation_refs": selected_refs,
            "safety_boundaries": [
                "ManagerContextPacket injection remains forbidden",
                "No raw transcript dump",
                "No durable memory write",
                "No runtime tool registration",
                "No provider or embedding call",
            ],
            "omission_trace": {
                "raw_transcript_omitted": True,
                "full_history_dump_omitted": True,
                "manager_tool_registration_omitted": True,
                "runtime_packet_injection_omitted": True,
            },
        },
    )


def _conversation_recall_retrieval_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    recall_candidates = [
        candidate
        for candidate in candidates
        if candidate.candidate_type == "conversation_recall_context"
    ]
    ranked = [
        {
            "rank": index + 1,
            "candidate_id": candidate.candidate_id,
            "candidate_type": candidate.candidate_type,
            "source_class": "conversation_history_summary",
            "retrieval_mode": "metadata_scope_filter",
            "scope_keys": candidate.scope_keys,
            "freshness_posture": candidate.freshness_posture,
            "source_trace_ids": candidate.source_trace_ids,
            "source_object_refs": candidate.source_object_refs,
            "summary_preview": _conversation_summary_preview(candidate),
            "raw_transcript_returned": False,
            "would_load_full_history": False,
            "runtime_effect_allowed": False,
        }
        for index, candidate in enumerate(
            sorted(
                recall_candidates,
                key=lambda item: (-item.confidence, item.candidate_id),
            )
        )
    ]
    return _base_artifact(
        artifact_type="conversation_recall_retrieval_shadow_eval",
        fixture=fixture,
        extra={
            "source_spec": "docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md",
            "summary_first": True,
            "retrieval_tool_registered": False,
            "retrieval_tool_called": False,
            "manager_tool_call_allowed": False,
            "live_vector_search_used": False,
            "raw_transcript_returned": False,
            "source_classes": [
                "conversation_history_summary",
                "memory_candidate_review_artifact",
            ],
            "routing_policy": {
                "deterministic_scope_filter_first": True,
                "metadata_filter_before_semantic_search": True,
                "full_document_read_fallback_allowed": False,
                "stale_result_requires_review": True,
            },
            "ranked_results": ranked,
            "negative_cases": [
                {
                    "case_id": "missing_user_scope",
                    "retrieval_allowed": False,
                    "reason": "scope_keys_required_before_recall",
                },
                {
                    "case_id": "raw_transcript_request",
                    "retrieval_allowed": False,
                    "reason": "summary_first_shadow_lab_forbids_raw_transcript",
                },
            ],
        },
    )
