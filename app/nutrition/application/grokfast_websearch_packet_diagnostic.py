from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


GROKFAST_WEBSEARCH_PACKET_PROFILE = {
    "provider_profile_id": "builderspace-grok-4-fast-websearch-packet-smoke",
    "provider": "builderspace",
    "model": "grok-4-fast",
    "provider_profile_role": "live_diagnostic_probe",
    "cost_tier": "low",
    "production_selected": False,
    "readiness_owner": False,
}

NON_CLAIMS = [
    "no_readiness_claim",
    "no_production_model_selection",
    "no_self_use_approval",
    "no_runtime_mutation",
    "no_fooddb_truth_promotion",
    "no_exact_card_truth_promotion",
    "no_kimi_call",
    "no_websearch_runtime_truth",
]


def build_fixture_manager_outputs(*, review_packet_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = []
    for packet in review_packet_artifact.get("review_packets") or []:
        if not isinstance(packet, dict):
            continue
        outputs.append(
            {
                "packet_id": packet.get("packet_id"),
                "manager_output": {
                    "manager_action": "final",
                    "final_action": "answer_only",
                    "workflow_effect": "no_mutation_review_candidate_only",
                    "target_attachment": {},
                    "tool_calls": [],
                    "item_results": [],
                    "evidence_used": [packet.get("packet_id"), packet.get("source_url")],
                    "answer_contract": {
                        "text": "WebSearch packet is an exact-card review candidate only; approval is required before runtime use."
                    },
                    "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
                },
                "provider_trace": {
                    "fixture_provider": True,
                    "provider_profile_id": GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"],
                    "provider_profile_model": GROKFAST_WEBSEARCH_PACKET_PROFILE["model"],
                },
            }
        )
    return outputs


def build_grokfast_websearch_packet_diagnostic(
    *,
    review_packet_artifact: dict[str, Any],
    manager_outputs: list[dict[str, Any]],
    live_provider_used: bool,
    status: str | None = None,
    failure_family: str | None = None,
) -> dict[str, Any]:
    outputs_by_packet = {
        str(item.get("packet_id")): item
        for item in manager_outputs
        if isinstance(item, dict) and item.get("packet_id")
    }
    case_results = []
    review_packets = [
        packet
        for packet in review_packet_artifact.get("review_packets") or []
        if isinstance(packet, dict)
    ]
    if not review_packets:
        return {
            "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
            "artifact_schema_version": "1.0",
            "generated_at_utc": _now(),
            "track": "FDB",
            "classification": "live_diagnostic_only",
            "status": status or "blocked",
            "failure_family": failure_family or "missing_review_packets",
            "claim_scope": "grokfast_manager_websearch_review_packet_seam_smoke",
            "provider_profile": dict(GROKFAST_WEBSEARCH_PACKET_PROFILE),
            "live_provider_used": live_provider_used,
            "readiness_claimed": False,
            "self_use_approved": False,
            "production_selected": False,
            "runtime_mutation_attempted": False,
            "runtime_truth_changed": False,
            "manager_context_changed": False,
            "packetizer_format_changed": False,
            "review_packet_artifact_type": review_packet_artifact.get("artifact_type"),
            "cases": [],
            "summary": {
                "case_count": 0,
                "pass_count": 0,
                "fail_count": 1,
                "failure_families": ["missing_review_packets"],
            },
            "non_claims": list(NON_CLAIMS),
        }

    for packet in review_packets:
        output = outputs_by_packet.get(str(packet.get("packet_id") or ""))
        if output is None:
            case_results.append(
                {
                    "packet_id": packet.get("packet_id"),
                    "status": "fail",
                    "failure_families": ["missing_manager_output"],
                    "provider_trace": {},
                }
            )
            continue
        evaluation = evaluate_manager_output_against_review_packet(
            review_packet=packet,
            manager_output=dict(output.get("manager_output") or {}),
        )
        evaluation["provider_trace"] = dict(output.get("provider_trace") or {})
        case_results.append(evaluation)

    pass_count = sum(1 for item in case_results if item.get("status") == "pass")
    fail_count = len(case_results) - pass_count
    return {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "live_diagnostic_only",
        "status": status or ("pass" if fail_count == 0 else "diagnostic_fail"),
        "failure_family": failure_family,
        "claim_scope": "grokfast_manager_websearch_review_packet_seam_smoke",
        "provider_profile": dict(GROKFAST_WEBSEARCH_PACKET_PROFILE),
        "live_provider_used": live_provider_used,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "runtime_mutation_attempted": False,
        "runtime_truth_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "review_packet_artifact_type": review_packet_artifact.get("artifact_type"),
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "failure_families": sorted(
                {
                    family
                    for item in case_results
                    for family in item.get("failure_families", [])
                    if family
                }
            ),
        },
        "non_claims": list(NON_CLAIMS),
    }


