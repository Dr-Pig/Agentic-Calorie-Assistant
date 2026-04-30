from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .retrieval_intent import RetrievalIntent

B2SourcePath = Literal["exact_db", "generic_anchor", "listed_item_fanout", "ask_user"]
B2EvidenceRequired = Literal[
    "exact_item_card",
    "generic_anchor_packet",
    "generic_anchor_packet_per_listed_item",
    "clarify_support",
]
B2ProductPolicyStatus = Literal["source_selection_only", "pending_or_provisional"]


@dataclass(frozen=True)
class B2EvidenceSourceSelection:
    source_path: B2SourcePath
    evidence_required: B2EvidenceRequired
    reason: str
    web_allowed: bool
    read_only: bool
    mutation_allowed: bool
    decides_logged_or_draft: Literal[False]
    product_policy_status: B2ProductPolicyStatus


def select_evidence_source(intent: RetrievalIntent) -> B2EvidenceSourceSelection:
    read_only = intent.retrieval_goal == "query_only_answer"

    if intent.retrieval_goal == "exact_brand_lookup" or (read_only and intent.brand_hint):
        return _selection(
            source_path="exact_db",
            evidence_required="exact_item_card",
            reason="exact_brand_intent_uses_local_exact_db_first",
            read_only=read_only,
        )

    if intent.retrieval_goal == "listed_item_lookup":
        return _selection(
            source_path="listed_item_fanout",
            evidence_required="generic_anchor_packet_per_listed_item",
            reason="listed_item_intent_uses_generic_anchor_fanout",
            read_only=read_only,
        )

    if intent.retrieval_goal == "composition_clarification":
        return _selection(
            source_path="ask_user",
            evidence_required="clarify_support",
            reason="composition_unknown_requires_clarify_support",
            read_only=read_only,
            product_policy_status="pending_or_provisional",
        )

    return _selection(
        source_path="generic_anchor",
        evidence_required="generic_anchor_packet",
        reason="generic_intent_uses_local_generic_anchor",
        read_only=read_only,
    )


def _selection(
    *,
    source_path: B2SourcePath,
    evidence_required: B2EvidenceRequired,
    reason: str,
    read_only: bool,
    product_policy_status: B2ProductPolicyStatus = "source_selection_only",
) -> B2EvidenceSourceSelection:
    return B2EvidenceSourceSelection(
        source_path=source_path,
        evidence_required=evidence_required,
        reason=reason,
        web_allowed=False,
        read_only=read_only,
        mutation_allowed=not read_only,
        decides_logged_or_draft=False,
        product_policy_status=product_policy_status,
    )


__all__ = ["B2EvidenceSourceSelection", "select_evidence_source"]
