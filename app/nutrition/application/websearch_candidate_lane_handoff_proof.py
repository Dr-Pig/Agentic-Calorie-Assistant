from __future__ import annotations

from typing import Any


_ALLOWED_MANAGER_CONTRACT_NEXT_SLICES = {
    "inspect_websearch_status_packet",
    "inspect_websearch_manager_contract_handoff",
    "narrow_websearch_packet_boundary_or_prompt_probe",
    "tighten_websearch_manager_contract_prompt_or_transport",
    "websearch_candidate_pipeline_narrow_expansion",
}


def handoff_proof(artifact: dict[str, Any]) -> dict[str, Any]:
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    return {
        "status": str(artifact.get("status") or ""),
        "selected_next_step": safe_manager_contract_next_slice(
            artifact.get("selected_next_step")
        ),
        "handoff_ready": artifact.get("handoff_ready") is True,
        "runtime_truth_changed": artifact.get("runtime_truth_changed") is True,
        "runtime_mutation_attempted": artifact.get("runtime_mutation_attempted") is True,
        "shared_contract_changed": artifact.get("shared_contract_changed") is True,
        "readiness_claimed": artifact.get("readiness_claimed") is True,
        "summary": {
            "live_seam_status": str(summary.get("live_seam_status") or ""),
            "contract_failure_detected": summary.get("contract_failure_detected") is True,
            "probe_case_count": safe_non_negative_int(summary.get("probe_case_count")),
            "probe_fail_count": safe_non_negative_int(summary.get("probe_fail_count")),
            "repair_case_count": safe_non_negative_int(summary.get("repair_case_count")),
            "alignment_blocker_count": safe_non_negative_int(
                summary.get("alignment_blocker_count")
            ),
            "aggregate_missing_required_fields": safe_count_map(
                summary.get("aggregate_missing_required_fields")
            ),
            "alias_hint_counts": safe_count_map(summary.get("alias_hint_counts")),
            "shape_pattern_counts": safe_count_map(summary.get("shape_pattern_counts")),
        },
        "alignment_blockers": safe_string_list(artifact.get("alignment_blockers")),
        "artifact_chain": artifact.get("artifact_chain")
        if isinstance(artifact.get("artifact_chain"), dict)
        else {},
    }


def unblocked_handoff_shape_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    if safe_non_negative_int(summary.get("probe_case_count")) <= 0:
        blockers.append("manager_contract_handoff_probe_evidence_missing")
    if summary.get("alignment_blocker_count") != 0:
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


def handoff_probe_case_count(artifact: dict[str, Any]) -> int:
    return safe_non_negative_int(handoff_proof(artifact)["summary"]["probe_case_count"])


def safe_manager_contract_next_slice(value: Any) -> str:
    text = str(value or "").strip()
    if text in _ALLOWED_MANAGER_CONTRACT_NEXT_SLICES:
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
    "handoff_probe_case_count",
    "handoff_proof",
    "safe_count_map",
    "safe_manager_contract_next_slice",
    "safe_non_negative_int",
    "unblocked_handoff_shape_blockers",
]
