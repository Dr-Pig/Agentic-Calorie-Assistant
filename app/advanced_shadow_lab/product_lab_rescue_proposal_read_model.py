from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_rescue_proposal_rows import (
    active_row,
    history_row,
    rescue_decision_packets,
    rescue_messages,
)


CLOSED_STATUSES = {"dismissed", "accepted_pending_commit_confirmation"}


def empty() -> dict[str, Any]:
    return _artifact(active_rows=[], history_rows=[], blockers=[])


def update(
    prior_model: Mapping[str, Any],
    turn_id: str,
    turn_artifact: Mapping[str, Any],
    chat_action_outcomes: list[Mapping[str, Any]],
) -> dict[str, Any]:
    history_rows = [
        *rows(prior_model, "history_rows"),
        *[
            history_row(turn_id, packet)
            for packet in rescue_decision_packets(chat_action_outcomes)
        ],
    ]
    closed_candidate_ids = {
        str(row.get("candidate_id") or "")
        for row in history_rows
        if row.get("lifecycle_status") in CLOSED_STATUSES
    }
    active_rows = [
        row
        for row in rows(prior_model, "active_inbox_rows")
        if str(row.get("candidate_id") or "") not in closed_candidate_ids
    ]
    for message in rescue_messages(turn_artifact):
        candidate_id = str(message.get("candidate_id") or "")
        if candidate_id not in closed_candidate_ids:
            active_rows = upsert_row(active_rows, active_row(turn_id, message))
    return _artifact(active_rows=active_rows, history_rows=history_rows, blockers=[])


def attach(
    artifact: Mapping[str, Any],
    read_model: Mapping[str, Any],
) -> dict[str, Any]:
    model = dict(read_model)
    return {
        **dict(artifact),
        "lab_rescue_proposal_read_model": model,
        "lab_rescue_active_inbox_count": len(model.get("active_inbox_rows") or []),
        "lab_rescue_history_count": len(model.get("history_rows") or []),
        "lab_rescue_history_statuses": [
            str(row.get("lifecycle_status") or "")
            for row in model.get("history_rows") or []
        ],
        "lab_rescue_history_source_refs": [
            str(ref)
            for row in model.get("history_rows") or []
            for ref in row.get("source_refs") or []
        ],
    }


def rows(model: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    return [dict(row) for row in model.get(key) or [] if isinstance(row, Mapping)]


def upsert_row(rows_: list[dict[str, Any]], row: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        *[item for item in rows_ if item.get("candidate_id") != row["candidate_id"]],
        row,
    ]


def _artifact(
    *,
    active_rows: list[Mapping[str, Any]],
    history_rows: list[Mapping[str, Any]],
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_rescue_proposal_read_model",
        "status": "blocked" if blockers else "pass",
        "active_inbox_rows": [dict(row) for row in active_rows],
        "history_rows": [dict(row) for row in history_rows],
        "active_inbox_count": len(active_rows),
        "history_count": len(history_rows),
        "raw_trace_included": False,
        "sidecar_diagnostic_included": False,
        "served_to_mainline_user": False,
        "scheduler_delivery_allowed": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


__all__ = [
    "attach",
    "empty",
    "update",
]
