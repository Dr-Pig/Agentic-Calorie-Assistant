from __future__ import annotations

from typing import Any


def build_fooddb_live_diagnostic_integration_edges() -> tuple[dict[str, Any], ...]:
    return (
        _edge(
            edge_id="fooddb_preflight_to_live_runner_readiness_packet",
            from_node="fooddb_live_diagnostic_preflight",
            to_node="fooddb_live_runner_readiness_packet",
            dependency_direction="fooddb_preflight_to_live_runner_gate",
            required_contract="live runner readiness requires clear FoodDB preflight before explicit GrokFast diagnostic",
            current_status="contract_backed",
            manager_style_guard="fooddb_live_runner_readiness_requires_clear_preflight_without_granting_runtime_truth",
            evidence=[
                "app.nutrition.application.grokfast_fooddb_live_runner_readiness_checks.is_grokfast_fooddb_live_runner_readiness_clear",
                "app.nutrition.application.grokfast_fooddb_live_runner_readiness_packet.build_grokfast_fooddb_live_runner_readiness_packet",
                "tests.test_grokfast_fooddb_live_runner_readiness_packet.test_fooddb_live_runner_readiness_blocks_preflight_not_clear",
            ],
            stop_condition="stop_if_live_runner_readiness_bypasses_fooddb_preflight_or_grants_runtime_truth",
        ),
        _edge(
            edge_id="retriever_router_readiness_to_live_runner_readiness_packet",
            from_node="retriever_router_readiness_gate",
            to_node="fooddb_live_runner_readiness_packet",
            dependency_direction="router_readiness_to_live_runner_gate",
            required_contract="live runner readiness must verify router stays manager-owned and candidate-only before explicit GrokFast diagnostic",
            current_status="contract_backed",
            manager_style_guard="fooddb_live_runner_readiness_may_consume_router_guard_but_cannot_decide_user_intent_or_mutation",
            evidence=[
                "app.nutrition.application.grokfast_fooddb_live_runner_readiness_checks.live_runner_readiness_input_blockers",
                "app.nutrition.application.food_evidence_retriever_router_readiness.build_food_evidence_retriever_router_readiness",
                "tests.test_grokfast_fooddb_live_runner_readiness_packet.test_fooddb_live_runner_readiness_blocks_router_guard_not_clear",
            ],
            stop_condition="stop_if_live_runner_readiness_opens_router_execution_without_clear_router_guard",
        ),
        _edge(
            edge_id="fooddb_live_runner_readiness_packet_to_grokfast_fooddb_live_diagnostic",
            from_node="fooddb_live_runner_readiness_packet",
            to_node="grokfast_fooddb_packet_live_diagnostic",
            dependency_direction="live_runner_gate_to_explicit_fooddb_live_diagnostic",
            required_contract="explicit GrokFast FoodDB live diagnostic requires clear live runner readiness packet",
            current_status="contract_backed",
            manager_style_guard="fooddb_live_runner_readiness_may_open_explicit_grokfast_diagnostic_but_not_runtime_truth_or_mutation",
            evidence=[
                "scripts.run_accurate_intake_grokfast_fooddb_packet_smoke.main",
                "tests.test_grokfast_fooddb_packet_smoke.test_grokfast_fooddb_packet_smoke_live_requires_runner_readiness_packet",
            ],
            stop_condition="stop_if_live_diagnostic_runs_without_clear_fooddb_live_runner_readiness_packet",
        ),
    )


def _edge(
    *,
    edge_id: str,
    from_node: str,
    to_node: str,
    dependency_direction: str,
    required_contract: str,
    current_status: str,
    manager_style_guard: str,
    evidence: list[str],
    stop_condition: str,
) -> dict[str, Any]:
    return {
        "edge_id": edge_id,
        "from": from_node,
        "to": to_node,
        "dependency_direction": dependency_direction,
        "required_contract": required_contract,
        "current_status": current_status,
        "manager_style_guard": manager_style_guard,
        "evidence": evidence,
        "stop_condition": stop_condition,
    }


__all__ = ["build_fooddb_live_diagnostic_integration_edges"]
