from __future__ import annotations

from typing import Any, Mapping


def calibration_proposal(packet: Mapping[str, Any]) -> dict[str, Any]:
    proposal = _mapping(packet.get("calibration_proposal_packet"))
    if not proposal:
        return {}
    return {
        "proposal_card": dict(_mapping(proposal.get("proposal_card"))),
        "primary_actions": [str(item) for item in proposal.get("primary_actions") or []],
        "lab_body_plan_preview": dict(_mapping(proposal.get("lab_body_plan_preview"))),
        "canonical_commit_requested": proposal.get("canonical_commit_requested") is True,
        "proposal_committed": proposal.get("proposal_committed") is True,
        "source_calibration_artifact_type": str(
            proposal.get("source_calibration_artifact_type") or ""
        ),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["calibration_proposal"]
