from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.shared.infra.json_artifacts import read_json_artifact


def build_recommendation_proactive_feedback_e2e_report(
    session_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    records = _turn_records(session_artifact)
    first = records[0] if records else {}
    second = records[1] if len(records) > 1 else {}
    summary = _journey_summary(first, second)
    blockers = [
        *_session_blockers(session_artifact),
        *_summary_blockers(summary),
    ]
    return {
        "artifact_type": (
            "advanced_product_lab_recommendation_proactive_feedback_e2e_report"
        ),
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "journey_summary": summary,
        "visible_candidate_ids_by_turn": _visible_candidate_ids(session_artifact),
        "feedback_projection_types": _feedback_projection_types(first),
        "mainline_activation_enabled": False,
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "blockers": blockers,
    }


def _turn_records(session_artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        _mapping(read_json_artifact(Path(path)))
        for path in session_artifact.get("turn_artifact_paths") or []
    ]


def _journey_summary(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
) -> dict[str, Any]:
    first_turn = _turn_artifact(first)
    second_turn = _turn_artifact(second)
    return {
        "recommendation_selected_primary_id": _selected_primary_id(first_turn),
        "recommendation_proactive_candidate_visible_turn_1": (
            "recommendation_prompt:0" in _visible_ids(first_turn)
        ),
        "feedback_event_projected": bool(_feedback_projection_types(first)),
        "recommendation_proactive_candidate_suppressed_turn_2": (
            "recommendation_prompt:0" not in _visible_ids(second_turn)
            and _has_omission(second_turn, "recommendation_prompt")
        ),
        "dashboard_mirror_suppressed_card_visible_turn_2": _dashboard_has_suppressed(
            second_turn,
            "recommendation_prompt",
        ),
    }


def _summary_blockers(summary: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if summary.get("recommendation_selected_primary_id") != "golden-1":
        blockers.append("recommendation.selected_primary_not_golden_1")
    for key, value in summary.items():
        if key == "recommendation_selected_primary_id":
            continue
        if value is not True:
            blockers.append(f"journey.{key}_not_true")
    return blockers


def _session_blockers(session_artifact: Mapping[str, Any]) -> list[str]:
    if session_artifact.get("status") == "pass":
        return []
    return [
        f"session.{blocker}" for blocker in session_artifact.get("blockers") or []
    ] or ["session.status_not_pass"]


def _selected_primary_id(turn_artifact: Mapping[str, Any]) -> str:
    recommendation = _mapping(turn_artifact.get("product_lab_recommendation_artifact"))
    synthesis = _mapping(recommendation.get("offer_synthesis"))
    primary = _mapping(synthesis.get("selected_primary"))
    return str(primary.get("candidate_id") or "")


def _visible_candidate_ids(session_artifact: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        str(row.get("turn_id") or ""): [
            str(item) for item in row.get("visible_candidate_ids") or []
        ]
        for row in session_artifact.get("turn_summaries") or []
        if isinstance(row, Mapping)
    }


def _visible_ids(turn_artifact: Mapping[str, Any]) -> list[str]:
    surface = _mapping(turn_artifact.get("lab_chat_surface"))
    return [
        str(message.get("candidate_id") or "")
        for message in surface.get("messages") or []
        if isinstance(message, Mapping)
    ]


def _feedback_projection_types(record: Mapping[str, Any]) -> list[str]:
    control = _mapping(record.get("post_turn_control_state"))
    entries = [
        item
        for item in control.get("journal_entries") or []
        if isinstance(item, Mapping)
    ]
    return [
        str(projection.get("projection_type") or "")
        for entry in entries
        for projection in _mapping(
            entry.get("feedback_event_projection")
        ).get("consumer_projections", [])
        if isinstance(projection, Mapping)
    ]


def _has_omission(turn_artifact: Mapping[str, Any], trigger: str) -> bool:
    proactive = _mapping(turn_artifact.get("product_lab_proactive_artifact"))
    return any(
        _mapping(trace).get("trigger_type") == trigger
        for trace in proactive.get("omission_traces") or []
    )


def _dashboard_has_suppressed(turn_artifact: Mapping[str, Any], trigger: str) -> bool:
    mirror = _mapping(turn_artifact.get("product_lab_proactive_dashboard_mirror"))
    return any(
        _mapping(card).get("trigger_type") == trigger
        for card in mirror.get("suppressed_cards") or []
    )


def _turn_artifact(record: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(record.get("turn_artifact"))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_recommendation_proactive_feedback_e2e_report"]
