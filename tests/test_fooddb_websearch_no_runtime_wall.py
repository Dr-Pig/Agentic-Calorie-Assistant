from __future__ import annotations

from pathlib import Path

from app.nutrition.application.fooddb_websearch_no_runtime_selection import (
    select_fooddb_websearch_no_runtime_next_required_slice,
)
from app.nutrition.application.fooddb_websearch_no_runtime_wall import (
    build_default_fooddb_websearch_no_runtime_wall,
    build_fooddb_websearch_no_runtime_wall,
)


def test_fooddb_websearch_no_runtime_wall_passes_default_candidate_preflight_artifacts() -> None:
    artifact = build_default_fooddb_websearch_no_runtime_wall()

    assert artifact["artifact_type"] == "accurate_intake_fooddb_websearch_no_runtime_wall_v1"
    assert artifact["classification"] == "deterministic_no_runtime_wall_only"
    assert artifact["status"] == "pass"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["shared_contract_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["packetizer_format_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["artifact_count"] >= 12
    assert artifact["summary"]["blocked_count"] == 0
    assert artifact["summary"]["runtime_truth_leak_count"] == 0
    assert artifact["summary"]["live_or_readiness_leak_count"] == 0
    assert artifact["next_required_slice"] == "grokfast_fooddb_packet_live_diagnostic"
    artifact_types = {result["artifact_type"] for result in artifact["artifact_results"]}
    assert "accurate_intake_fooddb_evidence_status_packet_v1" in artifact_types
    assert "accurate_intake_fooddb_activation_gap_report" in artifact_types
    assert "accurate_intake_fooddb_status_packet" in artifact_types
    assert (
        "accurate_intake_websearch_grokfast_packet_live_diagnostic_case_matrix"
        in artifact_types
    )


def test_select_no_runtime_wall_next_step_prefers_fooddb_live_diagnostic_first() -> None:
    next_slice = select_fooddb_websearch_no_runtime_next_required_slice(
        wall_clear=True,
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_fooddb_packet_live_diagnostic"],
        },
        websearch_status_packet={
            "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
            "next_required_slices": ["grokfast_fooddb_packet_live_diagnostic"],
        },
    )

    assert next_slice == "grokfast_fooddb_packet_live_diagnostic"


