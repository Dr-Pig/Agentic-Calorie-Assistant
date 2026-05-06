from __future__ import annotations

from typing import Any


_ALLOWED_NEXT_SLICES = {
    "await_manager_contract_owner_repair",
    "grokfast_websearch_packet_live_diagnostic",
    "inspect_contract_handoff_status",
    "inspect_fooddb_live_failure_taxonomy",
    "narrow_fooddb_packet_boundary_or_prompt_probe",
    "repair_artifact_alignment_required",
    "tighten_fooddb_manager_contract_prompt_or_transport",
}


def handoff_proof(artifact: dict[str, Any]) -> dict[str, Any]:
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    return {
        "status": str(artifact.get("status") or ""),
        "selected_next_step": safe_fooddb_handoff_next_slice(artifact.get("selected_next_step")),
        "handoff_ready": artifact.get("handoff_ready") is True,
        "runtime_truth_changed": artifact.get("runtime_truth_changed") is True,
        "runtime_mutation_attempted": artifact.get("runtime_mutation_attempted") is True,
        "shared_contract_changed": artifact.get("shared_contract_changed") is True,
        "readiness_claimed": artifact.get("readiness_claimed") is True,
        "summary": {
            "live_seam_status": str(summary.get("live_seam_status") or ""),
            "contract_failure_detected": summary.get("contract_failure_detected") is True,
            "probe_case_count": safe_non_negative_int(summary.get("probe_case_count")),
            "repair_case_count": safe_non_negative_int(summary.get("repair_case_count")),
            "alignment_blocker_count": safe_non_negative_int(summary.get("alignment_blocker_count")),
            "aggregate_missing_required_fields": safe_count_map(
                summary.get("aggregate_missing_required_fields")
            ),
            "alias_hint_counts": safe_count_map(summary.get("alias_hint_counts")),
            "probe_match_status_counts": safe_count_map(
                summary.get("probe_match_status_counts")
            ),
            "trace_status_counts": safe_count_map(summary.get("trace_status_counts")),
        },
        "alignment_blockers": safe_string_list(artifact.get("alignment_blockers")),
    }


def unblocked_handoff_shape_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = handoff_proof(artifact)["summary"]
    if summary["probe_case_count"] <= 0:
        blockers.append("manager_contract_handoff_probe_evidence_missing")
    if summary["alignment_blocker_count"] != 0:
        blockers.append("manager_contract_handoff_alignment_blockers_present")
    if artifact.get("alignment_blockers") not in ([], None):
        blockers.append("manager_contract_handoff_alignment_blocker_payload_present")
    for key, blocker in (
        ("runtime_truth_changed", "manager_contract_handoff_changed_runtime_truth"),
        ("runtime_mutation_attempted", "manager_contract_handoff_attempted_mutation"),
        ("shared_contract_changed", "manager_contract_handoff_changed_shared_contract"),
        ("readiness_claimed", "manager_contract_handoff_claimed_readiness"),
    ):
        if artifact.get(key) is not False:
            blockers.append(blocker)
    return blockers


def safe_fooddb_handoff_next_slice(value: Any) -> str:
    text = str(value or "").strip()
    if text in _ALLOWED_NEXT_SLICES:
        return text
    return ""


def safe_non_negative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, value)


def safe_count_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for key, count in value.items():
        if isinstance(count, bool) or not isinstance(count, int):
            continue
        result[str(key)] = max(0, count)
    return dict(sorted(result.items()))


def safe_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value if isinstance(item, str))


__all__ = [
    "handoff_proof",
    "safe_count_map",
    "safe_fooddb_handoff_next_slice",
    "safe_non_negative_int",
    "safe_string_list",
    "unblocked_handoff_shape_blockers",
]
