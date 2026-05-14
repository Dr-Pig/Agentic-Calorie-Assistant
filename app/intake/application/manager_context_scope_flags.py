from __future__ import annotations

from typing import Any


def current_turn_context_evidence_scope_flags() -> dict[str, Any]:
    return {
        "read_only": True,
        "mutation_authority": False,
        "context_evidence_read_only": True,
        "read_only_scope": "context_packet_evidence",
        "mutation_authority_scope": "context_packet_not_product_action",
        "user_utterance_may_request_mutation": True,
        "semantic_owner": "manager_llm",
    }


__all__ = ["current_turn_context_evidence_scope_flags"]
