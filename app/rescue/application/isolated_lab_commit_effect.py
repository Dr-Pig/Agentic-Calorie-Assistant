from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Mapping

from app.budget.application.effective_budget_math import (
    runtime_adjustment_delta_for_entry,
)
from app.rescue.application.isolated_lab_commit_validation import (
    PRODUCTION_DORMANT_FLAGS,
    input_blockers,
    mapping,
    to_int,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.isolated_lab_commit_effect"
)

def build_isolated_lab_rescue_commit_effect(
    *,
    accept_contract: Mapping[str, Any],
    rescue_response_card_packet: Mapping[str, Any],
    effective_from_policy: Mapping[str, Any],
    current_budget_view: Mapping[str, Any],
) -> dict[str, Any]:
    card = mapping(rescue_response_card_packet.get("rescue_response_card"))
    accepted = mapping(accept_contract.get("accepted_projection"))
    blockers = input_blockers(
        accept_contract=accept_contract,
        rescue_response_card_packet=rescue_response_card_packet,
        effective_from_policy=effective_from_policy,
        current_budget_view=current_budget_view,
        accepted=accepted,
        card=card,
    )
    if blockers:
        return _artifact(status="blocked", blockers=blockers)

    entries = _ledger_entries(
        accepted=accepted,
        card=card,
        policy=effective_from_policy,
    )
    refreshed = _refreshed_budget(current_budget_view, entries)
    return _artifact(
        status="pass",
        proposal_status_overlay=_proposal_overlay(accepted, card),
        lab_ledger_entries=entries,
        refreshed_current_budget_view=refreshed,
        rescue_commit_effect=_commit_effect(accepted, card, entries, refreshed),
    )


def _artifact(
    *,
    status: str,
    blockers: list[str] | None = None,
    proposal_status_overlay: dict[str, Any] | None = None,
    lab_ledger_entries: list[dict[str, Any]] | None = None,
    refreshed_current_budget_view: dict[str, Any] | None = None,
    rescue_commit_effect: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entries = lab_ledger_entries or []
    return {
        "artifact_type": "isolated_lab_rescue_commit_effect",
        "status": status,
        "owner": "app/rescue",
        "consumer": "proposal_inbox_history_audit_read_model",
        "proposal_status_overlay": proposal_status_overlay,
        "lab_ledger_entries": entries,
        "refreshed_current_budget_view": refreshed_current_budget_view,
        "rescue_commit_effect": rescue_commit_effect,
        "lab_enabled": True,
        "lab_isolated": True,
        "lab_runtime_effect_allowed": status == "pass",
        "lab_isolated_mutation_changed": status == "pass",
        "lab_ledger_entry_created": bool(entries),
        "lab_current_budget_view_refreshed": status == "pass",
        "blockers": blockers or [],
        **dict(PRODUCTION_DORMANT_FLAGS),
    }


def _ledger_entries(
    *,
    accepted: Mapping[str, Any],
    card: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    start_date = date.fromisoformat(str(policy["effective_from_local_date"]))
    entries: list[dict[str, Any]] = []
    for offset in range(to_int(card["recommended_days"])):
        local_date = start_date + timedelta(days=offset)
        entry_id = f"lab-rescue-overlay:{accepted['proposal_id']}:{local_date.isoformat()}"
        entries.append(
            {
                "entry_id": entry_id,
                "entry_type": "rescue_overlay",
                "user_id": str(accepted["user_id"]),
                "local_date": local_date.isoformat(),
                "delta_kcal": int(card["daily_kcal_adjustment"]),
                "source_object_type": "ProposalContainer",
                "source_object_id": str(accepted["proposal_id"]),
                "entry_status": "lab_projected",
                "effective_from": _effective_from(policy, offset),
                "created_at": str(accepted["accepted_at"]),
                "metadata": {
                    "cap_mode": str(accepted["cap_mode"]),
                    "commit_source": str(accepted["commit_source"]),
                },
            }
        )
    return entries


def _refreshed_budget(
    current_budget_view: Mapping[str, Any],
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    current_date = str(current_budget_view["local_date"])
    today_entries = [entry for entry in entries if entry["local_date"] == current_date]
    runtime_delta = sum(
        runtime_adjustment_delta_for_entry(
            entry_type=str(entry["entry_type"]),
            delta_kcal=int(entry["delta_kcal"]),
        )
        for entry in today_entries
    )
    adjustment = to_int(current_budget_view["adjustment_kcal"]) + runtime_delta
    remaining = (
        to_int(current_budget_view["budget_kcal"])
        - to_int(current_budget_view["consumed_kcal"])
        - adjustment
    )
    refreshed = dict(current_budget_view)
    refreshed.update(
        {
            "adjustment_kcal": adjustment,
            "remaining_kcal": remaining,
            "rescue_overlay_runtime_adjustment_kcal": runtime_delta,
            "source": "lab_isolated_rescue_overlay",
        }
    )
    return refreshed


def _proposal_overlay(accepted: Mapping[str, Any], card: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "proposal_id": str(accepted["proposal_id"]),
        "proposal_status": "accepted",
        "accepted_at": str(accepted["accepted_at"]),
        "accepted_option_id": str(card.get("proposal_option_id") or "primary_option"),
        "cap_mode": str(accepted["cap_mode"]),
    }


def _commit_effect(
    accepted: Mapping[str, Any],
    card: Mapping[str, Any],
    entries: list[dict[str, Any]],
    refreshed: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "proposal_id": str(accepted["proposal_id"]),
        "recommended_days": to_int(card["recommended_days"]),
        "daily_kcal_adjustment": int(card["daily_kcal_adjustment"]),
        "cap_mode": str(accepted["cap_mode"]),
        "ledger_entries_created": [entry["entry_id"] for entry in entries],
        "effective_from": entries[0]["effective_from"],
        "effective_to": entries[-1]["local_date"],
        "budget_view_refreshed": True,
        "refreshed_remaining_kcal": refreshed["remaining_kcal"],
        "recommendation_posture_updated": False,
        "recommendation_posture_update_deferred_to_pr21": True,
        "escalation_flagged": False,
    }


def _effective_from(policy: Mapping[str, Any], offset: int) -> str:
    local_date = date.fromisoformat(str(policy["effective_from_local_date"])) + timedelta(days=offset)
    start = str(policy["effective_start_local_time"] if offset == 0 else "00:00")
    return f"{local_date.isoformat()}T{start}"


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_isolated_lab_rescue_commit_effect"]
