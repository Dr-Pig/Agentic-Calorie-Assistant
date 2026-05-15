from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


SAFE_NO_COMMIT_REPLY = (
    "我還不能安全地更新日記，這一輪沒有寫入餐點。"
    "請補充必要資訊後我再幫你記。"
)
SAFE_DEGRADED_BUDGET_REPLY = "Onboarding is required before I can answer remaining budget."

_CANONICAL_STATE_FLAGS = (
    "meal_logged",
    "canonical_commit",
    "new_meal_version_created",
    "old_version_superseded",
)
_LEDGER_STATE_FLAGS = ("ledger_updated",)
_ALL_MUTATION_FLAGS = (*_CANONICAL_STATE_FLAGS, *_LEDGER_STATE_FLAGS, "draft_saved")


@dataclass(frozen=True)
class IntakeOutputHonestyResult:
    assistant_message: str
    state_delta: dict[str, Any]
    sidecar: dict[str, Any]
    phase_a_trace: dict[str, Any]


@dataclass(frozen=True)
class BudgetOutputHonestyResult:
    reply_text: str
    phase_a_trace: dict[str, Any]


def _result_field(result: Any | None, field_name: str) -> Any:
    if result is None:
        return None
    if isinstance(result, dict):
        return result.get(field_name)
    return getattr(result, field_name, None)


def _copy_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    return deepcopy(dict(value or {}))


def _projection_commit_decision(phase_a_trace: dict[str, Any]) -> dict[str, Any]:
    projection = phase_a_trace.get("boundary_projection")
    if not isinstance(projection, dict):
        return {}
    decision = projection.get("commit_boundary_decision")
    return dict(decision) if isinstance(decision, dict) else {}


def _add_trace(
    phase_a_trace: dict[str, Any],
    *,
    normalized: bool,
    reasons: list[str],
    affected_surfaces: list[str],
    text_check_used: bool = False,
    budget_answer_mode: str | None = None,
    concrete_remaining_kcal_allowed: bool | None = None,
) -> dict[str, Any]:
    updated = dict(phase_a_trace)
    payload: dict[str, Any] = {
        "checked": True,
        "normalized": normalized,
        "reasons": list(reasons),
        "affected_surfaces": list(affected_surfaces),
        "structured_sources": [
            "state_delta",
            "sidecar",
            "phase_a_commit_boundary_preflight",
            "boundary_projection",
            "budget_answer_contract",
            "persistence_result",
        ],
        "text_check_used": text_check_used,
    }
    if budget_answer_mode is not None:
        payload["budget_answer_mode"] = budget_answer_mode
    if concrete_remaining_kcal_allowed is not None:
        payload["concrete_remaining_kcal_allowed"] = concrete_remaining_kcal_allowed
    updated["phase_a_output_honesty"] = payload
    return updated


def _clear_flags(target: dict[str, Any], flags: tuple[str, ...]) -> bool:
    changed = False
    for flag in flags:
        if target.get(flag) is not False:
            target[flag] = False
            changed = True
    return changed


def _minimal_false_commit_claim(reply_text: str) -> bool:
    normalized = reply_text.strip().lower()
    if normalized.startswith("logged") or normalized.startswith("committed"):
        return True
    positive_commit_markers = (
        "已記錄",
        "已更新",
        "已加到",
        "已加入",
        "已寫入",
        "已經記錄",
        "已經更新",
        "已經加到",
        "logged",
        "committed",
        "saved",
    )
    negation_markers = (
        "沒有寫入",
        "尚未寫入",
        "還沒寫入",
        "沒有更新",
        "尚未更新",
        "還沒更新",
        "not saved",
        "not committed",
        "nothing was committed",
    )
    if any(marker in normalized for marker in negation_markers):
        return False
    return any(marker in normalized for marker in positive_commit_markers)


def _minimal_concrete_remaining_claim(reply_text: str, remaining_kcal: Any) -> bool:
    try:
        value = int(remaining_kcal)
    except (TypeError, ValueError):
        return False
    normalized = " ".join(reply_text.lower().split())
    candidates = (
        f"{value} kcal",
        f"{value}kcal",
        f"remaining {value}",
        f"remain {value}",
    )
    return any(candidate in normalized for candidate in candidates)


