from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_session_context_carryover_qa_bundle import (
    REQUIRED_INPUTS,
    build_session_context_carryover_qa_bundle_artifact,
)


def _valid_inputs() -> dict[str, dict[str, object]]:
    return {
        "context_quality_pack": {
            "artifact_type": "accurate_intake_context_quality_pack",
            "status": "context_quality_diagnostic_pass",
            "blockers": [],
            "summary": {
                "pending_pin_scenarios": 4,
                "manager_semantic_required_scenarios": 3,
                "short_term_runtime_replay_scenario_count": 7,
                "short_term_runtime_replay_current_gap_scenarios": 0,
                "fake_provider_handoff_scenario_count": 6,
            },
            "short_term_context_runtime_replay_checked": True,
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_truth_updated": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "short_term_context_runtime_replay": {
            "artifact_type": "accurate_intake_short_term_context_runtime_replay",
            "status": "runtime_replay_diagnostic_pass",
            "blockers": [],
            "runtime_trace_backed": True,
            "scenario_count": 7,
            "summary": {
                "scenario_count": 7,
                "pending_pin_scenarios": 3,
                "current_gap_scenarios": 0,
                "known_gap_signals": [],
            },
            "scenarios": [
                {"scenario_id": "pending_followup_answer", "pending_followup_present": True},
                {"scenario_id": "long_chat_with_pinned_pending_draft", "pending_draft_present": True},
                {"scenario_id": "modify_drink_sugar", "target_candidate_count": 1},
                {"scenario_id": "modify_rice_portion", "target_candidate_count": 1},
            ],
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
        },
        "context_conditioned_intent_wall": {
            "artifact_type": "accurate_intake_context_conditioned_intent_wall",
            "status": "pass",
            "blockers": [],
            "manager_fixture_semantic_source_used": True,
            "summary": {
                "scenario_count": 11,
                "pending_followup_carryover": True,
                "ambiguity_preserved": True,
                "query_no_mutation": True,
                "target_update_requires_manager_decision": True,
            },
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
        },
        "context_coverage_matrix": {
            "artifact_type": "accurate_intake_pl_ce_context_coverage_matrix",
            "status": "context_coverage_matrix_ready_for_human_review",
            "blockers": [],
            "summary": {
                "capability_count": 9,
                "covered_capability_count": 9,
                "known_runtime_gap_count": 0,
                "blocked_capability_count": 0,
            },
            "coverage_matrix": {
                "pending_followup_carryover": {"coverage_status": "fixture_runtime_and_fake_provider_checked"},
                "correction_target_candidates": {"coverage_status": "fixture_runtime_and_fake_provider_checked"},
                "removal_target_candidates": {"coverage_status": "fixture_runtime_and_fake_provider_checked"},
                "ambiguity_preserved": {"coverage_status": "fixture_runtime_and_fake_provider_checked"},
                "query_no_mutation": {"coverage_status": "fixture_and_fake_provider_checked"},
                "target_update_boundary": {"coverage_status": "fixture_and_fake_provider_checked"},
                "long_session_bounded_context": {"coverage_status": "fixture_runtime_checked"},
                "forbidden_context_exclusion": {"coverage_status": "runtime_and_fake_provider_checked"},
                "semantic_owner_boundary": {"coverage_status": "fixture_runtime_and_fake_provider_checked"},
            },
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
        },
        "product_pages_short_term_context_smoke": {
            "smoke_id": "accurate_intake_product_pages_short_term_context_smoke_v1",
            "status": "pass",
            "blockers": [],
            "browser_executed": True,
            "browser_reload_checked": True,
            "fixture_manager_used": True,
            "pending_followup_created": True,
            "pending_followup_reloaded": True,
            "context_policy_version_present": True,
            "loaded_context_summary_present": True,
            "omitted_context_summary_present": True,
            "pending_pins_present_after_followup": True,
            "chat_history_context_fields_reloaded": True,
            "chat_cjk_roundtrip_rendered": True,
            "assistant_followup_bubble_rendered": True,
            "assistant_commit_bubble_rendered": True,
            "today_same_day_meal_rendered": True,
            "today_summary_rendered": True,
            "product_pages_no_debug_trace": True,
            "target_candidate_surface_status": "not_checked_pending_followup_only",
            "frontend_semantic_owner": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
        },
        "product_pages_target_candidate_ui_smoke": {
            "smoke_id": "accurate_intake_product_pages_target_candidate_ui_smoke_v1",
            "status": "pass",
            "blockers": [],
            "browser_executed": True,
            "browser_reload_checked": True,
            "chat_page_loaded": True,
            "chat_history_reloaded": True,
            "target_candidate_surface_checked": True,
            "target_candidate_count_rendered": 2,
            "target_candidate_names_rendered": ["luwei", "milk tea"],
            "target_candidate_list_read_only": True,
            "context_strip_read_only": True,
            "product_pages_no_debug_trace": True,
            "manager_provider_call_count": 0,
            "frontend_selected_target": False,
            "frontend_semantic_owner": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
        },
    }


