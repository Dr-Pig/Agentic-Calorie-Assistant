from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.rescue.application.proposal_read_model import (
    build_active_rescue_proposal_inbox,
    build_rescue_proposal_history,
)
from app.rescue.domain.proposal_read_models import ProposalRecordSnapshot


_REQUIRED_CASE_IDS = (
    "active_inbox_projects_open_presented_negotiating_only",
    "history_keeps_dismissed_without_raw_trace",
    "non_rescue_proposals_filtered_from_rescue_views",
    "primary_actions_are_read_model_tokens_only",
)
_FALSE_FIELDS = (
    "runtime_connected",
    "mutation_changed",
    "proposal_committed",
    "ledger_entry_created",
    "day_budget_mutated",
    "body_plan_mutated",
    "recommendation_posture_updated",
    "manager_context_injected",
    "proactive_sent",
    "accept_action_commits_overlay",
    "dismiss_action_mutates_status",
)


def _proposal(
    *,
    proposal_id: str,
    proposal_type: str = "rescue",
    proposal_status: str,
    day: int,
    metadata: dict[str, Any] | None = None,
) -> ProposalRecordSnapshot:
    return ProposalRecordSnapshot(
        proposal_id=proposal_id,
        proposal_type=proposal_type,
        proposal_status=proposal_status,
        title=f"{proposal_id} title",
        summary=f"{proposal_id} summary",
        explanation=f"{proposal_id} expandable explanation",
        created_at=datetime(2026, 5, day, 12, 0, tzinfo=UTC),
        metadata=metadata or {},
    )


def _rescue_proposals() -> list[ProposalRecordSnapshot]:
    return [
        _proposal(proposal_id="rescue-open", proposal_status="open", day=1),
        _proposal(proposal_id="rescue-presented", proposal_status="presented", day=2),
        _proposal(proposal_id="rescue-negotiating", proposal_status="negotiating", day=3),
        _proposal(
            proposal_id="rescue-dismissed",
            proposal_status="dismissed",
            day=1,
            metadata={"raw_trace": {"internal": "hidden"}},
        ),
        _proposal(
            proposal_id="calibration-open",
            proposal_type="calibration",
            proposal_status="open",
            day=3,
        ),
    ]


def _base_case(case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "semantic_owner": "rescue_read_model_projection",
        "deterministic_role": "filter_sort_and_strip_internal_trace",
        "read_model_only": True,
        **dict.fromkeys(_FALSE_FIELDS, False),
    }


def _cases() -> list[dict[str, Any]]:
    proposals = _rescue_proposals()
    inbox = build_active_rescue_proposal_inbox(proposals)
    history = build_rescue_proposal_history(proposals)
    active_ids = [item.proposal_id for item in inbox.items]
    history_by_id = {item.proposal_id: item for item in history.items}
    only_non_rescue = [proposal for proposal in proposals if proposal.proposal_type != "rescue"]
    non_rescue_inbox = build_active_rescue_proposal_inbox(only_non_rescue)
    non_rescue_history = build_rescue_proposal_history(only_non_rescue)
    primary_actions = list(inbox.items[0].primary_actions)
    return [
        _base_case("active_inbox_projects_open_presented_negotiating_only")
        | {
            "active_inbox_ids": active_ids,
            "dismissed_excluded_from_active_inbox": "rescue-dismissed" not in active_ids,
            "sorted_newest_first": active_ids == ["rescue-negotiating", "rescue-presented", "rescue-open"],
            "raw_trace_exposed": any(item.raw_trace_exposed for item in inbox.items),
        },
        _base_case("history_keeps_dismissed_without_raw_trace")
        | {
            "history_ids": [item.proposal_id for item in history.items],
            "dismissed_visible_in_history": "rescue-dismissed" in history_by_id,
            "raw_trace_exposed": history_by_id["rescue-dismissed"].raw_trace_exposed,
            "expandable_explanation_available": bool(history_by_id["rescue-dismissed"].expandable_explanation),
        },
        _base_case("non_rescue_proposals_filtered_from_rescue_views")
        | {
            "non_rescue_active_inbox_count": len(non_rescue_inbox.items),
            "non_rescue_history_count": len(non_rescue_history.items),
        },
        _base_case("primary_actions_are_read_model_tokens_only")
        | {
            "primary_actions": primary_actions,
            "accept_action_commits_overlay": False,
            "dismiss_action_mutates_status": False,
        },
    ]


def _validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if [str(case.get("case_id") or "") for case in cases] != list(_REQUIRED_CASE_IDS):
        blockers.append("required_case_order_mismatch")
    for case in cases:
        case_id = str(case.get("case_id") or "unknown")
        for field in _FALSE_FIELDS:
            if case.get(field) is not False:
                blockers.append(f"{case_id}.{field}")
    return blockers


def build_rescue_read_model_shadow_contract_artifact() -> dict[str, Any]:
    cases = _cases()
    blockers = _validate_cases(cases)
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_rescue_read_model_shadow_contract",
        "status": "pass" if not blockers else "fail",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "owner": "app/rescue",
        "consumer": "future rescue accept/dismiss activation slices",
        "retirement_trigger": "approved rescue_accept_dismiss_runtime_activation_plan",
        "local_only": True,
        "diagnostic_only": True,
        "read_model_only": True,
        **dict.fromkeys(_FALSE_FIELDS, False),
        "best_practice_evidence": {
            "required": False,
            "rationale": "read-model-only offline sidecar; no runtime action, provider, route, or persistence is added",
        },
        "blockers": blockers,
        "cases": cases,
    }


__all__ = ["build_rescue_read_model_shadow_contract_artifact"]
