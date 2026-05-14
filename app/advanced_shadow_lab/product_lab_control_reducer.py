from __future__ import annotations

from typing import Any, Mapping


def candidate_states(
    *,
    candidates: list[dict[str, str]],
    journal: list[dict[str, Any]],
    lab_now_minute: int,
    observed_material_signals: list[str],
) -> list[dict[str, Any]]:
    observed = {str(signal) for signal in observed_material_signals}
    active = _active_controls(journal)
    return [
        _candidate_state(
            candidate=candidate,
            control=(
                active["by_candidate"].get(candidate["candidate_id"])
                or active["by_trigger"].get(candidate["trigger_type"])
            ),
            lab_now_minute=lab_now_minute,
            observed_material_signals=observed,
        )
        for candidate in candidates
    ]


def _active_controls(journal: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    active: dict[str, dict[str, dict[str, Any]]] = {
        "by_candidate": {},
        "by_trigger": {},
    }
    for entry in journal:
        candidate_id = str(entry.get("target_candidate_id") or "")
        trigger_type = str(entry.get("trigger_type") or "")
        scope = str(entry.get("scope") or "candidate_instance")
        action = str(entry.get("action") or "")
        if action in {"dismiss", "snooze", "opt_out"}:
            _set_active(
                active=active,
                scope=scope,
                candidate_id=candidate_id,
                trigger_type=trigger_type,
                entry=entry,
            )
        elif action in {"undo", "reopen_or_modify"}:
            _set_active(
                active=active,
                scope=scope,
                candidate_id=candidate_id,
                trigger_type=trigger_type,
                entry=entry,
            )
    return active


def _set_active(
    *,
    active: dict[str, dict[str, dict[str, Any]]],
    scope: str,
    candidate_id: str,
    trigger_type: str,
    entry: dict[str, Any],
) -> None:
    if scope == "trigger_family" and trigger_type:
        active["by_trigger"][trigger_type] = entry
        return
    if candidate_id:
        active["by_candidate"][candidate_id] = entry


def _candidate_state(
    *,
    candidate: dict[str, str],
    control: Mapping[str, Any] | None,
    lab_now_minute: int,
    observed_material_signals: set[str],
) -> dict[str, Any]:
    base = {
        "candidate_id": candidate["candidate_id"],
        "trigger_type": candidate["trigger_type"],
    }
    if control is None:
        return _visible(base, "not_suppressed", None)
    action = str(control.get("action") or "")
    if action == "undo":
        return _visible(base, "restored_by_undo", str(control.get("event_id") or ""))
    if action == "reopen_or_modify":
        return _visible(
            base,
            "restored_by_reopen_or_modify",
            str(control.get("event_id") or ""),
        )
    if action == "dismiss":
        return _dismiss_state(base, control, observed_material_signals)
    if action == "snooze":
        return _snooze_state(base, control, lab_now_minute, observed_material_signals)
    if action == "opt_out":
        return _suppressed(
            base,
            "opted_out_trigger",
            str(control.get("event_id") or ""),
        )
    return _visible(base, "not_suppressed", None)


def _dismiss_state(
    base: dict[str, str],
    control: Mapping[str, Any],
    observed_material_signals: set[str],
) -> dict[str, Any]:
    signal = str(control.get("next_signal_required") or "")
    event_id = str(control.get("event_id") or "")
    if signal and signal in observed_material_signals:
        return _visible(base, "released_by_material_signal", event_id)
    return _suppressed(base, "dismissed_until_material_signal", event_id)


def _snooze_state(
    base: dict[str, str],
    control: Mapping[str, Any],
    lab_now_minute: int,
    observed_material_signals: set[str],
) -> dict[str, Any]:
    signal = str(control.get("release_signal") or "")
    event_id = str(control.get("event_id") or "")
    if signal and signal in observed_material_signals:
        return _visible(base, "released_by_material_signal", event_id)
    if lab_now_minute >= int(control.get("snooze_release_at_minute") or 0):
        return _visible(base, "released_by_snooze_window", event_id)
    return _suppressed(base, "snoozed_until_release", event_id)


def _visible(
    base: dict[str, str],
    reason: str,
    event_id: str | None,
) -> dict[str, Any]:
    return {
        **base,
        "visible_in_lab": True,
        "suppression_reason": reason,
        "active_control_event_id": event_id,
    }


def _suppressed(
    base: dict[str, str],
    reason: str,
    event_id: str,
) -> dict[str, Any]:
    return {
        **base,
        "visible_in_lab": False,
        "suppression_reason": reason,
        "active_control_event_id": event_id,
    }
