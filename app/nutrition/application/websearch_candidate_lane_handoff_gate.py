from __future__ import annotations

from typing import Any

from .websearch_manager_contract_handoff import build_websearch_manager_contract_handoff


_ALLOWED_MANAGER_CONTRACT_NEXT_SLICES = {
    "inspect_websearch_manager_contract_handoff",
    "narrow_websearch_packet_boundary_or_prompt_probe",
    "tighten_websearch_manager_contract_prompt_or_transport",
    "websearch_candidate_pipeline_narrow_expansion",
}


def compact_websearch_manager_contract_gate(
    *,
    manager_contract_handoff_artifact: dict[str, Any] | None,
    live_diagnostic_report: dict[str, Any] | None = None,
    contract_probe_artifact: dict[str, Any] | None = None,
    repair_pack_artifact: dict[str, Any] | None = None,
    preflight_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(manager_contract_handoff_artifact, dict):
        return _gate("not_provided", "inspect_websearch_manager_contract_handoff", True)
    if (
        str(manager_contract_handoff_artifact.get("artifact_type") or "")
        != "accurate_intake_websearch_manager_contract_handoff_v1"
    ):
        raise ValueError("unsupported_websearch_status_manager_contract_handoff")

    status = str(manager_contract_handoff_artifact.get("status") or "")
    selected_next_step = _safe_manager_contract_next_slice(
        manager_contract_handoff_artifact.get("selected_next_step")
    )
    if status == "websearch_contract_unblocked":
        blockers = _verified_unblocked_handoff_blockers(
            manager_contract_handoff_artifact=manager_contract_handoff_artifact,
            live_diagnostic_report=live_diagnostic_report,
            contract_probe_artifact=contract_probe_artifact,
            repair_pack_artifact=repair_pack_artifact,
            preflight_artifact=preflight_artifact,
        )
        if blockers:
            return _gate(
                "blocked_on_manager_contract_handoff",
                "inspect_websearch_manager_contract_handoff",
                True,
                blockers,
            )
        return _gate("clear_for_websearch_lane", selected_next_step or None, False)
    if status == "ready_for_manager_contract_owner":
        return _gate(
            "blocked_on_manager_contract_owner",
            selected_next_step or "tighten_websearch_manager_contract_prompt_or_transport",
            True,
        )
    if status == "return_to_websearch_packet_boundary":
        return _gate(
            "blocked_on_websearch_packet_boundary",
            selected_next_step or "narrow_websearch_packet_boundary_or_prompt_probe",
            True,
        )
    return _gate(
        "blocked_on_manager_contract_handoff",
        selected_next_step or "inspect_websearch_manager_contract_handoff",
        True,
    )


def _verified_unblocked_handoff_blockers(
    *,
    manager_contract_handoff_artifact: dict[str, Any],
    live_diagnostic_report: dict[str, Any] | None,
    contract_probe_artifact: dict[str, Any] | None,
    repair_pack_artifact: dict[str, Any] | None,
    preflight_artifact: dict[str, Any] | None,
) -> list[str]:
    blockers = _unblocked_handoff_shape_blockers(manager_contract_handoff_artifact)
    if not all(
        isinstance(artifact, dict)
        for artifact in (
            live_diagnostic_report,
            contract_probe_artifact,
            repair_pack_artifact,
            preflight_artifact,
        )
    ):
        blockers.append("manager_contract_handoff_source_artifacts_missing")
        return blockers
    try:
        derived = build_websearch_manager_contract_handoff(
            live_diagnostic_report=live_diagnostic_report,  # type: ignore[arg-type]
            contract_probe_artifact=contract_probe_artifact,  # type: ignore[arg-type]
            repair_pack_artifact=repair_pack_artifact,  # type: ignore[arg-type]
            preflight_artifact=preflight_artifact,  # type: ignore[arg-type]
        )
    except ValueError:
        blockers.append("manager_contract_handoff_source_artifacts_invalid")
        return blockers
    if _handoff_proof(manager_contract_handoff_artifact) != _handoff_proof(derived):
        blockers.append("manager_contract_handoff_derivation_mismatch")
    return blockers


def _unblocked_handoff_shape_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
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


def _handoff_proof(artifact: dict[str, Any]) -> dict[str, Any]:
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    return {
        "status": str(artifact.get("status") or ""),
        "selected_next_step": _safe_manager_contract_next_slice(
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
            "probe_case_count": _safe_non_negative_int(summary.get("probe_case_count")),
            "probe_fail_count": _safe_non_negative_int(summary.get("probe_fail_count")),
            "repair_case_count": _safe_non_negative_int(summary.get("repair_case_count")),
            "alignment_blocker_count": _safe_non_negative_int(
                summary.get("alignment_blocker_count")
            ),
        },
        "alignment_blockers": _safe_string_list(artifact.get("alignment_blockers")),
        "artifact_chain": artifact.get("artifact_chain") if isinstance(
            artifact.get("artifact_chain"), dict
        ) else {},
    }


def _safe_manager_contract_next_slice(value: Any) -> str:
    text = str(value or "").strip()
    if text in _ALLOWED_MANAGER_CONTRACT_NEXT_SLICES:
        return text
    return ""


def _safe_non_negative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, value)


def _safe_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value if isinstance(item, str))


def _gate(
    status: str,
    next_required_slice: str | None,
    blocked: bool,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "next_required_slice": next_required_slice,
        "blocked": blocked,
        "blockers": sorted(set(blockers or [])),
    }


__all__ = ["compact_websearch_manager_contract_gate"]
