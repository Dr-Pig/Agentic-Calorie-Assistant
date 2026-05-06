from __future__ import annotations

import hashlib
import json
from typing import Any

from .websearch_live_extract_preflight import is_websearch_live_extract_preflight_clear
from .websearch_preflight_digest import websearch_live_extract_preflight_digest


def readiness_source_refs(
    review: dict[str, Any],
    preflight: dict[str, Any],
    chain: dict[str, Any],
) -> dict[str, Any]:
    return {
        "review_packet_digest": artifact_digest(review),
        "preflight_artifact_digest": websearch_live_extract_preflight_digest(preflight),
        "exact_candidate_chain_status_digest": artifact_digest(chain),
    }


def review_packet_count(artifact: dict[str, Any]) -> int:
    return len(review_packets(artifact))


def input_artifact_blockers(
    *,
    review_packet_artifact: dict[str, Any],
    preflight_artifact: dict[str, Any],
    exact_candidate_chain_status_artifact: dict[str, Any],
) -> list[str]:
    return [
        *_review_packet_blockers(review_packet_artifact),
        *_preflight_blockers(preflight_artifact, review_packet_artifact),
        *_chain_status_blockers(
            exact_candidate_chain_status_artifact,
            review_packet_artifact,
        ),
    ]


def live_runner_readiness_input_blockers(
    *,
    readiness_artifact: dict[str, Any],
    review_packet_artifact: dict[str, Any],
    preflight_artifact: dict[str, Any],
    exact_candidate_chain_status_artifact: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if not is_websearch_live_runner_readiness_clear(readiness_artifact):
        blockers.append("websearch_live_runner_readiness_packet_not_clear")
    refs = readiness_artifact.get("source_refs")
    refs = refs if isinstance(refs, dict) else {}
    expected_refs = readiness_source_refs(
        review_packet_artifact,
        preflight_artifact,
        exact_candidate_chain_status_artifact,
    )
    for key, expected_value in expected_refs.items():
        if refs.get(key) != expected_value:
            blockers.append(f"websearch_live_runner_readiness_source_ref_mismatch:{key}")
    return blockers


def is_websearch_live_runner_readiness_clear(artifact: dict[str, Any]) -> bool:
    return (
        artifact.get("artifact_type")
        == "accurate_intake_websearch_live_runner_readiness_packet_v1"
        and artifact.get("status") == "pass"
        and artifact.get("ready_for_grokfast_websearch_packet_live_diagnostic") is True
        and artifact.get("ready_for_runtime_truth") is False
        and artifact.get("runtime_truth_changed") is False
        and artifact.get("runtime_mutation_allowed") is False
        and artifact.get("manager_context_changed") is False
        and artifact.get("shared_contract_changed") is False
        and artifact.get("packetizer_format_changed") is False
        and artifact.get("live_provider_used") is False
        and artifact.get("live_websearch_used") is False
        and artifact.get("live_extract_used") is False
        and artifact.get("readiness_claimed") is False
        and not artifact.get("blockers")
    )


def _review_packet_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "accurate_intake_websearch_exact_candidate_review_packet_v1":
        blockers.append("unsupported_exact_review_packet_artifact")
    if artifact.get("status") != "pass":
        blockers.append("exact_review_packet_artifact_not_pass")
    for key, blocker in (
        ("runtime_truth_changed", "exact_review_packet_artifact_changed_runtime_truth"),
        ("runtime_mutation_allowed", "exact_review_packet_artifact_allowed_runtime_mutation"),
        ("live_websearch_used", "exact_review_packet_artifact_used_live_websearch"),
        ("live_extract_used", "exact_review_packet_artifact_used_live_extract"),
        ("live_provider_used", "exact_review_packet_artifact_used_live_provider"),
        ("readiness_claimed", "exact_review_packet_artifact_claimed_readiness"),
    ):
        if artifact.get(key) is not False:
            blockers.append(blocker)
    if not review_packets(artifact):
        blockers.append("exact_review_packet_missing")
    return blockers


def _preflight_blockers(preflight: dict[str, Any], review_packet: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not is_websearch_live_extract_preflight_clear(preflight):
        blockers.append("websearch_live_extract_preflight_not_clear")
    if not _preflight_authorizes_review_packet(preflight, review_packet):
        blockers.append("websearch_live_preflight_review_packet_mismatch")
    return blockers


def _chain_status_blockers(chain: dict[str, Any], review_packet: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not _is_chain_status_clear(chain):
        blockers.append("websearch_exact_candidate_chain_status_not_clear")
    if not _chain_status_authorizes_review_packet(chain, review_packet):
        blockers.append("websearch_exact_candidate_chain_review_packet_mismatch")
    return blockers


def _is_chain_status_clear(chain: dict[str, Any]) -> bool:
    return (
        chain.get("artifact_type") == "accurate_intake_websearch_exact_candidate_chain_status_v1"
        and chain.get("status") == "pass"
        and chain.get("ready_for_live_diagnostic") is True
        and chain.get("ready_for_runtime_truth") is False
        and chain.get("runtime_truth_changed") is False
        and chain.get("runtime_mutation_allowed") is False
        and chain.get("live_websearch_used") is False
        and chain.get("live_extract_used") is False
        and chain.get("live_provider_used") is False
        and chain.get("readiness_claimed") is False
    )


def _preflight_authorizes_review_packet(preflight: dict[str, Any], review_packet: dict[str, Any]) -> bool:
    preflight_refs = {
        (
            str(item.get("packet_id") or "").strip(),
            str(item.get("source_url") or "").strip(),
            str(item.get("canonical_name") or "").strip(),
            str(item.get("packet_digest") or "").strip(),
        )
        for item in preflight.get("review_packet_refs") or []
        if isinstance(item, dict)
    }
    review_refs = {
        (
            str(item.get("packet_id") or "").strip(),
            str(item.get("source_url") or "").strip(),
            str(item.get("canonical_name") or "").strip(),
            packet_digest(item),
        )
        for item in review_packets(review_packet)
    }
    return bool(preflight_refs) and preflight_refs == review_refs


def _chain_status_authorizes_review_packet(chain: dict[str, Any], review_packet: dict[str, Any]) -> bool:
    proof = chain.get("chain_proof") if isinstance(chain.get("chain_proof"), dict) else {}
    chain_review_ids = {str(item or "").strip() for item in proof.get("review_packet_ids") or []}
    review_ids = {str(item.get("packet_id") or "").strip() for item in review_packets(review_packet)}
    return bool(chain_review_ids) and chain_review_ids == review_ids


def review_packets(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in artifact.get("review_packets") or [] if isinstance(item, dict)]


def artifact_digest(artifact: dict[str, Any]) -> str:
    normalized = {key: value for key, value in artifact.items() if key != "generated_at_utc"}
    return hashlib.sha256(
        json.dumps(normalized, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]


def packet_digest(packet: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]


__all__ = [
    "input_artifact_blockers",
    "is_websearch_live_runner_readiness_clear",
    "live_runner_readiness_input_blockers",
    "readiness_source_refs",
    "review_packet_count",
]
