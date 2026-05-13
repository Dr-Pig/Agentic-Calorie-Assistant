from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.rescue_posture_handoff import (
    build_recommendation_rescue_posture_handoff,
)


def build_recommendation_rescue_posture_bridge(
    *,
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    rescue_effect = _mapping(fixture_inputs.get("isolated_lab_rescue_commit_effect"))
    if not rescue_effect:
        return {
            "artifact_type": "advanced_product_lab_recommendation_rescue_posture_bridge",
            "status": "omitted",
            "reason": "no_accepted_rescue_overlay",
            "recommendation_fixture_inputs": dict(fixture_inputs),
            "rescue_posture_applied_to_recommendation": False,
            "source_handoff_artifact": {},
            "blockers": [],
        }
    handoff = build_recommendation_rescue_posture_handoff(
        isolated_lab_rescue_commit_effect=rescue_effect,
        recommendation_payload=_mapping(fixture_inputs.get("recommendation_payload")),
    )
    patched_inputs = dict(fixture_inputs)
    if handoff.get("status") == "pass":
        patched_inputs["recommendation_payload"] = dict(
            _mapping(handoff.get("recommendation_runtime_patch"))
        )
    return {
        "artifact_type": "advanced_product_lab_recommendation_rescue_posture_bridge",
        "status": str(handoff.get("status") or "blocked"),
        "reason": "",
        "recommendation_fixture_inputs": patched_inputs,
        "rescue_posture_applied_to_recommendation": handoff.get("status") == "pass",
        "source_handoff_artifact": handoff,
        "blockers": [str(item) for item in handoff.get("blockers") or []],
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_recommendation_rescue_posture_bridge"]
