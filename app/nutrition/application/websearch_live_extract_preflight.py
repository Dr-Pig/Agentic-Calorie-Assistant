from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlparse

from .websearch_grokfast_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
    build_websearch_grokfast_live_diagnostic_case_matrix_artifact,
)
from .websearch_cache_rate_license_wall import MAX_CHUNKS_PER_SOURCE, MAX_SEARCH_RESULTS


_FORBIDDEN_LEAKAGE_MARKERS = (
    "candidate_packet",
    "likely_kcal",
    "observed_manager_output",
    "provider_trace",
    "raw_response_excerpt",
    "runtime_truth_allowed",
)
_PACKET_ID_RE = re.compile(r"^pkt_exact_card_review_[0-9a-f]{12}$")
_ALLOWED_SOURCE_URLS = {"https://milksha.example/menu/pearl-black-tea-latte"}
_ALLOWED_DISPLAY_TEXT = {"Milksha pearl black tea latte"}
_ALLOWED_SERVING_BASIS = {"per_cup"}


def build_websearch_live_extract_preflight(
    *,
    exact_review_packet_artifact: dict[str, Any],
    case_matrix_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case_matrix = (
        build_websearch_grokfast_live_diagnostic_case_matrix_artifact()
        if case_matrix_artifact is None
        else case_matrix_artifact
    )
    blockers = _review_artifact_blockers(exact_review_packet_artifact)
    blockers.extend(_case_matrix_blockers(case_matrix))
    candidate_review_packets = _review_packets(exact_review_packet_artifact)
    if not candidate_review_packets and not blockers:
        blockers.append("exact_review_packet_missing")
    blockers.extend(_review_packet_blockers(candidate_review_packets))
    clear = not blockers
    review_packets = candidate_review_packets if clear else []
    return {
        "artifact_type": "accurate_intake_websearch_live_extract_preflight_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_live_extract_preflight_only",
        "claim_scope": "websearch_live_extract_diagnostic_preflight_without_live_call",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "live_websearch_used": False,
        "live_extract_used": False,
        "live_provider_used": False,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "readiness_claimed": False,
        "ready_for_live_extract_diagnostic": clear,
        "ready_for_runtime_truth": False,
        "source_artifacts": {
            "exact_review_packet_artifact_type": _safe_review_packet_artifact_type(
                exact_review_packet_artifact.get("artifact_type")
            ),
            "case_matrix_artifact_type": _safe_case_matrix_artifact_type(
                case_matrix.get("artifact_type") if isinstance(case_matrix, dict) else None
            ),
        },
        "diagnostic_contract": {
            "live_call_allowed_by_this_artifact": False,
            "requires_explicit_allow_live_flag": True,
            "max_search_attempts": 2,
            "max_search_results": MAX_SEARCH_RESULTS,
            "max_extract_urls_per_case": 1,
            "max_chunks_per_source": MAX_CHUNKS_PER_SOURCE,
            "cache_required": True,
            "raw_content_allowed_in_manager_context": False,
            "extract_result_role": "review_candidate_only",
            "ledger_mutation_allowed": False,
            "exact_card_creation_allowed": False,
        },
        "review_packet_refs": [
            {
                "packet_id": packet.get("packet_id"),
                "source_url": packet.get("source_url"),
                "canonical_name": packet.get("canonical_name"),
                "matched_name": packet.get("matched_name"),
                "packet_digest": _review_packet_digest(packet),
            }
            for packet in review_packets
        ],
        "summary": {
            "review_packet_count": len(review_packets),
            "ready_for_live_extract_diagnostic_count": len(review_packets) if clear else 0,
            "ready_for_runtime_truth_count": 0,
            "case_matrix_case_count": _case_matrix_case_count(case_matrix),
            "case_matrix_fixed_required_cases": _case_matrix_ids(case_matrix)
            == list(REQUIRED_CASE_IDS),
            "case_matrix_negative_case_count": _case_matrix_summary_int(
                case_matrix, "negative_case_count"
            ),
            "case_matrix_modifier_guard_cases": _case_matrix_summary_int(
                case_matrix, "modifier_guard_cases"
            ),
            "case_matrix_live_provider_invoked": _case_matrix_flag_not_false(
                case_matrix, "live_provider_invoked"
            ),
            "case_matrix_websearch_invoked": _case_matrix_flag_not_false(
                case_matrix, "websearch_invoked"
            ),
        },
        "next_required_slice": (
            "grokfast_websearch_packet_live_diagnostic"
            if clear
            else "inspect_websearch_live_extract_preflight_blockers"
        ),
        "non_claims": [
            "no_live_websearch_call",
            "no_live_extract_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def is_websearch_live_extract_preflight_clear(artifact: dict[str, Any]) -> bool:
    return (
        artifact.get("artifact_type") == "accurate_intake_websearch_live_extract_preflight_v1"
        and not _preflight_integrity_blockers(artifact)
    )


def _review_artifact_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "accurate_intake_websearch_exact_candidate_review_packet_v1":
        blockers.append("unsupported_exact_review_packet_artifact")
    if artifact.get("status") != "pass":
        blockers.append("exact_review_packet_artifact_not_pass")
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("exact_review_packet_artifact_changed_runtime_truth")
    if artifact.get("runtime_mutation_allowed") is not False:
        blockers.append("exact_review_packet_artifact_allowed_runtime_mutation")
    if artifact.get("live_websearch_used") is not False:
        blockers.append("exact_review_packet_artifact_used_live_websearch")
    if artifact.get("live_extract_used") is not False:
        blockers.append("exact_review_packet_artifact_used_live_extract")
    if artifact.get("live_provider_used") is not False:
        blockers.append("exact_review_packet_artifact_used_live_provider")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("exact_review_packet_artifact_claimed_readiness")
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    if int(summary.get("runtime_truth_allowed_count") or 0) != 0:
        blockers.append("exact_review_packet_artifact_summary_runtime_truth_allowed")
    if int(summary.get("exact_card_created_count") or 0) != 0:
        blockers.append("exact_review_packet_artifact_summary_exact_card_created")
    if int(summary.get("approval_allowed_count") or 0) != 0:
        blockers.append("exact_review_packet_artifact_summary_approval_allowed")
    return blockers


def _case_matrix_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not isinstance(artifact, dict):
        return ["unsupported_websearch_grokfast_case_matrix_artifact"]
    if artifact.get("artifact_type") != (
        "accurate_intake_websearch_grokfast_packet_live_diagnostic_case_matrix"
    ):
        blockers.append("unsupported_websearch_grokfast_case_matrix_artifact")
    if artifact.get("status") != "pass":
        blockers.append("websearch_grokfast_case_matrix_not_pass")
    if artifact.get("classification") != "live_diagnostic_plan_only":
        blockers.append("websearch_grokfast_case_matrix_wrong_classification")
    if artifact.get("diagnostic_only") is not True:
        blockers.append("websearch_grokfast_case_matrix_not_diagnostic_only")
    if artifact.get("plan_only") is not True:
        blockers.append("websearch_grokfast_case_matrix_not_plan_only")
    for key, blocker in (
        ("live_llm_invoked", "websearch_grokfast_case_matrix_invoked_live_llm"),
        ("live_provider_invoked", "websearch_grokfast_case_matrix_invoked_live_provider"),
        ("websearch_invoked", "websearch_grokfast_case_matrix_invoked_websearch"),
        ("runtime_truth_changed", "websearch_grokfast_case_matrix_changed_runtime_truth"),
        ("mutation_changed", "websearch_grokfast_case_matrix_changed_mutation"),
        (
            "manager_context_packet_changed",
            "websearch_grokfast_case_matrix_changed_manager_context_packet",
        ),
        ("shared_contract_changed", "websearch_grokfast_case_matrix_changed_shared_contract"),
        ("packetizer_format_changed", "websearch_grokfast_case_matrix_changed_packetizer"),
        ("product_readiness_claimed", "websearch_grokfast_case_matrix_claimed_readiness"),
        ("private_self_use_approved", "websearch_grokfast_case_matrix_claimed_self_use"),
    ):
        if artifact.get(key) is not False:
            blockers.append(blocker)
    if _case_matrix_ids(artifact) != list(REQUIRED_CASE_IDS):
        blockers.append("websearch_grokfast_case_matrix_required_case_order_mismatch")
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    case_count, case_count_valid = _case_matrix_summary_value(summary, "case_count")
    exact_candidate_cases, exact_candidate_cases_valid = _case_matrix_summary_value(
        summary, "exact_candidate_cases"
    )
    negative_case_count, negative_case_count_valid = _case_matrix_summary_value(
        summary, "negative_case_count"
    )
    modifier_guard_cases, modifier_guard_cases_valid = _case_matrix_summary_value(
        summary, "modifier_guard_cases"
    )
    runtime_truth_allowed_cases, runtime_truth_allowed_cases_valid = _case_matrix_summary_value(
        summary, "runtime_truth_allowed_cases"
    )
    websearch_invoked_cases, websearch_invoked_cases_valid = _case_matrix_summary_value(
        summary, "websearch_invoked_cases"
    )
    live_provider_invoked_cases, live_provider_invoked_cases_valid = _case_matrix_summary_value(
        summary, "live_provider_invoked_cases"
    )
    if not case_count_valid or case_count != len(REQUIRED_CASE_IDS):
        blockers.append("websearch_grokfast_case_matrix_case_count_mismatch")
    if not exact_candidate_cases_valid or exact_candidate_cases < 1:
        blockers.append("websearch_grokfast_case_matrix_missing_exact_candidate")
    if not negative_case_count_valid or negative_case_count < 4:
        blockers.append("websearch_grokfast_case_matrix_missing_negative_cases")
    if not modifier_guard_cases_valid or modifier_guard_cases < 1:
        blockers.append("websearch_grokfast_case_matrix_missing_modifier_guard")
    if not runtime_truth_allowed_cases_valid or runtime_truth_allowed_cases != 0:
        blockers.append("websearch_grokfast_case_matrix_runtime_truth_allowed")
    if not websearch_invoked_cases_valid or websearch_invoked_cases != 0:
        blockers.append("websearch_grokfast_case_matrix_websearch_invoked_cases")
    if not live_provider_invoked_cases_valid or live_provider_invoked_cases != 0:
        blockers.append("websearch_grokfast_case_matrix_live_provider_invoked_cases")
    blockers.extend(_case_matrix_case_blockers(artifact))
    non_claims = set(artifact.get("non_claims") or [])
    for required_non_claim in (
        "not_full_self_use_gate",
        "not_websearch_runtime_truth_gate",
        "not_exact_card_promotion_gate",
        "not_live_websearch_execution",
    ):
        if required_non_claim not in non_claims:
            blockers.append(f"websearch_grokfast_case_matrix_missing_non_claim.{required_non_claim}")
    return blockers


def _case_matrix_case_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    cases = artifact.get("cases") if isinstance(artifact.get("cases"), list) else []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            blockers.append(f"websearch_grokfast_case_matrix_case_{index}_not_object")
            continue
        case_id = str(case.get("case_id") or f"index_{index}")
        for key, blocker in (
            ("live_provider_invoked", "invoked_live_provider"),
            ("websearch_invoked", "invoked_websearch"),
            ("ledger_mutation_allowed", "allowed_ledger_mutation"),
            ("runtime_truth_allowed", "allowed_runtime_truth"),
            ("snippet_truth_allowed", "allowed_snippet_truth"),
            ("exact_card_creation_allowed", "allowed_exact_card_creation"),
            ("selected_extract_truth_allowed", "allowed_selected_extract_truth"),
            ("raw_content_allowed_in_manager_context", "allowed_raw_content"),
            ("runtime_truth_changed", "changed_runtime_truth"),
            ("mutation_changed", "changed_mutation"),
            ("manager_context_packet_changed", "changed_manager_context_packet"),
            ("packetizer_format_changed", "changed_packetizer_format"),
            ("product_readiness_claimed", "claimed_product_readiness"),
        ):
            if case.get(key) is not False:
                blockers.append(f"websearch_grokfast_case_matrix.{case_id}.{blocker}")
        if case.get("websearch_candidate_only") is not True:
            blockers.append(f"websearch_grokfast_case_matrix.{case_id}.not_candidate_only")
        must_not_happen = case.get("must_not_happen")
        if not isinstance(must_not_happen, list) or "websearch_snippet_as_truth" not in must_not_happen:
            blockers.append(f"websearch_grokfast_case_matrix.{case_id}.missing_snippet_guard")
    return blockers


def _safe_review_packet_artifact_type(value: Any) -> str:
    if str(value or "") == "accurate_intake_websearch_exact_candidate_review_packet_v1":
        return "accurate_intake_websearch_exact_candidate_review_packet_v1"
    return "unsupported_exact_review_packet_artifact"


def _safe_case_matrix_artifact_type(value: Any) -> str:
    if str(value or "") == "accurate_intake_websearch_grokfast_packet_live_diagnostic_case_matrix":
        return "accurate_intake_websearch_grokfast_packet_live_diagnostic_case_matrix"
    return "unsupported_websearch_grokfast_case_matrix_artifact"


def _preflight_integrity_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("status") != "pass":
        blockers.append("preflight_status_not_pass")
    if artifact.get("ready_for_live_extract_diagnostic") is not True:
        blockers.append("preflight_not_ready_for_live_extract_diagnostic")
    if artifact.get("ready_for_runtime_truth") is not False:
        blockers.append("preflight_allowed_runtime_truth")
    if artifact.get("blockers"):
        blockers.append("preflight_has_blockers")
    if artifact.get("next_required_slice") != "grokfast_websearch_packet_live_diagnostic":
        blockers.append("preflight_next_slice_mismatch")
    for key, blocker in (
        ("live_websearch_used", "preflight_used_live_websearch"),
        ("live_extract_used", "preflight_used_live_extract"),
        ("live_provider_used", "preflight_used_live_provider"),
        ("runtime_truth_changed", "preflight_changed_runtime_truth"),
        ("runtime_mutation_allowed", "preflight_allowed_runtime_mutation"),
        ("manager_context_changed", "preflight_changed_manager_context"),
        ("packetizer_format_changed", "preflight_changed_packetizer_format"),
        ("readiness_claimed", "preflight_claimed_readiness"),
    ):
        if artifact.get(key) is not False:
            blockers.append(blocker)
    contract = artifact.get("diagnostic_contract") if isinstance(artifact.get("diagnostic_contract"), dict) else {}
    if contract.get("live_call_allowed_by_this_artifact") is not False:
        blockers.append("preflight_contract_allowed_live_call")
    if contract.get("requires_explicit_allow_live_flag") is not True:
        blockers.append("preflight_contract_missing_allow_live_flag")
    if contract.get("cache_required") is not True:
        blockers.append("preflight_contract_missing_cache")
    if contract.get("raw_content_allowed_in_manager_context") is not False:
        blockers.append("preflight_contract_allowed_raw_content_in_manager_context")
    if contract.get("ledger_mutation_allowed") is not False:
        blockers.append("preflight_contract_allowed_ledger_mutation")
    if contract.get("exact_card_creation_allowed") is not False:
        blockers.append("preflight_contract_allowed_exact_card_creation")
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    if int(summary.get("review_packet_count") or 0) <= 0:
        blockers.append("preflight_summary_review_packet_missing")
    if int(summary.get("ready_for_runtime_truth_count") or 0) != 0:
        blockers.append("preflight_summary_runtime_truth_ready")
    if int(summary.get("case_matrix_case_count") or 0) != len(REQUIRED_CASE_IDS):
        blockers.append("preflight_summary_case_matrix_case_count_mismatch")
    if summary.get("case_matrix_fixed_required_cases") is not True:
        blockers.append("preflight_summary_case_matrix_not_fixed")
    if int(summary.get("case_matrix_negative_case_count") or 0) < 4:
        blockers.append("preflight_summary_case_matrix_missing_negative_cases")
    if int(summary.get("case_matrix_modifier_guard_cases") or 0) < 1:
        blockers.append("preflight_summary_case_matrix_missing_modifier_guard")
    if summary.get("case_matrix_live_provider_invoked") is not False:
        blockers.append("preflight_summary_case_matrix_live_provider_invoked")
    if summary.get("case_matrix_websearch_invoked") is not False:
        blockers.append("preflight_summary_case_matrix_websearch_invoked")
    return blockers


def _review_packets(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        packet
        for packet in artifact.get("review_packets") or []
        if isinstance(packet, dict)
    ]


def _review_packet_blockers(packets: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for packet in packets:
        if not str(packet.get("packet_id") or "").strip():
            blockers.append("exact_review_packet_missing_packet_id")
        if not str(packet.get("source_url") or "").strip():
            blockers.append("exact_review_packet_missing_source_url")
        review_fields = packet.get("review_fields") if isinstance(packet.get("review_fields"), dict) else {}
        if _kcal_value(review_fields.get("kcal_value_candidate")) is None:
            blockers.append("exact_review_packet_missing_kcal_candidate")
        if review_fields.get("kcal_text_present") is not True:
            blockers.append("exact_review_packet_missing_kcal_text")
        if review_fields.get("identity_text_present") is not True:
            blockers.append("exact_review_packet_missing_identity_text")
        if not str(review_fields.get("serving_basis_candidate") or "").strip():
            blockers.append("exact_review_packet_missing_serving_basis")
        if str(review_fields.get("serving_basis_candidate") or "").strip() not in _ALLOWED_SERVING_BASIS:
            blockers.append("exact_review_packet_invalid_serving_basis_candidate")
        if packet.get("approval_allowed_by_this_packet") is not False:
            blockers.append("exact_review_packet_allowed_approval")
        if packet.get("runtime_truth_allowed") is not False:
            blockers.append("exact_review_packet_allowed_runtime_truth")
        if packet.get("packet_ready_truth_allowed") is not False:
            blockers.append("exact_review_packet_allowed_packet_ready_truth")
        if packet.get("promotion_allowed") is not False:
            blockers.append("exact_review_packet_allowed_promotion")
        if packet.get("exact_card_created") is not False:
            blockers.append("exact_review_packet_created_exact_card")
        if packet.get("runtime_mutation_allowed") is not False:
            blockers.append("exact_review_packet_allowed_runtime_mutation")
        if packet.get("raw_content_included") is not False:
            blockers.append("exact_review_packet_included_raw_content")
        if packet.get("raw_source_rows_included") is not False:
            blockers.append("exact_review_packet_included_raw_source_rows")
        blockers.extend(_review_packet_string_hygiene_blockers(packet))
    return blockers


def _review_packet_string_hygiene_blockers(packet: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    source_url = str(packet.get("source_url") or "").strip()
    if not _safe_https_url(source_url):
        blockers.append("exact_review_packet_invalid_source_url")
    if not _safe_packet_id(packet.get("packet_id")):
        blockers.append("exact_review_packet_invalid_packet_id")
    for key in ("canonical_name", "matched_name"):
        if not _safe_display_text(packet.get(key)):
            blockers.append(f"exact_review_packet_leaky_{key}")
    return blockers


def _safe_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme == "https") and value in _ALLOWED_SOURCE_URLS


def _safe_packet_id(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(_PACKET_ID_RE.match(text)) and not _contains_leakage_marker(text)


def _safe_display_text(value: Any) -> bool:
    text = str(value or "").strip()
    return text in _ALLOWED_DISPLAY_TEXT and not _contains_leakage_marker(text)


def _contains_leakage_marker(value: Any) -> bool:
    text = str(value or "").lower()
    return any(marker in text for marker in _FORBIDDEN_LEAKAGE_MARKERS)


def _case_matrix_ids(artifact: dict[str, Any]) -> list[str]:
    if not isinstance(artifact, dict):
        return []
    return [
        str(case.get("case_id") or "")
        for case in artifact.get("cases") or []
        if isinstance(case, dict)
    ]


def _case_matrix_case_count(artifact: dict[str, Any]) -> int:
    return len(_case_matrix_ids(artifact))


def _case_matrix_summary_int(artifact: dict[str, Any], key: str) -> int:
    if not isinstance(artifact, dict) or not isinstance(artifact.get("summary"), dict):
        return 0
    value, valid = _case_matrix_summary_value(artifact["summary"], key)
    return value if valid else 0


def _case_matrix_summary_value(summary: dict[str, Any], key: str) -> tuple[int, bool]:
    value = summary.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0, False
    return max(0, value), True


def _case_matrix_flag_not_false(artifact: dict[str, Any], key: str) -> bool:
    if not isinstance(artifact, dict):
        return True
    return artifact.get(key) is not False


def _kcal_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _review_packet_digest(packet: dict[str, Any]) -> str:
    payload = json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "build_websearch_live_extract_preflight",
    "is_websearch_live_extract_preflight_clear",
]
