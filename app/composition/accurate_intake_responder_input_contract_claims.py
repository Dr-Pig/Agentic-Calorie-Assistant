from __future__ import annotations

import json
from typing import Any

from app.composition.responder_macro_claim_contract import (
    FORBIDDEN_MACRO_CLAIMS_CONTRACT,
    INVENTION_BLOCKERS_BY_MACRO_CLAIM_TYPE,
)


FORBIDDEN_CLAIM_TYPES = {
    "readiness",
    "self_use_approval",
    "fooddb_truth",
    "web_truth",
    "selected_target",
}

FORBIDDEN_CLAIMS_CONTRACT = [
    "logged_status_without_allowed_fact",
    "kcal_without_allowed_fact",
    "remaining_without_allowed_fact",
    "exactness_without_allowed_fact",
    *FORBIDDEN_MACRO_CLAIMS_CONTRACT,
    "selected_target_without_manager_decision",
    "readiness_or_self_use_approval",
]

INVENTION_BLOCKER_BY_CLAIM_TYPE = {
    "logged_status": "invented_logged_status",
    "kcal": "invented_kcal_claim",
    "remaining": "invented_remaining_claim",
    "exactness": "invented_exactness_claim",
    **INVENTION_BLOCKERS_BY_MACRO_CLAIM_TYPE,
    "selected_target": "invented_target_selection",
}


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def fact(
    fact_id: str,
    claim_type: str,
    value: Any,
    *,
    source: str = "backend_structured_read_model",
) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "claim_type": claim_type,
        "value": value,
        "source": source,
        "read_only": True,
        "mutation_authority": False,
    }


def claim(claim_type: str, fact_id: str, value: Any) -> dict[str, Any]:
    return {"claim_type": claim_type, "fact_id": fact_id, "value": value}


def allowed_fact_map(allowed_facts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(fact_row.get("fact_id") or ""): fact_row for fact_row in allowed_facts}


def evaluate_response(
    *,
    response: dict[str, Any],
    allowed_facts: dict[str, dict[str, Any]],
    budget_status: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    normalized_claims: list[dict[str, Any]] = []
    claims = response.get("claims", [])
    if not isinstance(claims, list) or not claims:
        blockers.append("claims_missing")
        claims = []
    for claim_row in claims:
        if not isinstance(claim_row, dict):
            blockers.append("claim_not_structured_object")
            continue
        claim_type = str(claim_row.get("claim_type") or "")
        fact_id = str(claim_row.get("fact_id") or "")
        allowed_fact = allowed_facts.get(fact_id)
        normalized_claims.append(
            {
                "claim_type": claim_type,
                "fact_id": fact_id,
                "value": claim_row.get("value"),
                "allowed_fact_present": allowed_fact is not None,
            }
        )
        if claim_type in FORBIDDEN_CLAIM_TYPES:
            if claim_type == "readiness":
                blockers.append("readiness_claim_forbidden")
            elif claim_type == "selected_target":
                blockers.append("invented_target_selection")
            else:
                blockers.append(f"{claim_type}_claim_forbidden")
        if allowed_fact is None:
            blockers.append("claim_fact_id_not_allowed")
            invention_blocker = INVENTION_BLOCKER_BY_CLAIM_TYPE.get(claim_type)
            if invention_blocker is not None:
                blockers.append(invention_blocker)
            continue
        if allowed_fact.get("claim_type") != claim_type:
            blockers.append("claim_type_does_not_match_allowed_fact")
        if allowed_fact.get("value") != claim_row.get("value"):
            blockers.append("claim_value_does_not_match_allowed_fact")
    if budget_status != "ready":
        for claim_row in response.get("claims", []):
            if isinstance(claim_row, dict) and claim_row.get("claim_type") == "remaining":
                blockers.append("degraded_budget_concrete_remaining_forbidden")
    blockers = sorted(set(blockers))
    return json_safe(
        {
            "response_id": response.get("response_id"),
            "verdict": "accepted" if not blockers else "blocked",
            "blockers": blockers,
            "claims": normalized_claims,
            "structured_claims_used": True,
            "raw_text_claim_grading_used": False,
        }
    )


__all__ = [
    "FORBIDDEN_CLAIMS_CONTRACT",
    "allowed_fact_map",
    "claim",
    "evaluate_response",
    "fact",
    "json_safe",
]