def enforce_intake_output_honesty(
    *,
    assistant_message: str,
    state_delta: dict[str, Any] | None,
    sidecar: dict[str, Any] | None,
    phase_a_trace: dict[str, Any] | None,
    manager_final_action: str | None,
    persistence_result: Any | None,
) -> IntakeOutputHonestyResult:
    updated_trace = dict(phase_a_trace or {})
    updated_state_delta = _copy_dict(state_delta)
    updated_sidecar = _copy_dict(sidecar)
    sidecar_summary = _copy_dict(updated_sidecar.get("state_mutation_summary"))

    preflight = updated_trace.get("phase_a_commit_boundary_preflight")
    preflight = dict(preflight) if isinstance(preflight, dict) else {}
    commit_decision = _projection_commit_decision(updated_trace)

    preflight_blocked = preflight.get("blocked") is True
    final_action = str(manager_final_action or "no_commit")
    manager_no_commit = final_action == "no_commit"
    canonical_commit_present = _result_field(persistence_result, "canonical_commit") is not None

    intent = str(commit_decision.get("intent") or "")
    canonical_write_allowed = commit_decision.get("canonical_write_allowed")
    ledger_mutation_allowed = commit_decision.get("ledger_mutation_allowed")

    reasons: list[str] = []
    affected_surfaces: list[str] = []

    if preflight_blocked or manager_no_commit:
        if _clear_flags(updated_state_delta, _ALL_MUTATION_FLAGS):
            affected_surfaces.append("state_delta")
        if _clear_flags(sidecar_summary, _ALL_MUTATION_FLAGS):
            affected_surfaces.append("sidecar.state_mutation_summary")
        reasons.append("structured_state_delta_no_commit")
    else:
        canonical_disallowed = (
            canonical_write_allowed is False
            or intent in {"draft", "no_mutation"}
            or not canonical_commit_present
        )
        ledger_disallowed = ledger_mutation_allowed is False or not canonical_commit_present
        if canonical_disallowed:
            if _clear_flags(updated_state_delta, _CANONICAL_STATE_FLAGS):
                affected_surfaces.append("state_delta")
            if _clear_flags(sidecar_summary, _CANONICAL_STATE_FLAGS):
                affected_surfaces.append("sidecar.state_mutation_summary")
            reasons.append("structured_state_delta_no_canonical_commit")
        if ledger_disallowed:
            if _clear_flags(updated_state_delta, _LEDGER_STATE_FLAGS):
                affected_surfaces.append("state_delta")
            if _clear_flags(sidecar_summary, _LEDGER_STATE_FLAGS):
                affected_surfaces.append("sidecar.state_mutation_summary")
            reasons.append("structured_state_delta_no_ledger_mutation")

    text_check_used = False
    updated_message = assistant_message
    if (
        (preflight_blocked or manager_no_commit or not bool(updated_state_delta.get("canonical_commit")))
        and _minimal_false_commit_claim(assistant_message)
    ):
        updated_message = SAFE_NO_COMMIT_REPLY
        affected_surfaces.append("assistant_message")
        reasons.append("reply_false_commit_claim_removed")
        text_check_used = True

    if sidecar_summary:
        updated_sidecar["state_mutation_summary"] = sidecar_summary

    normalized = bool(affected_surfaces)
    updated_trace = _add_trace(
        updated_trace,
        normalized=normalized,
        reasons=list(dict.fromkeys(reasons)),
        affected_surfaces=list(dict.fromkeys(affected_surfaces)),
        text_check_used=text_check_used,
    )
    return IntakeOutputHonestyResult(
        assistant_message=updated_message,
        state_delta=updated_state_delta,
        sidecar=updated_sidecar,
        phase_a_trace=updated_trace,
    )


def enforce_budget_output_honesty(
    *,
    reply_text: str,
    remaining_budget: Any | None,
    active_body_plan_present: bool,
    phase_a_trace: dict[str, Any] | None,
) -> BudgetOutputHonestyResult:
    updated_trace = dict(phase_a_trace or {})
    status = str(_result_field(remaining_budget, "status") or "")
    degraded = status == "onboarding_required" or not active_body_plan_present
    concrete_remaining_allowed = not degraded
    budget_answer_mode = "degraded" if degraded else "ready"

    reasons: list[str] = []
    affected_surfaces: list[str] = []
    updated_reply = reply_text
    text_check_used = False

    if not concrete_remaining_allowed and _minimal_concrete_remaining_claim(
        reply_text,
        _result_field(remaining_budget, "remaining_kcal"),
    ):
        updated_reply = SAFE_DEGRADED_BUDGET_REPLY
        reasons.append("degraded_budget_concrete_remaining_removed")
        affected_surfaces.append("assistant_message")
        text_check_used = True

    updated_trace = _add_trace(
        updated_trace,
        normalized=bool(affected_surfaces),
        reasons=reasons,
        affected_surfaces=affected_surfaces,
        text_check_used=text_check_used,
        budget_answer_mode=budget_answer_mode,
        concrete_remaining_kcal_allowed=concrete_remaining_allowed,
    )
    return BudgetOutputHonestyResult(reply_text=updated_reply, phase_a_trace=updated_trace)


__all__ = [
    "BudgetOutputHonestyResult",
    "IntakeOutputHonestyResult",
    "SAFE_DEGRADED_BUDGET_REPLY",
    "SAFE_NO_COMMIT_REPLY",
    "enforce_budget_output_honesty",
    "enforce_intake_output_honesty",
]
