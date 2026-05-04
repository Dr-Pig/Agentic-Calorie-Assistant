from __future__ import annotations

from app.rescue.domain.proposal_read_models import (
    ActiveRescueProposalInbox,
    ProposalRecordSnapshot,
    RescueProposalHistory,
    RescueProposalReadItem,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("rescue.application.proposal_read_model")


ACTIVE_RESCUE_PROPOSAL_STATUSES = {"open", "presented", "negotiating"}


def build_active_rescue_proposal_inbox(
    proposals: list[ProposalRecordSnapshot],
) -> ActiveRescueProposalInbox:
    items = [
        _to_read_item(proposal)
        for proposal in proposals
        if _is_rescue(proposal) and proposal.proposal_status in ACTIVE_RESCUE_PROPOSAL_STATUSES
    ]
    items.sort(key=lambda item: item.created_at, reverse=True)
    return ActiveRescueProposalInbox(items=items)


def build_rescue_proposal_history(
    proposals: list[ProposalRecordSnapshot],
) -> RescueProposalHistory:
    items = [_to_read_item(proposal) for proposal in proposals if _is_rescue(proposal)]
    items.sort(key=lambda item: item.created_at, reverse=True)
    return RescueProposalHistory(items=items)


def _is_rescue(proposal: ProposalRecordSnapshot) -> bool:
    return proposal.proposal_type == "rescue"


def _to_read_item(proposal: ProposalRecordSnapshot) -> RescueProposalReadItem:
    return RescueProposalReadItem(
        proposal_id=proposal.proposal_id,
        proposal_status=proposal.proposal_status,
        title=proposal.title,
        summary=proposal.summary,
        expandable_explanation=proposal.explanation,
        raw_trace_exposed=False,
        created_at=proposal.created_at,
    )
