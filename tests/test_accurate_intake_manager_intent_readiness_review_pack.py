from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_conditioned_intent_wall import (
    build_context_conditioned_intent_wall_artifact,
)
from app.composition.accurate_intake_contextual_interaction_matrix import (
    build_contextual_interaction_matrix_artifact,
)
from app.composition.accurate_intake_fake_provider_context_smoke import (
    build_fake_provider_context_smoke_artifact,
)
from app.composition.accurate_intake_manager_intent_readiness_review_pack import (
    REQUIRED_INPUTS,
    build_manager_intent_readiness_review_pack_artifact,
)
from app.composition.accurate_intake_responder_input_contract_fake_smoke import (
    build_responder_input_contract_fake_smoke_artifact,
)
from scripts import build_accurate_intake_manager_intent_readiness_review_pack as script


def _valid_inputs() -> dict[str, dict[str, object]]:
    return {
        "context_conditioned_intent_wall": build_context_conditioned_intent_wall_artifact(),
        "contextual_interaction_matrix": build_contextual_interaction_matrix_artifact(),
        "fake_provider_context_smoke": build_fake_provider_context_smoke_artifact(),
        "responder_input_contract_fake_smoke": build_responder_input_contract_fake_smoke_artifact(),
        "context_coverage_matrix": {
            "artifact_type": "accurate_intake_pl_ce_context_coverage_matrix",
            "status": "context_coverage_matrix_ready_for_human_review",
            "blockers": [],
            "summary": {
                "capability_count": 9,
                "covered_capability_count": 9,
                "blocked_capability_count": 0,
                "known_runtime_gap_count": 0,
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
        "session_context_carryover_qa_bundle": {
            "artifact_type": "accurate_intake_session_context_carryover_qa_bundle",
            "status": "session_context_carryover_qa_ready_for_human_review",
            "blockers": [],
            "summary": {
                "pending_followup_carryover_checked": True,
                "target_candidate_ui_checked": True,
                "long_session_pinned_draft_checked": True,
                "context_conditioned_intent_wall_checked": True,
                "coverage_known_runtime_gap_count": 0,
            },
            "human_review_required": True,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_semantic_inference_used": False,
            "frontend_semantic_owner": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
        },
        "ui_context_alignment_pack": {
            "artifact_type": "accurate_intake_pl_ce_ui_context_alignment_pack",
            "status": "ui_context_alignment_ready_for_human_review",
            "blockers": [],
            "render_only_boundary_ok": True,
            "frontend_semantic_owner": False,
            "summary": {
                "chat_context_reload_checked": True,
                "seven_day_diary_checked": True,
                "body_read_model_checked": True,
                "context_covered_capabilities": 9,
                "context_known_runtime_gap_count": 0,
            },
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "manager_context_packet_schema_changed": False,
            "mutation_authority": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_evidence_used": False,
        },
    }


def test_manager_intent_readiness_pack_is_human_review_only() -> None:
    artifact = build_manager_intent_readiness_review_pack_artifact(_valid_inputs())

    assert artifact["artifact_type"] == "accurate_intake_manager_intent_readiness_review_pack"
    assert artifact["status"] == "manager_intent_readiness_ready_for_human_review"
    assert artifact["required_inputs"] == list(REQUIRED_INPUTS)
    assert artifact["blockers"] == []
    assert artifact["local_only"] is True
    assert artifact["diagnostic_only"] is True
    assert artifact["fixture_only"] is True
    assert artifact["aggregate_only"] is True
    assert artifact["human_review_required"] is True
    assert artifact["review_required_before_provider_call"] is True
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["semantic_owner"] == "fixture_manager_structured_decision"
    assert artifact["next_gate"]["requires_human_approval"] is True  # type: ignore[index]


def test_manager_intent_readiness_pack_summarizes_substantive_context_coverage() -> None:
    artifact = build_manager_intent_readiness_review_pack_artifact(_valid_inputs())
    summary = artifact["summary"]

    assert summary["intent_wall_scenarios"] >= 11
    assert summary["contextual_interactions"] >= 11
    assert summary["pending_followup_interactions"] >= 1
    assert summary["target_candidate_interactions"] >= 4
    assert summary["ambiguity_preserved_interactions"] >= 2
    assert summary["query_no_mutation_interactions"] >= 1
    assert summary["target_update_manager_decision_interactions"] >= 1
    assert summary["fake_provider_handoff_scenarios"] >= 6
    assert summary["fake_provider_ambiguous_back_reference_scenarios"] >= 1
    assert summary["responder_allowed_fact_scenarios"] >= 5
    assert summary["context_covered_capabilities"] >= 9
    assert summary["context_blocked_capabilities"] == 0
    assert summary["context_known_runtime_gaps"] == 0
    assert summary["session_pending_followup_carryover_checked"] is True
    assert summary["session_target_candidate_ui_checked"] is True
    assert summary["session_long_context_checked"] is True
    assert summary["ui_chat_context_reload_checked"] is True
    assert summary["ui_today_seven_day_diary_checked"] is True
    assert summary["ui_body_read_model_checked"] is True


def test_manager_intent_readiness_pack_blocks_upstream_blockers_and_claims() -> None:
    inputs = _valid_inputs()
    inputs["contextual_interaction_matrix"]["blockers"] = ["semantic_owner_boundary_missing"]
    inputs["fake_provider_context_smoke"]["live_llm_invoked"] = True
    inputs["context_coverage_matrix"]["ready_for_live_diagnostic_decision"] = True
    inputs["session_context_carryover_qa_bundle"]["fooddb_truth_updated"] = True
    inputs["ui_context_alignment_pack"]["frontend_semantic_owner"] = True

    artifact = build_manager_intent_readiness_review_pack_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "contextual_interaction_matrix.upstream_blockers_present" in artifact["blockers"]
    assert "contextual_interaction_matrix.semantic_owner_boundary_missing" in artifact["blockers"]
    assert "fake_provider_context_smoke.live_llm_invoked" in artifact["blockers"]
    assert "context_coverage_matrix.ready_for_live_diagnostic_decision" in artifact["blockers"]
    assert "session_context_carryover_qa_bundle.fooddb_truth_updated" in artifact["blockers"]
    assert "ui_context_alignment_pack.frontend_semantic_owner" in artifact["blockers"]
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False


def test_manager_intent_readiness_pack_blocks_nested_semantic_promotion() -> None:
    inputs = _valid_inputs()
    interactions = inputs["contextual_interaction_matrix"]["interactions"]  # type: ignore[index]
    interactions[0]["deterministic_selected_target"] = True  # type: ignore[index]
    responder_scenarios = inputs["responder_input_contract_fake_smoke"]["scenarios"]  # type: ignore[index]
    responder_scenarios[0]["live_llm_invoked"] = True  # type: ignore[index]

    artifact = build_manager_intent_readiness_review_pack_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert (
        "contextual_interaction_matrix.interactions[0].deterministic_selected_target"
        in artifact["blockers"]
    )
    assert (
        "responder_input_contract_fake_smoke.scenarios[0].live_llm_invoked"
        in artifact["blockers"]
    )


def test_manager_intent_readiness_pack_blocks_missing_ui_session_or_coverage_evidence() -> None:
    inputs = _valid_inputs()
    inputs["context_coverage_matrix"]["summary"]["known_runtime_gap_count"] = 1  # type: ignore[index]
    inputs["session_context_carryover_qa_bundle"]["summary"][  # type: ignore[index]
        "long_session_pinned_draft_checked"
    ] = False
    inputs["ui_context_alignment_pack"]["summary"]["seven_day_diary_checked"] = False  # type: ignore[index]

    artifact = build_manager_intent_readiness_review_pack_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_coverage_matrix.known_runtime_gap_count_present" in artifact["blockers"]
    assert (
        "session_context_carryover_qa_bundle.long_session_pinned_draft_checked_not_true"
        in artifact["blockers"]
    )
    assert "ui_context_alignment_pack.seven_day_diary_not_checked" in artifact["blockers"]


def test_manager_intent_readiness_pack_script_blocks_missing_or_invalid_inputs(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{not-json", encoding="utf-8")

    input_artifacts = script.build_input_artifacts(
        {
            "context_conditioned_intent_wall": invalid_path,
            "contextual_interaction_matrix": tmp_path / "missing.json",
        }
    )
    artifact = build_manager_intent_readiness_review_pack_artifact(input_artifacts)

    assert artifact["status"] == "blocked"
    assert "context_conditioned_intent_wall.invalid_json" in artifact["blockers"]
    assert "contextual_interaction_matrix.missing" in artifact["blockers"]


def test_manager_intent_readiness_pack_cli_writes_source_paths(tmp_path: Path) -> None:
    paths: dict[str, Path] = {}
    for group_id, payload in _valid_inputs().items():
        path = tmp_path / f"{group_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        paths[group_id] = path
    output = tmp_path / "manager_intent_readiness.json"

    argv: list[str] = []
    for group_id, path in paths.items():
        argv.extend(["--artifact", f"{group_id}={path}"])
    argv.extend(["--output", str(output)])
    assert script.main(argv) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["status"] == "manager_intent_readiness_ready_for_human_review"
    assert payload["included_artifact_statuses"]["contextual_interaction_matrix"][  # type: ignore[index]
        "source_artifact_path"
    ] == str(paths["contextual_interaction_matrix"])


def test_manager_intent_readiness_pack_source_does_not_touch_forbidden_domains() -> None:
    source_files = [
        Path("app/composition/accurate_intake_manager_intent_readiness_review_pack.py"),
        Path("scripts/build_accurate_intake_manager_intent_readiness_review_pack.py"),
    ]
    forbidden_fragments = (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "packetizer",
        "Tavily",
        "GrokFast",
        "Kimi",
        "ManagerContextPacket",
        "mutation_legality",
        "live_llm_invoked = True",
        "fooddb_truth_updated = True",
        "manager_context_packet_schema_changed = True",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in source_files)

    for fragment in forbidden_fragments:
        assert fragment not in combined
