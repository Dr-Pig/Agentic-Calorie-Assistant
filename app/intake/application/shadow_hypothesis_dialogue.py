from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ShadowHypothesisDialogueResult:
    assistant_message: str
    phase_a_trace: dict[str, Any]


def _shadow_trace(phase_a_trace: dict[str, Any]) -> dict[str, Any]:
    shadow = phase_a_trace.get("shadow_hypothesis_runtime")
    return dict(shadow) if isinstance(shadow, dict) else {}


def _skip_reason(shadow: dict[str, Any]) -> str | None:
    if shadow.get("created") is not True:
        return "shadow_not_created"
    if shadow.get("mutation_authority") is True:
        return "shadow_authoritative"
    if str(shadow.get("role") or "") != "tentative_non_authoritative":
        return "role_not_tentative"
    if str(shadow.get("visibility_posture") or "") != "uncertainty_visible":
        return "not_uncertainty_visible"
    if str(shadow.get("confidence") or "") != "medium":
        return "confidence_not_medium"
    if not str(shadow.get("candidate_target_object_id") or "").strip():
        return "candidate_target_missing"
    return None


def _candidate_label(shadow: dict[str, Any]) -> str:
    target_type = str(shadow.get("candidate_target_object_type") or "meal_thread")
    target_id = str(shadow.get("candidate_target_object_id") or "").strip()
    if target_type == "meal_thread":
        return f"meal thread {target_id}"
    return f"{target_type} {target_id}".strip()


def _add_trace(
    phase_a_trace: dict[str, Any],
    *,
    applied: bool,
    skip_reason: str | None,
    shadow: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(phase_a_trace)
    updated["shadow_hypothesis_dialogue"] = {
        "checked": True,
        "applied": applied,
        "skip_reason": skip_reason,
        "candidate_target_object_id": shadow.get("candidate_target_object_id"),
        "intent": shadow.get("intent"),
        "confidence": shadow.get("confidence"),
        "visibility_posture": shadow.get("visibility_posture"),
        "mutation_authority": shadow.get("mutation_authority", False),
    }
    return updated


def apply_shadow_hypothesis_dialogue_cue(
    *,
    assistant_message: str,
    phase_a_trace: dict[str, Any] | None,
    mutation_committed: bool = False,
) -> ShadowHypothesisDialogueResult:
    updated_trace = dict(phase_a_trace or {})
    shadow = _shadow_trace(updated_trace)
    if mutation_committed:
        return ShadowHypothesisDialogueResult(
            assistant_message=assistant_message,
            phase_a_trace=_add_trace(
                updated_trace,
                applied=False,
                skip_reason="mutation_already_committed",
                shadow=shadow,
            ),
        )
    skip_reason = _skip_reason(shadow)
    if skip_reason is not None:
        return ShadowHypothesisDialogueResult(
            assistant_message=assistant_message,
            phase_a_trace=_add_trace(
                updated_trace,
                applied=False,
                skip_reason=skip_reason,
                shadow=shadow,
            ),
        )

    # The shadow hypothesis may be useful review evidence, but it is not the
    # final response owner. Exposing target-object labels here leaks internal
    # state and can contradict the Manager-owned answer.
    return ShadowHypothesisDialogueResult(
        assistant_message=assistant_message,
        phase_a_trace=_add_trace(
            updated_trace,
            applied=False,
            skip_reason="user_visible_cue_disabled",
            shadow=shadow,
        ),
    )


__all__ = [
    "ShadowHypothesisDialogueResult",
    "apply_shadow_hypothesis_dialogue_cue",
]
