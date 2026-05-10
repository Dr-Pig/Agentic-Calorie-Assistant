from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS


SUPPORTED_ACTIONS = {"dismiss", "snooze", "undo"}


def build_new_control_entries(
    *,
    session_id: str,
    turn_id: str,
    lab_now_minute: int,
    candidate_ids: set[str],
    prior_entries: list[dict[str, Any]],
    events: list[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    blockers: list[str] = []
    for index, event in enumerate(events):
        entry, event_blockers = _entry(
            session_id=session_id,
            turn_id=turn_id,
            lab_now_minute=lab_now_minute,
            candidate_ids=candidate_ids,
            prior_entries=[*prior_entries, *entries],
            event=event,
            index=index,
        )
        blockers.extend(event_blockers)
        if not event_blockers:
            entries.append(entry)
    return entries, blockers


def _entry(
    *,
    session_id: str,
    turn_id: str,
    lab_now_minute: int,
    candidate_ids: set[str],
    prior_entries: list[dict[str, Any]],
    event: Mapping[str, Any],
    index: int,
) -> tuple[dict[str, Any], list[str]]:
    action = str(event.get("action") or "")
    candidate_id = str(event.get("target_candidate_id") or "")
    blockers = _event_blockers(event, index, action, candidate_id, candidate_ids)
    undo_event_id = str(event.get("undo_event_id") or "")
    if action == "undo" and not _has_target_control(
        prior_entries,
        candidate_id,
        undo_event_id,
    ):
        blockers.append(f"control_event[{index}].undo_target_not_active")
    return {
        "artifact_type": "advanced_product_lab_control_journal_entry",
        "event_id": str(event.get("event_id") or ""),
        "session_id": session_id,
        "turn_id": turn_id,
        "action": action,
        "target_candidate_id": candidate_id,
        "trigger_type": str(event.get("trigger_type") or ""),
        "scope": str(event.get("scope") or "candidate_instance"),
        "dismiss_reason": event.get("dismiss_reason") if action == "dismiss" else None,
        "next_signal_required": str(event.get("next_signal_required") or ""),
        "snooze_minutes": event.get("snooze_minutes") if action == "snooze" else None,
        "snooze_release_at_minute": (
            lab_now_minute + int(event.get("snooze_minutes") or 0)
            if action == "snooze"
            else None
        ),
        "release_signal": str(event.get("release_signal") or ""),
        "undo_event_id": undo_event_id if action == "undo" else None,
        "raw_user_text_semantic_inference_performed": False,
        **dict(FALSE_FLAGS),
    }, blockers


def _event_blockers(
    event: Mapping[str, Any],
    index: int,
    action: str,
    candidate_id: str,
    candidate_ids: set[str],
) -> list[str]:
    blockers: list[str] = []
    prefix = f"control_event[{index}]"
    if not str(event.get("event_id") or ""):
        blockers.append(f"{prefix}.event_id_missing")
    if action not in SUPPORTED_ACTIONS:
        blockers.append(f"{prefix}.action_unsupported:{action}")
    if not candidate_id:
        blockers.append(f"{prefix}.target_candidate_id_missing")
    elif candidate_id not in candidate_ids:
        blockers.append(f"{prefix}.target_candidate_id_unknown:{candidate_id}")
    if not str(event.get("trigger_type") or ""):
        blockers.append(f"{prefix}.trigger_type_missing")
    if action == "dismiss" and not str(event.get("next_signal_required") or ""):
        blockers.append(f"{prefix}.next_signal_required_missing")
    if action == "snooze" and int(event.get("snooze_minutes") or 0) <= 0:
        blockers.append(f"{prefix}.snooze_minutes_missing")
    return blockers


def _has_target_control(
    entries: list[dict[str, Any]],
    candidate_id: str,
    undo_event_id: str,
) -> bool:
    for entry in reversed(entries):
        if entry.get("target_candidate_id") != candidate_id:
            continue
        if entry.get("event_id") != undo_event_id:
            continue
        return entry.get("action") in {"dismiss", "snooze"}
    return False