def test_select_no_runtime_wall_next_step_can_advance_to_websearch_live_diagnostic() -> None:
    next_slice = select_fooddb_websearch_no_runtime_next_required_slice(
        wall_clear=True,
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        websearch_status_packet={
            "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
    )

    assert next_slice == "grokfast_websearch_packet_live_diagnostic"


def test_fooddb_websearch_no_runtime_wall_blocks_runtime_truth_and_mutation_leaks() -> None:
    artifact = build_fooddb_websearch_no_runtime_wall(
        artifacts=(
            {
                "artifact_type": "unsafe_websearch_candidate",
                "runtime_truth_changed": True,
                "runtime_mutation_allowed": True,
                "cases": [
                    {
                        "case_id": "candidate",
                        "websearch_candidate_packet": {
                            "runtime_truth_allowed": True,
                            "exact_card_created": True,
                        },
                    }
                ],
            },
        )
    )

    assert artifact["status"] == "blocked"
    assert "unsafe_websearch_candidate:$.runtime_truth_changed" in artifact["blockers"]
    assert "unsafe_websearch_candidate:$.runtime_mutation_allowed" in artifact["blockers"]
    assert (
        "unsafe_websearch_candidate:$.cases[0].websearch_candidate_packet.runtime_truth_allowed"
        in artifact["blockers"]
    )
    assert (
        "unsafe_websearch_candidate:$.cases[0].websearch_candidate_packet.exact_card_created"
        in artifact["blockers"]
    )
    assert artifact["next_required_slice"] == "inspect_fooddb_websearch_no_runtime_wall_blockers"


def test_fooddb_websearch_no_runtime_wall_blocks_live_and_readiness_leaks() -> None:
    artifact = build_fooddb_websearch_no_runtime_wall(
        artifacts=(
            {
                "artifact_type": "unsafe_live_report",
                "live_provider_used": True,
                "live_websearch_used": True,
                "readiness_claimed": True,
                "self_use_approved": True,
            },
        )
    )

    assert artifact["status"] == "blocked"
    assert "unsafe_live_report:$.live_provider_used" in artifact["blockers"]
    assert "unsafe_live_report:$.live_websearch_used" in artifact["blockers"]
    assert "unsafe_live_report:$.readiness_claimed" in artifact["blockers"]
    assert "unsafe_live_report:$.self_use_approved" in artifact["blockers"]
    assert artifact["summary"]["live_or_readiness_leak_count"] == 4


def test_fooddb_websearch_no_runtime_wall_blocks_known_claim_flag_variants() -> None:
    artifact = build_fooddb_websearch_no_runtime_wall(
        artifacts=(
            {
                "artifact_type": "unsafe_variant_probe",
                "source_live_provider_used": True,
                "source_live_websearch_used": True,
                "live_llm_invoked": True,
                "llm_call": True,
                "llm_enabled": True,
                "llm_allowed": True,
                "live_call_used": True,
                "live_call_allowed_by_this_artifact": True,
                "live_provider_used": "detected",
                "llm_used": 1,
                "provider_called": True,
                "provider_enabled": True,
                "provider_allowed": True,
                "provider_invocation_count": 1,
                "provider_invocations": ["call-1"],
                "web_search_used": True,
                "websearch_called": True,
                "websearch_enabled": True,
                "websearch_allowed": True,
                "websearch_invocations": ["search-1"],
                "websearch_usage": True,
                "tavily_called": 1,
                "tavily_enabled": True,
                "tavily_allowed": True,
                "tavily_invocation_count": 1,
                "tavily_request_sent": True,
                "tavily_usage": True,
                "ready_for_runtime_truth": True,
                "mutation_allowed": True,
                "ledger_mutated": True,
                "packetizer_contract_changed": True,
                "shared_packet_contract_changed": True,
                "product_readiness_claim": True,
                "product_ready": True,
                "product_claimed": True,
                "production_ready": True,
                "production_claimed": True,
                "self_use_claimed": True,
                "runtime_truth_promoted": "true",
                "runtime_truth_readiness": True,
                "runtime_mutation_attempted": "attempted",
                "runtime_truth_changed": "changed",
                "exact_card_created": "created",
                "product_readiness_claimed": "claimed_by_manifest",
                "private_self_use_is_approved": True,
                "manager_context_runtime_schema_changed": "true",
                "manager_context_schema_change": True,
                "manager_context_packet_schema_updated": True,
                "manager_context_packet_schema_modified": True,
                "packetizer_format_change": True,
                "shared_contract_change": True,
                "shared_contract_updated": True,
                "product_loop_integration": True,
                "product_loop_integrated": True,
                "product_loop_activation": True,
                "runtime_packetizer_contract_changed": True,
                "web_readiness_claimed": True,
                "product_loop_integration_claimed": True,
                "probe": {
                    "exact_card_candidate": {
                        "exact_card": "created",
                        "exact_candidate_promotion_allowed": True,
                        "websearch_candidate_promotion_allowed": True,
                        "exact_card_candidate_promotion_allowed": True,
                        "exact_candidate_promoted": True,
                        "exact_candidate_truth_allowed": True,
                        "promotion": "allowed",
                        "runtime_truth": "allowed",
                        "selected_extract_final_truth_allowed": True,
                        "websearch_truth_allowed": True,
                        "websearch_candidate_promoted": True,
                        "runtime_truth_allowed": True,
                    },
                    "exact_evidence_lane": {
                        "runtime_truth_allowed": True,
                    },
                    "manager_context_schema_changed": True,
                    "context_packet_schema_changed": True,
                    "manager_context_packet_schema_changed": True,
                    "manager_context_packet_changed": True,
                },
            },
        )
    )

    assert artifact["status"] == "blocked"
    assert "unsafe_variant_probe:$.source_live_provider_used" in artifact["blockers"]
    assert "unsafe_variant_probe:$.source_live_websearch_used" in artifact["blockers"]
    assert "unsafe_variant_probe:$.live_llm_invoked" in artifact["blockers"]
    assert "unsafe_variant_probe:$.llm_call" in artifact["blockers"]
    assert "unsafe_variant_probe:$.llm_enabled" in artifact["blockers"]
    assert "unsafe_variant_probe:$.llm_allowed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.live_call_used" in artifact["blockers"]
    assert "unsafe_variant_probe:$.live_call_allowed_by_this_artifact" in artifact["blockers"]
    assert "unsafe_variant_probe:$.live_provider_used" in artifact["blockers"]
    assert "unsafe_variant_probe:$.llm_used" in artifact["blockers"]
    assert "unsafe_variant_probe:$.provider_called" in artifact["blockers"]
    assert "unsafe_variant_probe:$.provider_enabled" in artifact["blockers"]
    assert "unsafe_variant_probe:$.provider_allowed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.provider_invocation_count" in artifact["blockers"]
    assert "unsafe_variant_probe:$.provider_invocations" in artifact["blockers"]
    assert "unsafe_variant_probe:$.web_search_used" in artifact["blockers"]
    assert "unsafe_variant_probe:$.websearch_called" in artifact["blockers"]
    assert "unsafe_variant_probe:$.websearch_enabled" in artifact["blockers"]
    assert "unsafe_variant_probe:$.websearch_allowed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.websearch_invocations" in artifact["blockers"]
    assert "unsafe_variant_probe:$.websearch_usage" in artifact["blockers"]
    assert "unsafe_variant_probe:$.tavily_called" in artifact["blockers"]
    assert "unsafe_variant_probe:$.tavily_enabled" in artifact["blockers"]
    assert "unsafe_variant_probe:$.tavily_allowed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.tavily_invocation_count" in artifact["blockers"]
    assert "unsafe_variant_probe:$.tavily_request_sent" in artifact["blockers"]
    assert "unsafe_variant_probe:$.tavily_usage" in artifact["blockers"]
    assert "unsafe_variant_probe:$.ready_for_runtime_truth" in artifact["blockers"]
    assert "unsafe_variant_probe:$.mutation_allowed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.ledger_mutated" in artifact["blockers"]
    assert "unsafe_variant_probe:$.packetizer_contract_changed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.shared_packet_contract_changed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.product_readiness_claim" in artifact["blockers"]
    assert "unsafe_variant_probe:$.product_ready" in artifact["blockers"]
    assert "unsafe_variant_probe:$.product_claimed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.production_ready" in artifact["blockers"]
    assert "unsafe_variant_probe:$.production_claimed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.self_use_claimed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.runtime_truth_promoted" in artifact["blockers"]
    assert "unsafe_variant_probe:$.runtime_truth_readiness" in artifact["blockers"]
    assert "unsafe_variant_probe:$.runtime_mutation_attempted" in artifact["blockers"]
    assert "unsafe_variant_probe:$.runtime_truth_changed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.exact_card_created" in artifact["blockers"]
    assert "unsafe_variant_probe:$.product_readiness_claimed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.private_self_use_is_approved" in artifact["blockers"]
    assert "unsafe_variant_probe:$.manager_context_runtime_schema_changed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.manager_context_schema_change" in artifact["blockers"]
    assert "unsafe_variant_probe:$.manager_context_packet_schema_updated" in artifact["blockers"]
    assert "unsafe_variant_probe:$.manager_context_packet_schema_modified" in artifact["blockers"]
    assert "unsafe_variant_probe:$.packetizer_format_change" in artifact["blockers"]
    assert "unsafe_variant_probe:$.shared_contract_change" in artifact["blockers"]
    assert "unsafe_variant_probe:$.shared_contract_updated" in artifact["blockers"]
    assert "unsafe_variant_probe:$.product_loop_integration" in artifact["blockers"]
    assert "unsafe_variant_probe:$.product_loop_integrated" in artifact["blockers"]
    assert "unsafe_variant_probe:$.product_loop_activation" in artifact["blockers"]
    assert "unsafe_variant_probe:$.runtime_packetizer_contract_changed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.web_readiness_claimed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.product_loop_integration_claimed" in artifact["blockers"]
    assert (
        "unsafe_variant_probe:$.probe.exact_card_candidate.exact_card" in artifact["blockers"]
    )
    assert (
        "unsafe_variant_probe:$.probe.exact_card_candidate.exact_candidate_promotion_allowed"
        in artifact["blockers"]
    )
    assert (
        "unsafe_variant_probe:$.probe.exact_card_candidate.websearch_candidate_promotion_allowed"
        in artifact["blockers"]
    )
    assert (
        "unsafe_variant_probe:$.probe.exact_card_candidate.exact_card_candidate_promotion_allowed"
        in artifact["blockers"]
    )
    assert (
        "unsafe_variant_probe:$.probe.exact_card_candidate.exact_candidate_promoted"
        in artifact["blockers"]
    )
    assert (
        "unsafe_variant_probe:$.probe.exact_card_candidate.exact_candidate_truth_allowed"
        in artifact["blockers"]
    )
    assert (
        "unsafe_variant_probe:$.probe.exact_card_candidate.promotion" in artifact["blockers"]
    )
    assert (
        "unsafe_variant_probe:$.probe.exact_card_candidate.runtime_truth" in artifact["blockers"]
    )
    assert (
        "unsafe_variant_probe:$.probe.exact_card_candidate.selected_extract_final_truth_allowed"
        in artifact["blockers"]
    )
    assert (
        "unsafe_variant_probe:$.probe.exact_card_candidate.websearch_truth_allowed"
        in artifact["blockers"]
    )
    assert (
        "unsafe_variant_probe:$.probe.exact_card_candidate.websearch_candidate_promoted"
        in artifact["blockers"]
    )
    assert (
        "unsafe_variant_probe:$.probe.exact_card_candidate.runtime_truth_allowed"
        in artifact["blockers"]
    )
    assert (
        "unsafe_variant_probe:$.probe.exact_evidence_lane.runtime_truth_allowed"
        in artifact["blockers"]
    )
    assert "unsafe_variant_probe:$.probe.manager_context_schema_changed" in artifact["blockers"]
    assert "unsafe_variant_probe:$.probe.context_packet_schema_changed" in artifact["blockers"]
    assert (
        "unsafe_variant_probe:$.probe.manager_context_packet_schema_changed"
        in artifact["blockers"]
    )
    assert "unsafe_variant_probe:$.probe.manager_context_packet_changed" in artifact["blockers"]


def test_fooddb_websearch_no_runtime_wall_blocks_source_status_blockers_and_leak_counts() -> None:
    artifact = build_fooddb_websearch_no_runtime_wall(
        artifacts=(
            {
                "artifact_type": "unsafe_summary_probe",
                "status": "diagnostic_fail",
                "blockers": ["source already detected runtime leak"],
                "violations": ["source already detected semantic overclaim"],
                "object_blockers": {"reason": "runtime leak"},
                "object_violations": {"reason": "overclaim"},
                "blocker_details": ["runtime leak"],
                "leak_details": ["runtime truth leak"],
                "violation_details": ["overclaim"],
                "secondary_blockers": 1,
                "secondary_violations": "yes",
                "summary": {
                    "runtime_truth_allowed_count": 1,
                    "runtime_truth_leak_count": 1,
                    "ready_for_runtime_truth_count": 1,
                    "blocker_count": 1,
                    "blockers_count": 1,
                    "violations_count": 1,
                    "leaks": 1,
                    "leak_summary": "yes",
                    "promotion_allowed_count": 1,
                    "promotion_leak_count": 1,
                    "exact_card_created_count": 1,
                    "exact_candidate_leak_count": 1,
                },
                "websearch_candidates": [
                    {
                        "case_id": "candidate",
                        "summary": {
                            "runtime_truth_allowed_count": 1,
                        },
                    }
                ],
            },
        )
    )

    assert artifact["status"] == "blocked"
    assert "unsafe_summary_probe:$.status" in artifact["blockers"]
    assert "unsafe_summary_probe:$.blockers" in artifact["blockers"]
    assert "unsafe_summary_probe:$.violations" in artifact["blockers"]
    assert "unsafe_summary_probe:$.object_blockers" in artifact["blockers"]
    assert "unsafe_summary_probe:$.object_violations" in artifact["blockers"]
    assert "unsafe_summary_probe:$.blocker_details" in artifact["blockers"]
    assert "unsafe_summary_probe:$.leak_details" in artifact["blockers"]
    assert "unsafe_summary_probe:$.violation_details" in artifact["blockers"]
    assert "unsafe_summary_probe:$.secondary_blockers" in artifact["blockers"]
    assert "unsafe_summary_probe:$.secondary_violations" in artifact["blockers"]
    assert "unsafe_summary_probe:$.summary.promotion_allowed_count" in artifact["blockers"]
    assert "unsafe_summary_probe:$.summary.exact_card_created_count" in artifact["blockers"]
    assert "unsafe_summary_probe:$.summary.runtime_truth_leak_count" in artifact["blockers"]
    assert "unsafe_summary_probe:$.summary.ready_for_runtime_truth_count" in artifact["blockers"]
    assert "unsafe_summary_probe:$.summary.blocker_count" in artifact["blockers"]
    assert "unsafe_summary_probe:$.summary.blockers_count" in artifact["blockers"]
    assert "unsafe_summary_probe:$.summary.violations_count" in artifact["blockers"]
    assert "unsafe_summary_probe:$.summary.leaks" in artifact["blockers"]
    assert "unsafe_summary_probe:$.summary.leak_summary" in artifact["blockers"]
    assert "unsafe_summary_probe:$.summary.promotion_leak_count" in artifact["blockers"]
    assert "unsafe_summary_probe:$.summary.exact_candidate_leak_count" in artifact["blockers"]
    assert (
        "unsafe_summary_probe:$.websearch_candidates[0].summary.runtime_truth_allowed_count"
        in artifact["blockers"]
    )
    result = artifact["artifact_results"][0]
    assert result["blockers"].count("unsafe_summary_probe:$.blockers") == 1
    assert result["blockers"].count("unsafe_summary_probe:$.violations") == 1


def test_fooddb_websearch_no_runtime_wall_blocks_non_pass_source_statuses() -> None:
    artifact = build_fooddb_websearch_no_runtime_wall(
        artifacts=(
            {
                "artifact_type": "not_ready_probe",
                "status": "not_ready",
            },
            {
                "artifact_type": "blocked_input_probe",
                "status": "blocked_input_overclaim",
            },
            {
                "artifact_type": "ready_alias_probe",
                "status": "ready",
            },
            {
                "artifact_type": "success_alias_probe",
                "status": "success",
            },
        )
    )

    assert artifact["status"] == "blocked"
    assert "not_ready_probe:$.status" in artifact["blockers"]
    assert "blocked_input_probe:$.status" in artifact["blockers"]
    assert "ready_alias_probe:$.status" in artifact["blockers"]
    assert "success_alias_probe:$.status" in artifact["blockers"]


def test_fooddb_websearch_no_runtime_wall_does_not_block_non_candidate_fooddb_runtime_anchor_flags() -> None:
    artifact = build_fooddb_websearch_no_runtime_wall(
        artifacts=(
            {
                "artifact_type": "fooddb_status_packet_with_approved_anchor_summary",
                "runtime_truth_changed": False,
                "approval_required_before_runtime_truth": True,
                "anchors": [
                    {
                        "anchor_id": "approved_fooddb_anchor",
                        "runtime_role": "common_serving_anchor",
                        "runtime_truth_allowed": True,
                        "approval_metadata": {
                            "runtime_truth_allowed": True,
                        },
                    }
                ],
            },
        )
    )

    assert artifact["status"] == "pass"


def test_fooddb_websearch_no_runtime_wall_blocks_unapproved_runtime_truth_allowed() -> None:
    artifact = build_fooddb_websearch_no_runtime_wall(
        artifacts=(
            {
                "artifact_type": "unknown_report",
                "runtime_truth_allowed": True,
            },
            {
                "artifact_type": "fooddb_candidate_seed_report",
                "row": {
                    "runtime_role": "candidate_seed",
                    "runtime_truth_allowed": True,
                },
            },
            {
                "artifact_type": "accurate_intake_websearch_candidate_packet_smoke",
                "row": {
                    "runtime_role": "common_serving_anchor",
                    "runtime_truth_allowed": True,
                    "approval_metadata": {
                        "runtime_truth_allowed": True,
                    },
                },
            },
            {
                "artifact_type": "candidate_approval_metadata_probe",
                "approval_metadata": {
                    "runtime_truth_allowed": True,
                },
            },
        )
    )

    assert artifact["status"] == "blocked"
    assert "unknown_report:$.runtime_truth_allowed" in artifact["blockers"]
    assert "fooddb_candidate_seed_report:$.row.runtime_truth_allowed" in artifact["blockers"]
    assert (
        "accurate_intake_websearch_candidate_packet_smoke:$.row.runtime_truth_allowed"
        in artifact["blockers"]
    )
    assert (
        "candidate_approval_metadata_probe:$.approval_metadata.runtime_truth_allowed"
        in artifact["blockers"]
    )


def test_fooddb_websearch_no_runtime_wall_blocks_candidate_root_truth_fields() -> None:
    artifact = build_fooddb_websearch_no_runtime_wall(
        artifacts=(
            {
                "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
                "runtime_truth_allowed": True,
            },
            {
                "artifact_type": "accurate_intake_exact_card_candidate_promotion_readiness_v1",
                "promotion": "allowed",
                "truth": "selected",
            },
            {
                "artifact_type": "product_loop_probe",
                "product_loop_consumption": "integrated",
                "completed_product_loop_steps": ["api"],
            },
        )
    )

    assert artifact["status"] == "blocked"
    assert (
        "accurate_intake_websearch_candidate_lane_status_packet_v1:$.runtime_truth_allowed"
        in artifact["blockers"]
    )
    assert (
        "accurate_intake_exact_card_candidate_promotion_readiness_v1:$.promotion"
        in artifact["blockers"]
    )
    assert (
        "accurate_intake_exact_card_candidate_promotion_readiness_v1:$.truth"
        in artifact["blockers"]
    )
    assert "product_loop_probe:$.product_loop_consumption" in artifact["blockers"]
    assert "product_loop_probe:$.completed_product_loop_steps" in artifact["blockers"]


def test_fooddb_websearch_no_runtime_wall_treats_explicit_negative_strings_as_safe() -> None:
    artifact = build_fooddb_websearch_no_runtime_wall(
        artifacts=(
            {
                "artifact_type": "negative_claim_strings",
                "runtime_truth_changed": "not_changed",
                "live_provider_used": "not_used",
                "mutation_allowed": "false",
                "product_readiness_claimed": "no",
            },
        )
    )

    assert artifact["status"] == "pass"


def test_fooddb_websearch_no_runtime_wall_does_not_block_artifact_type_metadata() -> None:
    artifact = build_fooddb_websearch_no_runtime_wall(
        artifacts=(
            {
                "artifact_type": "safe_metadata_probe",
                "source_artifacts": {
                    "exact_card_readiness_artifact_type": (
                        "accurate_intake_exact_card_candidate_promotion_readiness_v1"
                    ),
                },
            },
        )
    )

    assert artifact["status"] == "pass"


def test_fooddb_websearch_no_runtime_wall_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_websearch_no_runtime_wall import main

    output_path = tmp_path / "no_runtime_wall.json"

    assert main(["--output", str(output_path)]) == 0

    artifact = read_json_artifact(output_path)
    assert artifact["artifact_type"] == "accurate_intake_fooddb_websearch_no_runtime_wall_v1"
    assert artifact["status"] == "pass"


def test_fooddb_websearch_no_runtime_wall_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/nutrition/application/fooddb_websearch_no_runtime_wall.py"),
        Path("scripts/build_accurate_intake_fooddb_websearch_no_runtime_wall.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "ManagerContextPacket",
        "BuilderSpaceAdapter",
        "TavilyAdapter",
        "runtime_truth_changed = True",
        "live_provider_used = True",
        "live_websearch_used = True",
        "readiness_claimed = True",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source
