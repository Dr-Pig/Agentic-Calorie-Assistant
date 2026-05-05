from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


REQUIRED_INPUTS = (
    "product_pages_ui_review_bundle",
    "session_context_carryover_qa_bundle",
    "contextual_interaction_matrix",
    "pl_ce_local_mvp_candidate_bundle",
)

EXPECTED_ARTIFACT_TYPES = {
    "product_pages_ui_review_bundle": "accurate_intake_product_pages_ui_review_bundle",
    "session_context_carryover_qa_bundle": "accurate_intake_session_context_carryover_qa_bundle",
    "contextual_interaction_matrix": "accurate_intake_contextual_interaction_matrix",
    "pl_ce_local_mvp_candidate_bundle": "accurate_intake_pl_ce_local_mvp_candidate_bundle",
}

EXPECTED_STATUSES = {
    "product_pages_ui_review_bundle": "product_pages_ui_review_ready_for_human_review",
    "session_context_carryover_qa_bundle": "session_context_carryover_qa_ready_for_human_review",
    "contextual_interaction_matrix": "pass",
    "pl_ce_local_mvp_candidate_bundle": "pl_ce_local_mvp_candidate_ready_for_human_review",
}

FORBIDDEN_TRUE_FLAGS = (
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "live_provider_called",
    "web_tavily_used",
    "websearch_evidence_used",
    "fooddb_evidence_used",
    "fooddb_truth_changed",
    "fooddb_truth_updated",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "manager_context_packet_schema_changed",
    "runtime_truth_changed",
    "mutation_changed",
    "mutation_authority",
    "frontend_semantic_owner",
    "frontend_selected_target",
    "deterministic_semantic_inference_used",
    "deterministic_selected_intent",
    "deterministic_selected_target",
    "raw_text_intent_router_used",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {
            "",
            "0",
            "false",
            "no",
            "none",
            "null",
            "not_available",
            "not_checked",
        }
    return True


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _input_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not payload:
        return [f"{group_id}.missing"]
    expected_type = EXPECTED_ARTIFACT_TYPES[group_id]
    if payload.get("artifact_type") != expected_type:
        blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    expected_status = EXPECTED_STATUSES[group_id]
    if _status(payload) != expected_status:
        blockers.append(f"{group_id}.unexpected_status:{_status(payload)}")
    if payload.get("blockers") not in (None, []):
        blockers.append(f"{group_id}.upstream_blockers_present")
    for flag in FORBIDDEN_TRUE_FLAGS:
        if _claim_is_true(payload.get(flag)):
            blockers.append(f"{group_id}.{flag}")
    return blockers


def _review_cards(payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "review_area": "product_pages_ui",
            "input_artifact": "product_pages_ui_review_bundle",
            "question": "Do Chat, Today, and Body render backend/read-model truth clearly enough for local MVP review?",
            "decision_options": ["proceed", "narrow", "stop"],
            "source_status": _status(payloads.get("product_pages_ui_review_bundle", {})),
        },
        {
            "review_area": "short_term_session_context",
            "input_artifact": "session_context_carryover_qa_bundle",
            "question": "Do pending follow-up, long-session pinned draft, and target-candidate context carry over enough for Manager use?",
            "decision_options": ["proceed", "narrow", "stop"],
            "source_status": _status(payloads.get("session_context_carryover_qa_bundle", {})),
        },
        {
            "review_area": "contextual_intent_support",
            "input_artifact": "contextual_interaction_matrix",
            "question": "Do same-utterance context variants preserve ambiguity and keep fixture Manager as semantic owner?",
            "decision_options": ["proceed", "narrow", "stop"],
            "source_status": _status(payloads.get("contextual_interaction_matrix", {})),
        },
        {
            "review_area": "local_mvp_candidate_boundary",
            "input_artifact": "pl_ce_local_mvp_candidate_bundle",
            "question": "Is this still local diagnostic evidence only, with no FoodDB/live/readiness claim?",
            "decision_options": ["proceed", "narrow", "stop"],
            "source_status": _status(payloads.get("pl_ce_local_mvp_candidate_bundle", {})),
        },
    ]


def build_pl_ce_reviewer_cockpit_artifact(
    input_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    payloads = {group_id: _object_dict(input_artifacts.get(group_id)) for group_id in REQUIRED_INPUTS}
    blockers: list[str] = []
    for group_id in sorted(set(input_artifacts) - set(REQUIRED_INPUTS)):
        blockers.append(f"unexpected_input:{group_id}")
    for group_id, payload in payloads.items():
        blockers.extend(_input_blockers(group_id, payload))
    product_pages = payloads["product_pages_ui_review_bundle"]
    session_context = payloads["session_context_carryover_qa_bundle"]
    interaction_matrix = payloads["contextual_interaction_matrix"]
    candidate_bundle = payloads["pl_ce_local_mvp_candidate_bundle"]
    status = "pl_ce_reviewer_cockpit_ready_for_human_review" if not blockers else "blocked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_reviewer_cockpit",
            "status": status,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "local_pl_ce_reviewer_cockpit",
            "review_decision_scope": "proceed_narrow_or_stop",
            "required_inputs": list(REQUIRED_INPUTS),
            "blockers": blockers,
            "review_cards": _review_cards(payloads),
            "browser_execution_seen": product_pages.get("browser_executed") is True,
            "contextual_interaction_matrix_seen": bool(interaction_matrix),
            "session_context_carryover_seen": bool(session_context),
            "candidate_bundle_seen": bool(candidate_bundle),
            "summary": {
                "review_card_count": 4,
                "contextual_interaction_count": _object_dict(
                    interaction_matrix.get("summary")
                ).get("interaction_count"),
                "contextual_ambiguity_count": _object_dict(
                    interaction_matrix.get("summary")
                ).get("ambiguity_preserved_interactions"),
                "ready_inputs": sum(1 for payload in payloads.values() if payload),
            },
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "aggregate_only": True,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "shared_contract_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "live_provider_called": False,
            "web_tavily_used": False,
            "websearch_evidence_used": False,
            "fooddb_evidence_used": False,
            "fooddb_truth_changed": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_db_used": False,
            "manager_context_packet_schema_changed": False,
            "frontend_semantic_owner": False,
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "mutation_authority": False,
        }
    )


__all__ = ["build_pl_ce_reviewer_cockpit_artifact"]
