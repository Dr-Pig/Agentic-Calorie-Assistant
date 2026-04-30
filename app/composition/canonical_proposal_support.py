from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.shared.infra.models import ProactiveTriggerRecord, ProposalContainerRecord, ProposalOptionRecord, User


def ensure_proposal_skeleton(
    db: Session,
    *,
    user: User,
    proposal_type: str,
    option_type: str,
    option_label: str,
) -> ProposalContainerRecord:
    return ensure_proposal_artifact_skeleton(
        db,
        user=user,
        proposal_type=proposal_type,
        options=[
            {
                "option_type": option_type,
                "option_label": option_label,
                "is_primary": True,
                "rank_order": 0,
            }
        ],
    )


def ensure_proposal_artifact_skeleton(
    db: Session,
    *,
    user: User,
    proposal_type: str,
    options: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> ProposalContainerRecord:
    proposal = ProposalContainerRecord(user_id=user.id, proposal_type=proposal_type)
    proposal.metadata_json = dict(metadata or {})
    db.add(proposal)
    db.flush()
    created_options: list[ProposalOptionRecord] = []
    for index, option_payload in enumerate(options):
        option = ProposalOptionRecord(
            proposal_container_id=proposal.id,
            option_type=str(option_payload.get("option_type", "")),
            option_label=str(option_payload.get("option_label", "")),
            option_summary=str(option_payload.get("option_summary", "")),
            rank_order=int(option_payload.get("rank_order", index)),
            is_primary=bool(option_payload.get("is_primary", False)),
            effect_payload_json=dict(option_payload.get("effect_payload_json", {})),
        )
        db.add(option)
        db.flush()
        created_options.append(option)

    if created_options:
        primary = next((option for option in created_options if option.is_primary), created_options[0])
        if not primary.is_primary:
            primary.is_primary = True
        proposal.top_option_id = primary.id
    db.commit()
    db.refresh(proposal)
    return proposal


def ensure_proactive_trigger_skeleton(
    db: Session,
    *,
    user: User,
    trigger_type: str,
) -> ProactiveTriggerRecord:
    record = ProactiveTriggerRecord(user_id=user.id, trigger_type=trigger_type)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
