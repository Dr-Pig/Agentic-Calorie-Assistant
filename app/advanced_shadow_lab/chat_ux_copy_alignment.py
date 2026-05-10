from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import (
    FALSE_FLAG_NAMES as LAB_FALSE_FLAG_NAMES,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.chat_ux_copy_alignment"
)
FIXTURE_TYPE = "advanced_shadow_e2e_fixture_chain_artifact"
FALSE_FLAG_NAMES = LAB_FALSE_FLAG_NAMES
COPY_SIDE_EFFECT_FLAG_NAMES = tuple(
    flag for flag in FALSE_FLAG_NAMES if flag != "live_provider_used"
)
TARGET_SURFACE_TO_WORKFLOW = {
    "recommendation_prompt_reason_copy": "recommendation",
    "rescue_proposal_copy_posture": "rescue",
    "proactive_chat_copy_posture": "proactive",
}


def build_copy_diagnostic_metadata(
    artifacts: list[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        str(artifact.get("target_surface") or ""): _copy_metadata_row(artifact)
        for artifact in artifacts
        if str(artifact.get("target_surface") or "")
    }


def copy_diagnostic_blockers(
    copy_metadata: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    for surface, metadata in copy_metadata.items():
        for flag in COPY_SIDE_EFFECT_FLAG_NAMES:
            if metadata.get(flag) is True:
                blockers.append(f"copy_diagnostic[{surface}].{flag}")
    return blockers


def copy_alignment_summary(
    copy_metadata: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    counts = {
        "aligned_count": 0,
        "not_applicable_count": 0,
        "blocked_count": 0,
        "not_run_count": 0,
    }
    for row in copy_metadata.values():
        status = row.get("alignment_status")
        if status == "aligned":
            counts["aligned_count"] += 1
        elif status == "not_applicable_to_existing_packet":
            counts["not_applicable_count"] += 1
        elif status == "not_run":
            counts["not_run_count"] += 1
        else:
            counts["blocked_count"] += 1
    return {"status": "blocked" if counts["blocked_count"] else "pass", **counts}


def copy_for_workflow(
    workflow: str,
    copy_metadata: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    for surface, metadata in copy_metadata.items():
        if TARGET_SURFACE_TO_WORKFLOW.get(surface) == workflow:
            return metadata
    return {}


def copy_status(copy: Mapping[str, Any]) -> str:
    if not copy:
        return "copy_diagnostic_not_attached"
    status = str(copy.get("alignment_status") or "")
    return "copy_diagnostic_aligned" if status == "aligned" else f"copy_diagnostic_{status}"


def public_copy_metadata(copy: Mapping[str, Any]) -> dict[str, Any] | None:
    if not copy:
        return None
    return {
        "artifact_type": str(copy.get("artifact_type") or ""),
        "status": str(copy.get("status") or ""),
        "target_surface": str(copy.get("target_surface") or ""),
        "provider_mode": str(copy.get("provider_mode") or ""),
        "output_guard_status": str(copy.get("output_guard_status") or ""),
        "alignment_status": str(copy.get("alignment_status") or ""),
    }


def chat_packet_copy_alignment_row(
    fixture_chain: Mapping[str, Any],
) -> dict[str, str]:
    packet = _mapping(fixture_chain.get("chat_ux_packet"))
    summary = _mapping(packet.get("copy_alignment_summary"))
    packet_status = str(packet.get("status") or "missing")
    alignment_status = str(summary.get("status") or "missing")
    if packet_status == "pass" and alignment_status == "pass":
        finding = "copy_alignment_passed"
    elif packet_status == "missing":
        finding = "chat_ux_packet_missing"
    else:
        finding = "copy_alignment_blocked"
    return {
        "surface": "chat_ux_packet_copy_alignment",
        "fixture_status": packet_status,
        "dogfood_status": "not_applicable",
        "live_status": alignment_status,
        "finding": finding,
    }


def chat_packet_copy_alignment_blockers(
    fixture_chain: Mapping[str, Any],
) -> list[str]:
    if fixture_chain.get("artifact_type") != FIXTURE_TYPE or fixture_chain.get("status") != "pass":
        return []
    row = chat_packet_copy_alignment_row(fixture_chain)
    if row["fixture_status"] == "pass" and row["live_status"] == "pass":
        return []
    return [f"chat_ux_packet_copy_alignment.{row['finding']}"]


def _copy_metadata_row(artifact: Mapping[str, Any]) -> dict[str, Any]:
    surface = str(artifact.get("target_surface") or "")
    status = str(artifact.get("status") or "")
    guard_status = str(_mapping(artifact.get("output_guard")).get("status") or "")
    return {
        "artifact_type": str(artifact.get("artifact_type") or ""),
        "status": status,
        "target_surface": surface,
        "provider_mode": str(artifact.get("provider_mode") or ""),
        "output_guard_status": guard_status,
        "alignment_status": _alignment_status(surface, status, guard_status),
        **{flag: artifact.get(flag) for flag in COPY_SIDE_EFFECT_FLAG_NAMES if artifact.get(flag) is True},
    }


def _alignment_status(surface: str, status: str, guard_status: str) -> str:
    if TARGET_SURFACE_TO_WORKFLOW.get(surface) == "proactive":
        return "not_applicable_to_existing_packet"
    if status == "not_run":
        return "not_run"
    if status == "pass" and guard_status == "pass":
        return "aligned"
    return "blocked"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