def evaluate_manager_output_against_review_packet(
    *,
    review_packet: dict[str, Any],
    manager_output: dict[str, Any],
) -> dict[str, Any]:
    allowed_refs = _allowed_refs(review_packet)
    used_refs = _used_evidence_refs(manager_output)
    invented_refs = sorted(ref for ref in used_refs if not _ref_is_allowed(ref, allowed_refs))
    failure_families: list[str] = []

    if invented_refs:
        failure_families.append("invented_evidence_reference")
    if not any(_ref_is_allowed(ref, allowed_refs) for ref in used_refs):
        failure_families.append("websearch_review_packet_not_used")
    if str(manager_output.get("manager_action") or "") != "final":
        failure_families.append("manager_did_not_finalize_after_packet")
    if str(manager_output.get("final_action") or "") in {"commit", "log_food", "add_food"}:
        failure_families.append("review_candidate_used_for_commit")
    if any(bool(item) for item in _recursive_values_for_key(manager_output, "item_results")):
        failure_families.append("review_candidate_used_as_item_result")
    if manager_output.get("tool_calls"):
        failure_families.append("review_packet_triggered_additional_tools")
    if _has_truth_or_promotion_claim(manager_output):
        failure_families.append("review_candidate_promoted_to_truth")
    mutation_intent = str(((manager_output.get("semantic_decision") or {}).get("mutation_intent_candidate")) or "")
    if mutation_intent and mutation_intent != "no_mutation":
        failure_families.append("review_candidate_mutation_intent")

    return {
        "packet_id": review_packet.get("packet_id"),
        "status": "pass" if not failure_families else "fail",
        "failure_families": failure_families,
        "used_evidence_refs": sorted(used_refs),
        "allowed_evidence_refs": sorted(allowed_refs),
        "manager_action": manager_output.get("manager_action"),
        "final_action": manager_output.get("final_action"),
        "runtime_mutation_attempted": False,
        "manager_output": manager_output,
    }


def build_live_manager_payload(*, review_packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "diagnostic_scope": "websearch_review_packet_manager_seam_smoke",
        "raw_user_input": review_packet.get("matched_name") or review_packet.get("canonical_name"),
        "websearch_exact_candidate_review_packet": dict(review_packet),
        "instructions": [
            "Use only the provided WebSearch exact-card review packet for source references.",
            "Treat extracted kcal/serving values as review candidates, not runtime truth.",
            "Do not create an exact card or claim runtime nutrition truth.",
            "Do not mutate or write ledger state.",
            "Return a final answer-only diagnostic decision that states approval is required before runtime use.",
        ],
        "constraints": {
            "phase_b1_manager_role": "pass_2_synthesis",
            "websearch_review_packet_smoke": True,
            "runtime_truth_allowed": False,
            "runtime_mutation_allowed": False,
        },
    }


def _allowed_refs(review_packet: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for key in (
        "packet_id",
        "source_url",
        "source_title",
        "canonical_name",
        "matched_name",
        "source_extract_result_candidate_id",
        "source_selected_extract_packet_id",
        "source_exact_card_candidate_id",
    ):
        value = str(review_packet.get(key) or "").strip()
        if value:
            refs.add(value)
    source = review_packet.get("source_provenance") if isinstance(review_packet.get("source_provenance"), dict) else {}
    for key in ("raw_extract_ref", "selected_extract_packet_id", "source_url"):
        value = str(source.get(key) or "").strip()
        if value:
            refs.add(value)
    return refs


def _used_evidence_refs(manager_output: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for value in _recursive_values_for_key(manager_output, "evidence_used"):
        values = value if isinstance(value, list) else [value]
        for ref in values:
            cleaned = str(ref or "").strip()
            if cleaned:
                refs.add(cleaned)
    return refs


def _has_truth_or_promotion_claim(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {
                "runtime_truth_allowed",
                "packet_ready_truth_allowed",
                "promotion_allowed",
                "exact_card_created",
                "runtime_mutation_allowed",
            } and item is True:
                return True
            if key == "exactness" and str(item or "").lower() == "exact":
                return True
            if _has_truth_or_promotion_claim(item):
                return True
    elif isinstance(value, list):
        return any(_has_truth_or_promotion_claim(item) for item in value)
    elif isinstance(value, str):
        return _has_textual_truth_overclaim(value)
    return False


def _has_textual_truth_overclaim(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    overclaim_phrases = (
        "approved for runtime",
        "runtime use approved",
        "approved as truth",
        "runtime truth allowed",
        "promotion approved",
        "ready to create the exact card",
        "can create exact card",
        "created exact card",
        "exact card approved",
    )
    return any(phrase in normalized for phrase in overclaim_phrases)


def _recursive_values_for_key(value: Any, key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for item_key, item_value in value.items():
            if item_key == key:
                found.append(item_value)
            found.extend(_recursive_values_for_key(item_value, key))
    elif isinstance(value, list):
        for item in value:
            found.extend(_recursive_values_for_key(item, key))
    return found


def _ref_is_allowed(ref: str, allowed_refs: set[str]) -> bool:
    normalized_ref = _normalize_ref(ref)
    return any(normalized_ref == _normalize_ref(allowed) for allowed in allowed_refs if allowed)


def _normalize_ref(value: str) -> str:
    return value.strip().strip(".,;:()[]{}<>\"'").lower()


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "GROKFAST_WEBSEARCH_PACKET_PROFILE",
    "NON_CLAIMS",
    "build_fixture_manager_outputs",
    "build_grokfast_websearch_packet_diagnostic",
    "build_live_manager_payload",
    "evaluate_manager_output_against_review_packet",
]
