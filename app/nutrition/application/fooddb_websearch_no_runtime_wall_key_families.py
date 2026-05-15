from __future__ import annotations

from typing import Any


def live_usage_key_forbidden(lowered_key: str) -> bool:
    actors = ("live", "llm", "provider", "websearch", "web_search", "tavily")
    if not any(actor in lowered_key for actor in actors):
        return False
    if "allowed" in lowered_key:
        return True
    return any(
        marker in lowered_key
        for marker in (
            "call",
            "called",
            "call_used",
            "enabled",
            "invoked",
            "invocation",
            "invocations",
            "request",
            "request_sent",
            "sent",
            "used",
            "usage",
        )
    ) or (
        "allowed" in lowered_key
        and ("call" in lowered_key or "live" in lowered_key or "runtime" in lowered_key)
    )


def mutation_key_forbidden(lowered_key: str) -> bool:
    return "mutation" in lowered_key or lowered_key == "ledger_mutated"


def promotion_key_forbidden(lowered_key: str) -> bool:
    if "promot" not in lowered_key:
        return False
    return any(marker in lowered_key for marker in ("allowed", "created", "promoted", "runtime_truth", "truth"))


def readiness_key_forbidden(lowered_key: str) -> bool:
    if "readiness_claim" in lowered_key:
        return True
    if "self_use" in lowered_key and "approved" in lowered_key:
        return True
    if "claimed" in lowered_key or "claim" in lowered_key:
        return any(marker in lowered_key for marker in ("private_self_use", "product", "production", "self_use"))
    if "ready" not in lowered_key and "readiness" not in lowered_key:
        return False
    return any(marker in lowered_key for marker in ("private_self_use", "product", "production", "self_use"))


def context_or_schema_change_key_forbidden(lowered_key: str) -> bool:
    return change_family_key(lowered_key) and any(
        marker in lowered_key for marker in ("context", "manager_context", "schema")
    )


def contract_or_format_change_key_forbidden(lowered_key: str) -> bool:
    return change_family_key(lowered_key) and any(
        marker in lowered_key for marker in ("contract", "format", "packet", "packetizer", "shared")
    )


def product_loop_key_forbidden(lowered_key: str) -> bool:
    if "product_loop" in lowered_key and any(
        marker in lowered_key
        for marker in ("activat", "claim", "consum", "integrat", "integration", "ready", "readiness")
    ):
        return True
    return "completed_product_loop" in lowered_key


def source_blocker_family_key(lowered_key: str) -> bool:
    return any(marker in lowered_key for marker in ("blocker", "leak", "violation"))


def metadata_key_allowed(lowered_key: str) -> bool:
    return lowered_key == "artifact_type" or lowered_key.endswith("_artifact_type")


def change_family_key(lowered_key: str) -> bool:
    return any(marker in lowered_key for marker in ("change", "changed", "modif", "modified", "update", "updated"))


def runtime_truth_key_forbidden(lowered_key: str) -> bool:
    if "runtime_truth" not in lowered_key or "required_before_runtime_truth" in lowered_key:
        return False
    return any(
        marker in lowered_key
        for marker in ("allowed", "changed", "created", "leak", "promoted", "ready", "readiness")
    )


def candidate_truth_key_forbidden(
    lowered_key: str,
    path: str,
    *,
    candidate_context: bool,
) -> bool:
    if "required_before_runtime_truth" in lowered_key or not candidate_context:
        return False
    if lowered_key in {"exact_card", "final_truth", "packet_truth", "promotion", "runtime_truth", "selected_truth", "truth"}:
        return True
    if not any(marker in lowered_key for marker in ("exact_card", "promot", "truth")):
        return False
    return any(
        marker in lowered_key
        for marker in ("allowed", "created", "final", "promoted", "ready", "readiness", "selected")
    )


def approved_fooddb_common_serving_anchor(parent: dict[str, Any]) -> bool:
    approval = parent.get("approval_metadata")
    return (
        parent.get("runtime_role") == "common_serving_anchor"
        and parent.get("runtime_truth_allowed") is True
        and isinstance(approval, dict)
        and approval.get("runtime_truth_allowed") is True
    )


def path_is_candidate_lane(path: str) -> bool:
    lowered = path.lower()
    return any(
        token in lowered
        for token in (
            "websearch",
            "candidate",
            "selected_extract",
            "extract_result",
            "exact_evidence",
            "exact_lane",
            "exact_source",
            "exact_item",
            "exact_card",
            "review_packet",
        )
    )


__all__ = [
    "approved_fooddb_common_serving_anchor",
    "candidate_truth_key_forbidden",
    "context_or_schema_change_key_forbidden",
    "contract_or_format_change_key_forbidden",
    "live_usage_key_forbidden",
    "metadata_key_allowed",
    "mutation_key_forbidden",
    "path_is_candidate_lane",
    "product_loop_key_forbidden",
    "promotion_key_forbidden",
    "readiness_key_forbidden",
    "runtime_truth_key_forbidden",
    "source_blocker_family_key",
]
