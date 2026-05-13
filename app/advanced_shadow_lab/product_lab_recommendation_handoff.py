from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.pending_intake_handoff_packet import (
    build_recommendation_pending_intake_handoff,
)


def build_pending_intake_handoff_packet(
    *,
    primary_candidate: Mapping[str, Any],
    ux_packet: Mapping[str, Any],
) -> dict[str, Any]:
    return build_recommendation_pending_intake_handoff(
        primary_candidate=primary_candidate,
        ux_packet=ux_packet,
        artifact_type="advanced_product_lab_pending_intake_handoff",
    )


__all__ = ["build_pending_intake_handoff_packet"]
