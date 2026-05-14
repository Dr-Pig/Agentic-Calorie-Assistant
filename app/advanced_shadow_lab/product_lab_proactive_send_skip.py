from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS


REQUEST_FIELDS = (
    ("delivery_request", "delivery_request_not_allowed"),
    ("scheduler_request", "scheduler_request_not_allowed"),
    ("notification_request", "notification_request_not_allowed"),
    ("mutation_request", "mutation_request_not_allowed"),
)
VALID_DECISIONS = {"send", "skip"}


def run_product_lab_proactive_send_skip_fixture(
    *,
    pre_delivery_review: Mapping[str, Any],
    provider_decisions: list[Mapping[str, Any]],
) -> dict[str, Any]:
    reviews = _eligible_reviews(pre_delivery_review)
    decisions_by_id = {
        str(decision.get("candidate_id") or ""): dict(decision)
        for decision in provider_decisions
        if isinstance(decision, Mapping)
    }
    blockers: list[str] = []
    rows: list[dict[str, Any]] = []
    for review in reviews:
        candidate_id = str(review.get("candidate_id") or "")
        decision = decisions_by_id.get(candidate_id)
        if decision is None:
            blockers.append(f"provider_decision[{candidate_id}].decision_missing")
            continue
        decision_blockers = _decision_blockers(candidate_id, decision)
        blockers.extend(decision_blockers)
        rows.append(_decision_row(review, decision, decision_blockers))
    status = "blocked" if blockers else "pass"
    send_rows = [
        row
        for row in rows
        if not row["blockers"] and row["send_or_skip"] == "send" and status == "pass"
    ]
    skip_rows = [
        row
        for row in rows
        if not row["blockers"] and row["send_or_skip"] == "skip" and status == "pass"
    ]
    return {
        "artifact_type": "advanced_product_lab_proactive_contextual_send_skip_fixture",
        "artifact_schema_version": "1.0",
        "status": status,
        "provider_mode": "fixture_llm_provider",
        "semantic_decision_owner": "fixture_llm_provider",
        "deterministic_role": "validate_reject_or_omit_only",
        "decision_count": len(rows),
        "decisions": rows,
        "send_candidate_ids": [row["candidate_id"] for row in send_rows],
        "skip_candidate_ids": [row["candidate_id"] for row in skip_rows],
        "omission_traces": [_skip_omission(row) for row in skip_rows],
        "blockers": blockers,
        "live_provider_used": False,
        "notification_delivery_allowed": False,
        "scheduler_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "raw_keyword_semantic_oracle_allowed": False,
        **dict(FALSE_FLAGS),
    }


def _eligible_reviews(pre_delivery_review: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        review
        for review in pre_delivery_review.get("candidate_reviews") or []
        if isinstance(review, Mapping)
        and _mapping(review.get("review_decision")).get("status")
        == "candidate_for_human_review"
    ]


def _decision_blockers(candidate_id: str, decision: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    prefix = f"provider_decision[{candidate_id}]"
    send_or_skip = str(decision.get("send_or_skip") or "")
    if send_or_skip not in VALID_DECISIONS:
        blockers.append(f"{prefix}.send_or_skip_invalid")
    if send_or_skip == "send" and not str(decision.get("chat_first_copy") or ""):
        blockers.append(f"{prefix}.chat_first_copy_missing")
    if send_or_skip == "skip" and not str(decision.get("skip_reason") or ""):
        blockers.append(f"{prefix}.skip_reason_missing")
    for field, blocker in REQUEST_FIELDS:
        if decision.get(field) is True:
            blockers.append(f"{prefix}.{blocker}")
    return blockers


def _decision_row(
    review: Mapping[str, Any],
    decision: Mapping[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "candidate_id": str(review.get("candidate_id") or ""),
        "trigger_type": str(review.get("trigger_type") or ""),
        "send_or_skip": str(decision.get("send_or_skip") or ""),
        "reason_summary": str(decision.get("reason_summary") or ""),
        "chat_first_copy": str(decision.get("chat_first_copy") or ""),
        "skip_reason": str(decision.get("skip_reason") or ""),
        "reason_codes": [str(item) for item in decision.get("reason_codes") or []],
        "source_refs": [str(item) for item in review.get("source_refs") or []],
        "blockers": blockers,
        "llm_owned_semantic_decision": True,
        "deterministic_validated": not blockers,
        "delivery_request": decision.get("delivery_request") is True,
        "scheduler_request": decision.get("scheduler_request") is True,
        "notification_request": decision.get("notification_request") is True,
        "mutation_request": decision.get("mutation_request") is True,
    }


def _skip_omission(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(row.get("candidate_id") or ""),
        "trigger_type": str(row.get("trigger_type") or ""),
        "omission_reason": f"contextual_send_skip:{row.get('skip_reason') or ''}",
        "source_refs": [str(item) for item in row.get("source_refs") or []],
        "scheduler_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["run_product_lab_proactive_send_skip_fixture"]