def test_session_context_carryover_bundle_proves_short_term_context_review_ready() -> None:
    artifact = build_session_context_carryover_qa_bundle_artifact(_valid_inputs())

    assert artifact["artifact_type"] == "accurate_intake_session_context_carryover_qa_bundle"
    assert artifact["status"] == "session_context_carryover_qa_ready_for_human_review"
    assert artifact["required_inputs"] == list(REQUIRED_INPUTS)
    assert artifact["blockers"] == []
    assert artifact["summary"]["pending_followup_carryover_checked"] is True
    assert artifact["summary"]["target_candidate_ui_checked"] is True
    assert artifact["summary"]["long_session_pinned_draft_checked"] is True
    assert artifact["summary"]["context_conditioned_intent_wall_checked"] is True
    assert artifact["summary"]["coverage_known_runtime_gap_count"] == 0
    assert artifact["human_review_required"] is True
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["context_engineering_fault_claimed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["deterministic_semantic_inference_used"] is False
    assert artifact["frontend_semantic_owner"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False


def test_session_context_carryover_bundle_blocks_missing_pending_followup_reload() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_short_term_context_smoke"]["pending_followup_reloaded"] = False

    artifact = build_session_context_carryover_qa_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_short_term_context_smoke.pending_followup_reloaded_not_true" in artifact["blockers"]


def test_session_context_carryover_bundle_blocks_missing_long_session_runtime_replay() -> None:
    inputs = _valid_inputs()
    inputs["short_term_context_runtime_replay"]["scenarios"] = [
        {"scenario_id": "pending_followup_answer", "pending_followup_present": True}
    ]

    artifact = build_session_context_carryover_qa_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "short_term_context_runtime_replay.long_chat_with_pinned_pending_draft_missing" in artifact["blockers"]


def test_session_context_carryover_bundle_blocks_missing_target_candidate_ui_surface() -> None:
    inputs = _valid_inputs()
    inputs["product_pages_target_candidate_ui_smoke"]["target_candidate_surface_checked"] = False
    inputs["product_pages_target_candidate_ui_smoke"]["target_candidate_count_rendered"] = 0

    artifact = build_session_context_carryover_qa_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "product_pages_target_candidate_ui_smoke.target_candidate_surface_checked_not_true" in artifact["blockers"]
    assert "product_pages_target_candidate_ui_smoke.target_candidate_count_rendered_mismatch" in artifact["blockers"]


def test_session_context_carryover_bundle_blocks_semantic_or_readiness_overclaims() -> None:
    inputs = _valid_inputs()
    inputs["context_conditioned_intent_wall"]["deterministic_semantic_inference_used"] = True
    inputs["product_pages_target_candidate_ui_smoke"]["frontend_semantic_owner"] = True
    inputs["context_coverage_matrix"]["ready_for_live_diagnostic_decision"] = True

    artifact = build_session_context_carryover_qa_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_conditioned_intent_wall.deterministic_semantic_inference_used" in artifact["blockers"]
    assert "product_pages_target_candidate_ui_smoke.frontend_semantic_owner" in artifact["blockers"]
    assert "context_coverage_matrix.ready_for_live_diagnostic_decision" in artifact["blockers"]


def test_session_context_carryover_bundle_cli_writes_from_existing_artifacts(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_session_context_carryover_qa_bundle import main

    output_path = tmp_path / "session-context-carryover.json"
    args = ["--output", str(output_path)]
    for group_id, payload in _valid_inputs().items():
        artifact_path = tmp_path / f"{group_id}.json"
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        args.extend(["--artifact", f"{group_id}={artifact_path}"])

    exit_code = main(args)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "session_context_carryover_qa_ready_for_human_review"
    assert artifact["included_artifact_statuses"]["context_coverage_matrix"]["source_artifact_path"]


def test_session_context_carryover_bundle_source_stays_out_of_db_websearch_live_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_session_context_carryover_qa_bundle.py"),
        Path("scripts/build_accurate_intake_session_context_carryover_qa_bundle.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "from tavily",
        "import tavily",
        "tavilyclient",
        "tavilysearch",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "kimi",
        "grok",
        "live_llm_invoked = True",
        "web_tavily_used = True",
        "ready_for_live_diagnostic_decision = True",
        "ready_for_fdb_integration = True",
    ]
    combined_source = "\n".join(path.read_text(encoding="utf-8").lower() for path in source_paths)

    for fragment in forbidden:
        assert fragment.lower() not in combined_source
