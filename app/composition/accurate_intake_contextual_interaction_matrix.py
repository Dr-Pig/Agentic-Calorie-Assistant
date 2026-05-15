from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.composition.accurate_intake_context_conditioned_intent_wall import (
    build_context_conditioned_intent_wall_artifact,
)
from app.composition.accurate_intake_contextual_interaction_cases import (
    REQUIRED_INTERACTION_IDS,
    interactions,
    json_safe,
)
from app.composition.accurate_intake_contextual_interaction_validation import (
    validate_interactions,
)
from app.composition.accurate_intake_correction_removal_fixture_flow import (
    build_correction_removal_fixture_flow_artifact,
)
from app.composition.accurate_intake_responder_input_contract_fake_smoke import (
    build_responder_input_contract_fake_smoke_artifact,
)


_REQUIRED_INTERACTION_IDS = REQUIRED_INTERACTION_IDS
_interactions = interactions
_json_safe = json_safe
_validate = validate_interactions


def _artifact_by_id(artifact: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    return {
        str(scenario.get(key) or ""): scenario
        for scenario in artifact.get("scenarios", [])
        if isinstance(scenario, dict)
    }


def _context_wall_by_id() -> dict[str, dict[str, Any]]:
    return _artifact_by_id(build_context_conditioned_intent_wall_artifact(), "scenario_id")


def _correction_flow_by_id() -> dict[str, dict[str, Any]]:
    return _artifact_by_id(build_correction_removal_fixture_flow_artifact(), "scenario_id")


def _responder_scenarios_by_id() -> dict[str, dict[str, Any]]:
    return _artifact_by_id(build_responder_input_contract_fake_smoke_artifact(), "scenario_id")


def build_contextual_interaction_matrix_artifact() -> dict[str, Any]:
    context_wall = _context_wall_by_id()
    correction_flow = _correction_flow_by_id()
    responder_scenarios = _responder_scenarios_by_id()
    interaction_rows = interactions()
    blockers = validate_interactions(
        interaction_rows,
        context_wall=context_wall,
        correction_flow=correction_flow,
        responder_scenarios=responder_scenarios,
    )
    return json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_contextual_interaction_matrix",
            "status": "pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "local_pl_ce_short_term_context_interaction_matrix",
            "local_only": True,
            "diagnostic_only": True,
            "fixture_only": True,
            "semantic_owner": "fixture_manager_structured_decision",
            "manager_fixture_semantic_source_used": True,
            "deterministic_supplies_candidates_and_pins_only": True,
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "frontend_render_only": True,
            "frontend_semantic_owner": False,
            "frontend_raw_text_semantic_router": False,
            "frontend_selects_target": False,
            "mutation_authority": False,
            "mutation_changed": False,
            "runtime_truth_changed": False,
            "manager_context_packet_schema_changed": False,
            "shared_contract_changed": False,
            "fooddb_truth_changed": False,
            "fooddb_truth_updated": False,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "web_tavily_used": False,
            "live_llm_invoked": False,
            "production_db_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": blockers,
            "summary": {
                "interaction_count": len(interaction_rows),
                "pending_followup_interactions": sum(
                    1 for row in interaction_rows if row["pending_followup_required"]
                ),
                "target_candidate_interactions": sum(
                    1 for row in interaction_rows if row["target_candidates_required"]
                ),
                "ambiguity_preserved_interactions": sum(
                    1 for row in interaction_rows if row["ambiguity_must_be_preserved"]
                ),
                "query_no_mutation_interactions": sum(
                    1 for row in interaction_rows if row["query_no_mutation"]
                ),
                "target_update_manager_decision_interactions": sum(
                    1
                    for row in interaction_rows
                    if row["target_update_requires_manager_decision"]
                ),
            },
            "interactions": interaction_rows,
        }
    )


__all__ = ["build_contextual_interaction_matrix_artifact"]
