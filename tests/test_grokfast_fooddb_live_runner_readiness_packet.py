from __future__ import annotations

from pathlib import Path

from app.nutrition.application.food_evidence_retriever_router import (
    RetrieverBackendAvailability,
)
from app.nutrition.application.food_evidence_retriever_router_readiness import (
    build_food_evidence_retriever_router_readiness,
)
from app.nutrition.application.grokfast_fooddb_diagnostic_preflight import (
    build_grokfast_fooddb_diagnostic_preflight,
)
from app.nutrition.application.grokfast_fooddb_live_runner_readiness_packet import (
    build_grokfast_fooddb_live_runner_readiness_packet,
    is_grokfast_fooddb_live_runner_readiness_clear,
)


def _retrieval_eval_wall(*, fail_count: int = 0) -> dict:
    return {
        "artifact_type": "accurate_intake_retrieval_eval_wall_v1",
        "classification": "deterministic_retrieval_eval_wall_only",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "case_count": 9,
            "pass_count": 9 - fail_count,
            "fail_count": fail_count,
            "websearch_runtime_truth_allowed_count": 0,
            "next_required_slice": (
                "inspect_retrieval_eval_wall_failures"
                if fail_count
                else "grokfast_fooddb_packet_live_diagnostic"
            ),
        },
    }


def _fooddb_status() -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "runtime_common_serving_anchor_count": 51,
            "listed_component_anchor_count": 30,
            "manager_fooddb_packet_seam_gate_status": "pass",
            "manager_contract_handoff_status": "not_run",
            "manager_contract_owner_handoff_ready": False,
        },
        "next_required_slices": ["grokfast_fooddb_packet_live_diagnostic"],
    }


def _manager_packet_smoke() -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_manager_packet_smoke",
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "live_provider_used": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "readiness_claimed": False,
        "summary": {
            "case_count": 5,
            "compact_packet_pass_count": 5,
            "raw_source_rows_included": False,
            "candidate_only_records_included": False,
            "full_fooddb_included": False,
        },
    }


def _backend_parity() -> dict:
    case_ids = ("boba_alias", "chicken_bento_alias", "kelp_component", "latte_alias")
    return {
        "artifact_type": "accurate_intake_fooddb_index_backend_parity_v1",
        "classification": "deterministic_backend_parity_only",
        "status": "pass",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "next_required_slice": "grokfast_fooddb_packet_live_diagnostic",
        "summary": {
            "case_count": 4,
            "pass_count": 4,
            "fail_count": 0,
            "backend_count": 3,
            "backend_labels": ["local_json", "sqlite_fts", "supabase_rows"],
        },
        "cases": [
            {
                "case_id": case_id,
                "status": "pass",
                "checks": {
                    "accepted_anchor_parity": True,
                    "manager_visible_evidence_payload_parity": True,
                    "expected_top_anchor": True,
                    "manager_visible_boundary": True,
                },
                "backend_results": [
                    {
                        "backend_label": label,
                        "manager_visible_boundary_passed": True,
                        "manager_visible_evidence_item_signatures": [
                            {"anchor_id": f"{case_id}_anchor", "runtime_truth_allowed": True}
                        ],
                    }
                    for label in ("local_json", "sqlite_fts", "supabase_rows")
                ],
            }
            for case_id in case_ids
        ],
    }


def _case_matrix() -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_grokfast_packet_live_diagnostic_case_matrix",
        "status": "pass",
        "plan_only": True,
        "live_llm_invoked": False,
        "live_provider_invoked": False,
        "websearch_invoked": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_packet_changed": False,
        "shared_contract_changed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "non_claims": [
            "not_full_self_use_gate",
            "not_websearch_exact_card_gate",
            "not_final_response_quality_gate",
            "not_production_readiness",
            "not_private_self_use_approval",
            "not_kimi_activation",
            "not_runtime_mutation_gate",
        ],
        "summary": {
            "case_count": 5,
            "modifier_guard_cases": 2,
            "bare_basket_cases": 1,
            "listed_basket_cases": 1,
            "websearch_cases": 0,
            "exact_card_cases": 0,
        },
        "cases": [
            {"case_id": "boba_large_half_sugar"},
            {"case_id": "boba_typo"},
            {"case_id": "bare_luwei"},
            {"case_id": "listed_luwei_components"},
            {"case_id": "chicken_bento_less_rice"},
        ],
    }


def _preflight() -> dict:
    return build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
        index_backend_parity_artifact=_backend_parity(),
        case_matrix_artifact=_case_matrix(),
    )


def _router_readiness() -> dict:
    return build_food_evidence_retriever_router_readiness(
        base_availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=False,
        )
    )


def test_fooddb_live_runner_readiness_packet_passes_without_live() -> None:
    artifact = build_grokfast_fooddb_live_runner_readiness_packet(
        preflight_artifact=_preflight(),
        router_readiness_artifact=_router_readiness(),
    )

    assert (
        artifact["artifact_type"]
        == "accurate_intake_grokfast_fooddb_live_runner_readiness_packet_v1"
    )
    assert artifact["status"] == "pass"
    assert artifact["ready_for_grokfast_fooddb_packet_live_diagnostic"] is True
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["provider_readiness_checked"] is False
    assert artifact["runner_contract"]["requires_explicit_allow_live_flag"] is True
    assert is_grokfast_fooddb_live_runner_readiness_clear(artifact) is True


def test_fooddb_live_runner_readiness_blocks_preflight_not_clear() -> None:
    preflight = _preflight()
    preflight["clear_to_run_live_diagnostic"] = False

    artifact = build_grokfast_fooddb_live_runner_readiness_packet(
        preflight_artifact=preflight,
        router_readiness_artifact=_router_readiness(),
    )

    assert artifact["status"] == "blocked"
    assert "fooddb_grokfast_preflight_not_clear" in artifact["blockers"]
    assert is_grokfast_fooddb_live_runner_readiness_clear(artifact) is False


def test_fooddb_live_runner_readiness_blocks_router_guard_not_clear() -> None:
    router = _router_readiness()
    router["status"] = "blocked"

    artifact = build_grokfast_fooddb_live_runner_readiness_packet(
        preflight_artifact=_preflight(),
        router_readiness_artifact=router,
    )

    assert artifact["status"] == "blocked"
    assert "food_evidence_retriever_router_readiness_not_pass" in artifact["blockers"]


def test_fooddb_live_runner_readiness_clear_predicate_blocks_contract_drift() -> None:
    artifact = build_grokfast_fooddb_live_runner_readiness_packet(
        preflight_artifact=_preflight(),
        router_readiness_artifact=_router_readiness(),
    )

    for field in (
        "manager_context_changed",
        "shared_contract_changed",
        "packetizer_format_changed",
    ):
        drifted = dict(artifact)
        drifted[field] = True
        assert is_grokfast_fooddb_live_runner_readiness_clear(drifted) is False


def test_fooddb_live_runner_readiness_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_grokfast_fooddb_live_runner_readiness_packet import (
        main,
    )

    preflight = _preflight()
    router = _router_readiness()
    preflight_path = tmp_path / "preflight.json"
    router_path = tmp_path / "router.json"
    output = tmp_path / "readiness.json"
    write_json_artifact(preflight_path, preflight)
    write_json_artifact(router_path, router)

    assert (
        main(
            [
                "--preflight-artifact",
                str(preflight_path),
                "--router-readiness-artifact",
                str(router_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["status"] == "pass"
    assert artifact["ready_for_grokfast_fooddb_packet_live_diagnostic"] is True
