from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_calibration_packets"
)


def with_calibration_chat_packet(
    packets: list[Mapping[str, Any]],
    calibration: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    if not _presented(calibration):
        return list(packets)
    packet = _calibration_packet(calibration)
    if calibration.get("suppress_other_product_packets") is True:
        return [packet]
    return [*packets, packet]


def calibration_product_fields(packet: Mapping[str, Any]) -> dict[str, Any]:
    calibration = _mapping(packet.get("calibration_proposal_packet"))
    if not calibration:
        return {}
    return {
        "product_lab_copy": str(packet.get("product_lab_copy") or ""),
        "calibration_proposal_packet": dict(calibration),
        "product_runtime_output_refs": [
            str(item) for item in packet.get("product_runtime_output_refs") or []
        ],
    }


def _calibration_packet(artifact: Mapping[str, Any]) -> dict[str, Any]:
    card = _mapping(artifact.get("proposal_card"))
    return {
        "packet_id": "calibration_proposal:0",
        "workflow_family": "calibration",
        "trigger_type": "calibration_proposal",
        "product_lab_copy": " ".join(
            item
            for item in [str(card.get("headline") or ""), str(card.get("summary") or "")]
            if item
        ),
        "calibration_proposal_packet": {
            "proposal_card": dict(card),
            "primary_actions": list(artifact.get("primary_actions") or []),
            "lab_body_plan_preview": dict(_mapping(card.get("lab_body_plan_preview"))),
            "canonical_commit_requested": False,
            "proposal_committed": False,
            "source_calibration_artifact_type": str(artifact.get("artifact_type") or ""),
        },
        "product_runtime_output_refs": [str(artifact.get("artifact_type") or "")],
    }


def _presented(calibration: Mapping[str, Any]) -> bool:
    return (
        calibration.get("status") == "pass"
        and calibration.get("proposal_presented_to_lab") is True
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "calibration_product_fields",
    "with_calibration_chat_packet",
]
