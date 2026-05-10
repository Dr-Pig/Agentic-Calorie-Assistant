from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping

from app.runtime.contracts.pending_meal_intent import PendingMealIntent
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.pending_intent_handoff_shadow"
)

OFFER_ARTIFACT = "recommendation_offer_shadow_packet"
ALLOWED_EVENT_TYPE = "recommendation_acceptance"
ALLOWED_ACCEPTANCE_KIND = "pending_meal_intent"
INTAKE_COMMIT_ACCEPTANCE_KINDS = {"intake_commit_request", "log_eaten"}
ALLOWED_SURFACES = {"chat", "recommendation_card", "menu_scan", "unknown"}
FALSE_FLAGS = {
    "runtime_effect_allowed": False,
    "recommendation_served": False,
    "user_facing_behavior_changed": False,
    "intake_commit_requested": False,
    "intake_handoff_created": False,
    "recommendation_intent_state_created": False,
    "meal_thread_mutated": False,
    "ledger_entry_created": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "durable_memory_written": False,
    "manager_context_packet_changed": False,
    "manager_context_injected": False,
    "proactive_sent": False,
    "canonical_product_mutation_allowed": False,
}


def build_recommendation_pending_intent_shadow_packet(
    *,
    offer_shadow_packet: Mapping[str, Any],
    acceptance_event: Mapping[str, Any],
    user_id: str,
    created_at: datetime,
    expiry_hours: int = 6,
) -> dict[str, Any]:
    blockers = offer_blockers(offer_shadow_packet) + acceptance_blockers(acceptance_event)
    selected_candidate = candidate_summary(offer_shadow_packet)
    if not selected_candidate:
        blockers.append("offer_shadow_packet.selected_candidate_missing")

    if blockers:
        return artifact(
            status="blocked",
            blockers=blockers,
            selected_candidate=None,
            pending_meal_intent=None,
            pending_meal_intent_trace={},
            acceptance_trace=acceptance_trace(acceptance_event, accepted=False),
            created_at=created_at,
            expires_at=None,
        )

    expires_at = created_at + timedelta(hours=expiry_hours)
    intent = PendingMealIntent(
        intent_id=intent_id(selected_candidate["candidate_id"], acceptance_event),
        user_id=user_id,
        candidate_title=selected_candidate["title"],
        source_surface=source_surface(acceptance_event),
        status="created",
        created_at=created_at,
        expires_at=expires_at,
        candidate_metadata={
            "candidate_id": selected_candidate["candidate_id"],
            "store_name": selected_candidate["store_name"],
            "estimated_kcal": selected_candidate["estimated_kcal"],
            "source_refs": selected_candidate["source_refs"],
        },
    )
    return artifact(
        status="pass",
        blockers=[],
        selected_candidate=selected_candidate,
        pending_meal_intent=pending_intent_payload(intent),
        pending_meal_intent_trace=intent.to_trace_payload(),
        acceptance_trace=acceptance_trace(acceptance_event, accepted=True),
        created_at=created_at,
        expires_at=expires_at,
    )


def artifact(
    *,
    status: str,
    blockers: list[str],
    selected_candidate: dict[str, Any] | None,
    pending_meal_intent: dict[str, Any] | None,
    pending_meal_intent_trace: dict[str, Any],
    acceptance_trace: dict[str, Any],
    created_at: datetime,
    expires_at: datetime | None,
) -> dict[str, Any]:
    return {
        "artifact_type": "recommendation_pending_meal_intent_shadow_packet",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/recommendation",
        "consumer": "future_chat_first_short_term_context_shadow_review",
        "retirement_trigger": "approved_recommendation_intake_handoff_runtime_contract",
        "selected_candidate": selected_candidate,
        "pending_meal_intent": pending_meal_intent,
        "pending_meal_intent_trace": pending_meal_intent_trace,
        "pending_meal_intent_created": status == "pass" and pending_meal_intent is not None,
        "acceptance_trace": acceptance_trace,
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "blockers": blockers,
        "local_only": True,
        "diagnostic_only": True,
        "shadow_only": True,
        "non_claims": [
            "not_recommendation_serving",
            "not_user_facing_response",
            "not_recommendation_intent_state",
            "not_intake_commit",
            "not_meal_thread_mutation",
            "not_runtime_activation_evidence",
        ],
        **dict(FALSE_FLAGS),
    }


def offer_blockers(offer: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if offer.get("artifact_type") != OFFER_ARTIFACT:
        blockers.append("offer_shadow_packet.unsupported_artifact_type")
    if offer.get("status") != "pass":
        blockers.append("offer_shadow_packet.status_not_pass")
    ux_packet = mapping(offer.get("ux_packet"))
    if ux_packet.get("serve_allowed") is not False:
        blockers.append("offer_shadow_packet.serve_allowed_not_false")
    for flag in FALSE_FLAGS:
        if offer.get(flag) is True:
            blockers.append(f"offer_shadow_packet.{flag}")
    return blockers


def acceptance_blockers(event: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if event.get("event_type") != ALLOWED_EVENT_TYPE:
        blockers.append("acceptance_event.event_type_missing")
    kind = str(event.get("acceptance_kind") or "")
    if kind in INTAKE_COMMIT_ACCEPTANCE_KINDS:
        blockers.append("acceptance_event.intake_commit_request_not_pending_intent")
    if kind != ALLOWED_ACCEPTANCE_KIND:
        blockers.append("acceptance_event.acceptance_kind_not_pending_meal_intent")
    if source_surface(event) not in ALLOWED_SURFACES:
        blockers.append("acceptance_event.source_surface_unsupported")
    return blockers


def acceptance_trace(event: Mapping[str, Any], *, accepted: bool) -> dict[str, Any]:
    return {
        "acceptance_required": True,
        "explicit_acceptance_observed": accepted,
        "event_type": str(event.get("event_type") or ""),
        "acceptance_kind": str(event.get("acceptance_kind") or ""),
        "source_surface": source_surface(event),
        "user_action_id": user_action_id(event),
        "raw_user_input_classified_upstream": True,
    }


def candidate_summary(offer: Mapping[str, Any]) -> dict[str, Any] | None:
    primary = mapping(offer.get("selected_primary"))
    if not primary:
        return None
    return {
        "candidate_id": str(primary.get("candidate_id") or ""),
        "title": str(primary.get("title") or ""),
        "store_name": str(primary.get("store_name") or ""),
        "estimated_kcal": primary.get("estimated_kcal")
        if isinstance(primary.get("estimated_kcal"), int)
        else None,
        "source_refs": source_refs(primary),
    }


def pending_intent_payload(intent: PendingMealIntent) -> dict[str, Any]:
    payload = intent.model_dump(mode="json")
    payload["contract_scope"] = "pending_meal_intent_only"
    return payload


def intent_id(candidate_id: str, event: Mapping[str, Any]) -> str:
    return f"pending-meal-{candidate_id}-{user_action_id(event)}"


def user_action_id(event: Mapping[str, Any]) -> str:
    value = str(event.get("user_action_id") or "untracked-action")
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)


def source_surface(event: Mapping[str, Any]) -> str:
    return str(event.get("source_surface") or "unknown")


def source_refs(candidate: Mapping[str, Any]) -> list[str]:
    return [
        str(ref)
        for ref in candidate.get("source_refs") or []
        if str(ref).startswith("memory_candidate:")
    ]


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
