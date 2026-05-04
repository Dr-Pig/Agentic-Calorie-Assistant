from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.rescue.application.proposal_read_model import (
    build_active_rescue_proposal_inbox,
    build_rescue_proposal_history,
)
from app.rescue.domain.proposal_read_models import ProposalRecordSnapshot
from app.rescue.domain.proposal_read_models import RescueProposalReadItem


def test_active_inbox_filters_out_dismissed_rescue_proposals() -> None:
    proposals = [
        ProposalRecordSnapshot(
            proposal_id="p1",
            proposal_type="rescue",
            proposal_status="open",
            title="Recover 450 kcal over 3 days",
            summary="Reduce about 150 kcal per day.",
            explanation="This keeps the adjustment below the daily safety threshold.",
            created_at=datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc),
        ),
        ProposalRecordSnapshot(
            proposal_id="p2",
            proposal_type="rescue",
            proposal_status="dismissed",
            title="Recover 300 kcal over 2 days",
            summary="Reduce about 150 kcal per day.",
            explanation="Dismissed by the user for this instance.",
            created_at=datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc),
        ),
    ]

    inbox = build_active_rescue_proposal_inbox(proposals)

    assert [item.proposal_id for item in inbox.items] == ["p1"]
    assert inbox.items[0].primary_actions == []
    assert inbox.items[0].action_surface == "read_only_shadow_status"
    assert inbox.items[0].formal_commit_handler_bound is False


def test_history_keeps_dismissed_proposal_with_expandable_explanation() -> None:
    proposal = ProposalRecordSnapshot(
        proposal_id="p2",
        proposal_type="rescue",
        proposal_status="dismissed",
        title="Recover 300 kcal over 2 days",
        summary="Reduce about 150 kcal per day.",
        explanation="The proposal was dismissed for the current instance.",
        created_at=datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc),
        metadata={"raw_trace": {"internal": "hidden"}},
    )

    history = build_rescue_proposal_history([proposal])

    assert len(history.items) == 1
    assert history.items[0].proposal_status == "dismissed"
    assert history.items[0].expandable_explanation == proposal.explanation
    assert history.items[0].raw_trace_exposed is False


def test_read_model_does_not_project_non_rescue_proposals_into_rescue_views() -> None:
    proposal = ProposalRecordSnapshot(
        proposal_id="p3",
        proposal_type="calibration",
        proposal_status="open",
        title="Adjust daily budget",
        summary="Calibration proposal.",
        explanation="Not rescue.",
        created_at=datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc),
    )

    assert build_active_rescue_proposal_inbox([proposal]).items == []
    assert build_rescue_proposal_history([proposal]).items == []


def test_active_inbox_accepts_presented_and_negotiating_and_sorts_newest_first() -> None:
    older = ProposalRecordSnapshot(
        proposal_id="p4",
        proposal_type="rescue",
        proposal_status="presented",
        title="Recover over 4 days",
        summary="Smaller daily adjustment.",
        explanation="Presented to the user.",
        created_at=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
    )
    newer = ProposalRecordSnapshot(
        proposal_id="p5",
        proposal_type="rescue",
        proposal_status="negotiating",
        title="Recover over 3 days",
        summary="Negotiation in progress.",
        explanation="User asked for a lighter plan.",
        created_at=datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc),
    )

    inbox = build_active_rescue_proposal_inbox([older, newer])

    assert [item.proposal_id for item in inbox.items] == ["p5", "p4"]
    assert all(item.primary_actions == [] for item in inbox.items)
    assert all(item.action_surface == "read_only_shadow_status" for item in inbox.items)


def test_rescue_proposal_read_item_rejects_primary_actions() -> None:
    with pytest.raises(ValidationError):
        RescueProposalReadItem(
            proposal_id="p6",
            proposal_status="open",
            title="Recover over 3 days",
            summary="Shadow status only.",
            expandable_explanation="No live accept handler is bound.",
            primary_actions=["accept_rescue_plan"],
            created_at=datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc),
        )
