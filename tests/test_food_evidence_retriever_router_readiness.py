from __future__ import annotations

from pathlib import Path

from app.nutrition.application.food_evidence_retriever_router import (
    RetrieverBackendAvailability,
    build_food_evidence_retriever_route_plan,
    build_food_evidence_retriever_route_plan_for_request,
)
from app.nutrition.application.food_evidence_retriever_router_readiness import (
    apply_websearch_status_gate_to_availability,
    build_food_evidence_retriever_router_readiness,
)
from app.nutrition.application.retrieval_intent import RetrievalIntent
from app.nutrition.application.retrieval_request import (
    build_retrieval_request_from_raw_text_hint,
)


def _exact_brand_intent() -> RetrievalIntent:
    return RetrievalIntent(
        base_dish="pearl black tea latte",
        aliases=["Milksha pearl black tea latte"],
        brand_hint="Milksha",
        size_hint="large",
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
    )


def _generic_intent() -> RetrievalIntent:
    return RetrievalIntent(
        base_dish="tea egg",
        aliases=["tea egg"],
        brand_hint=None,
        size_hint=None,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="generic_anchor_lookup",
    )


def _base_availability() -> RetrieverBackendAvailability:
    return RetrieverBackendAvailability(
        local_fooddb_index=True,
        sqlite_fts_index=True,
        websearch_candidate_lane=True,
        supabase_index=True,
    )


def _websearch_status_ready() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_evidence_status_packet_v1",
        "status": "pass",
        "summary": {
            "candidate_lane_status": "deterministic_websearch_candidate_lane_status_only",
            "candidate_lane_next_required_slice": "inspect_websearch_status_packet",
            "exact_lane_status": "clear_for_websearch_exact_candidate_chain",
            "exact_lane_next_required_slice": "inspect_websearch_exact_candidate_chain_status",
            "manager_contract_handoff_status": "websearch_contract_unblocked",
            "manager_contract_selected_next_step": "inspect_websearch_status_packet",
            "live_seam_status": "live_diagnostic_pass",
        },
        "next_required_slices": ["inspect_websearch_exact_candidate_chain_status"],
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
    }


def _websearch_status_blocked() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_evidence_status_packet_v1",
        "status": "blocked_on_candidate_lane",
        "summary": {
            "candidate_lane_status": "deterministic_websearch_candidate_lane_status_only",
            "candidate_lane_next_required_slice": "grokfast_fooddb_packet_live_diagnostic",
            "exact_lane_status": "unknown",
            "exact_lane_next_required_slice": "inspect_websearch_status_packet",
            "manager_contract_handoff_status": "not_provided",
            "manager_contract_selected_next_step": None,
            "live_seam_status": "not_provided",
        },
        "next_required_slices": ["grokfast_fooddb_packet_live_diagnostic"],
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
    }


def test_apply_websearch_status_gate_disables_exact_brand_lane_when_status_not_ready() -> None:
    gated = apply_websearch_status_gate_to_availability(
        _base_availability(),
        websearch_status_packet=_websearch_status_blocked(),
    )

    plan = build_food_evidence_retriever_route_plan(
        _exact_brand_intent(),
        availability=gated,
    )

    assert gated.websearch_candidate_lane is False
    assert plan.backend_sequence == ("sqlite_fts_index", "supabase_index", "local_fooddb_index")
    assert plan.websearch_candidate_enabled is False
    assert "no direct runtime truth from websearch" not in plan.routing_reasons


def test_apply_websearch_status_gate_enables_exact_brand_lane_after_live_clear() -> None:
    gated = apply_websearch_status_gate_to_availability(
        _base_availability(),
        websearch_status_packet=_websearch_status_ready(),
    )

    plan = build_food_evidence_retriever_route_plan(
        _exact_brand_intent(),
        availability=gated,
    )

    assert gated.websearch_candidate_lane is True
    assert plan.backend_sequence == (
        "sqlite_fts_index",
        "supabase_index",
        "local_fooddb_index",
        "websearch_candidate_lane",
    )
    assert plan.websearch_candidate_enabled is True
    assert plan.websearch_runtime_truth_allowed is False


def test_router_readiness_artifact_summarizes_gated_routes_without_runtime_truth() -> None:
    artifact = build_food_evidence_retriever_router_readiness(
        base_availability=_base_availability(),
        websearch_status_packet=_websearch_status_ready(),
    )

    assert artifact["artifact_type"] == "accurate_intake_food_evidence_retriever_router_readiness_v1"
    assert artifact["status"] == "pass"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["shared_contract_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["case_count"] == 4
    assert artifact["summary"]["fail_count"] == 0
    assert artifact["summary"]["exact_brand_websearch_ready"] is True
    assert artifact["summary"]["next_required_slice"] == "inspect_websearch_status_packet"


def test_router_readiness_artifact_keeps_generic_and_raw_hint_boundaries() -> None:
    artifact = build_food_evidence_retriever_router_readiness(
        base_availability=_base_availability(),
        websearch_status_packet=_websearch_status_ready(),
    )
    cases = {case["case_id"]: case for case in artifact["cases"]}

    assert cases["generic_fooddb_only"]["backend_sequence"] == [
        "sqlite_fts_index",
        "supabase_index",
        "local_fooddb_index",
    ]
    assert cases["generic_fooddb_only"]["websearch_candidate_enabled"] is False
    assert cases["raw_text_hint_stays_blocked"]["primary_backend"] == "blocked_no_execution"
    assert cases["raw_text_hint_stays_blocked"]["websearch_candidate_enabled"] is False


def test_router_readiness_artifact_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_food_evidence_retriever_router_readiness import main

    status_path = tmp_path / "websearch_status.json"
    output = tmp_path / "router_readiness.json"
    write_json_artifact(status_path, _websearch_status_ready())

    assert (
        main(
            [
                "--websearch-status-packet",
                str(status_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_food_evidence_retriever_router_readiness_v1"
    assert artifact["summary"]["exact_brand_websearch_ready"] is True
