from __future__ import annotations

from pathlib import Path

from app.nutrition.application.exact_card_candidate_promotion_readiness import (
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (
    build_exact_evidence_lane_policy_artifact,
)
from app.nutrition.application.grokfast_websearch_packet_diagnostic import (
    build_fixture_manager_outputs as build_fixture_live_manager_outputs,
    build_grokfast_websearch_packet_diagnostic,
)
from app.nutrition.application.websearch_candidate_lane_status_packet import (
    build_websearch_candidate_lane_status_packet,
)
from app.nutrition.application.websearch_candidate_pipeline import (
    build_websearch_candidate_pipeline_diagnostic,
)
from app.nutrition.application.websearch_exact_candidate_review_packet import (
    build_websearch_exact_candidate_review_packet,
)
from app.nutrition.application.websearch_extract_result_candidate_smoke import (
    build_websearch_extract_result_candidate_smoke,
)
from app.nutrition.application.websearch_live_diagnostic_report import (
    build_websearch_live_diagnostic_report,
)
from app.nutrition.application.websearch_live_extract_preflight import (
    build_websearch_live_extract_preflight,
)
from app.nutrition.application.websearch_manager_contract_handoff import (
    build_websearch_manager_contract_handoff,
)
from app.nutrition.application.websearch_manager_contract_probe import (
    build_websearch_manager_contract_probe,
)
from app.nutrition.application.websearch_manager_contract_repair_pack import (
    build_websearch_manager_contract_repair_pack,
)
from app.nutrition.application.websearch_preflight_digest import (
    PREFLIGHT_DIGEST_ALGORITHM,
    PREFLIGHT_DIGEST_SCOPE,
    websearch_live_extract_preflight_digest,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (
    build_websearch_selected_extract_packet_smoke,
)


def _clear_preflight_artifact() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_live_extract_preflight_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": "2026-05-06T00:00:00Z",
        "track": "FDB",
        "classification": "deterministic_live_extract_preflight_only",
        "claim_scope": "websearch_live_extract_diagnostic_preflight_without_live_call",
        "status": "pass",
        "blockers": [],
        "live_websearch_used": False,
        "live_extract_used": False,
        "live_provider_used": False,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "readiness_claimed": False,
        "ready_for_live_extract_diagnostic": True,
        "ready_for_runtime_truth": False,
        "diagnostic_contract": {
            "live_call_allowed_by_this_artifact": False,
            "requires_explicit_allow_live_flag": True,
            "cache_required": True,
            "raw_content_allowed_in_manager_context": False,
            "ledger_mutation_allowed": False,
            "exact_card_creation_allowed": False,
        },
        "review_packet_refs": [
            {
                "packet_id": "pkt_exact_card_review_123456789abc",
                "source_url": "https://milksha.example/menu/pearl-black-tea-latte",
                "canonical_name": "Milksha pearl black tea latte",
                "matched_name": "Milksha pearl black tea latte",
                "packet_digest": "abc123def4567890",
            }
        ],
        "summary": {
            "review_packet_count": 1,
            "ready_for_live_extract_diagnostic_count": 1,
            "ready_for_runtime_truth_count": 0,
            "case_matrix_case_count": 6,
            "case_matrix_fixed_required_cases": True,
            "case_matrix_negative_case_count": 4,
            "case_matrix_modifier_guard_cases": 1,
            "case_matrix_live_provider_invoked": False,
            "case_matrix_websearch_invoked": False,
        },
        "next_required_slice": "grokfast_websearch_packet_live_diagnostic",
        "non_claims": [
            "no_live_websearch_call",
            "no_live_extract_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_readiness_claim",
        ],
    }


def _live_report(*, preflight_artifact: dict) -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_live_diagnostic_report",
        "seam_status": "live_diagnostic_pass",
        "source_artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "source_status": "pass",
        "preflight_evidence_healthy": True,
        "preflight_evidence_required": True,
        "preflight_evidence": {
            "preflight_artifact_digest_algorithm": PREFLIGHT_DIGEST_ALGORITHM,
            "preflight_artifact_digest_scope": PREFLIGHT_DIGEST_SCOPE,
            "preflight_artifact_digest": websearch_live_extract_preflight_digest(
                preflight_artifact
            ),
            "preflight_artifact_digest_verified": True,
            "preflight_artifact_integrity_clear": True,
            "ready_for_runtime_truth": False,
        },
        "can_expand_websearch_candidate_pipeline": True,
        "source_live_provider_used": True,
        "source_live_websearch_used": False,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "next_recommended_slice": "inspect_websearch_status_packet",
        "non_claims": [
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_kimi_call",
            "no_runtime_mutation",
            "no_websearch_runtime_truth",
            "no_fooddb_truth_promotion",
            "no_exact_card_truth_promotion",
            "no_readiness_claim",
        ],
    }


def _probe() -> dict:
    cases = [
        {
            "case_id": "grokfast_websearch_exact_candidate_intent_type_only",
            "status": "pass",
            "failure_families": [],
            "missing_required_fields": [],
            "shape_patterns": [],
            "observed_keys": [
                "confidence",
                "evidence_posture",
                "exactness",
                "intent",
                "manager_action",
                "repair_ack",
                "target_attachment",
                "workflow_effect",
            ],
            "validation_error_family": None,
            "raw_manager_output_included": False,
            "provider_trace_included": False,
        },
        {
            "case_id": "grokfast_websearch_size_followup_intent_type_only",
            "status": "pass",
            "failure_families": [],
            "missing_required_fields": [],
            "shape_patterns": [],
            "observed_keys": [
                "confidence",
                "evidence_posture",
                "exactness",
                "intent",
                "manager_action",
                "repair_ack",
                "target_attachment",
                "workflow_effect",
            ],
            "validation_error_family": None,
            "raw_manager_output_included": False,
            "provider_trace_included": False,
        },
    ]
    return {
        "artifact_type": "accurate_intake_websearch_manager_contract_probe",
        "status": "pass",
        "contract_failure_detected": False,
        "artifact_schema_version": "1.0",
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "manager_contract_changed": False,
        "prompt_changed": False,
        "schema_changed": False,
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "fail_count": 0,
            "aggregate_missing_required_fields": {},
            "next_recommended_slice": "narrow_prompt_schema_intent_alias_probe",
        },
        "non_claims": [
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_kimi_call",
            "no_prompt_or_schema_change",
            "no_runtime_mutation",
            "no_websearch_runtime_truth",
            "no_fooddb_truth_promotion",
            "no_exact_card_truth_promotion",
            "no_readiness_claim",
        ],
    }


def _repair_pack() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_manager_contract_repair_pack",
        "artifact_schema_version": "1.0",
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "manager_contract_changed": False,
        "prompt_changed": False,
        "schema_changed": False,
        "readiness_claimed": False,
        "next_recommended_slice": "tighten_websearch_manager_contract_prompt_or_transport",
        "summary": {
            "case_count": 0,
            "aggregate_missing_required_fields": {},
            "alias_hint_counts": {},
            "shape_pattern_counts": {},
        },
        "cases": [],
        "non_claims": [
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_prompt_or_schema_change",
            "no_manager_contract_change",
            "no_runtime_truth_promotion",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_packetizer_format_change",
            "no_manager_context_change",
            "no_websearch_runtime_truth",
            "no_readiness_claim",
        ],
    }


def _verified_handoff_inputs() -> dict:
    preflight = _clear_preflight_artifact()
    live_report = _live_report(preflight_artifact=preflight)
    probe = _probe()
    repair_pack = _repair_pack()
    handoff = build_websearch_manager_contract_handoff(
        live_diagnostic_report=live_report,
        contract_probe_artifact=probe,
        repair_pack_artifact=repair_pack,
        preflight_artifact=preflight,
    )
    return {
        "manager_contract_handoff_artifact": handoff,
        "live_diagnostic_report": live_report,
        "contract_probe_artifact": probe,
        "repair_pack_artifact": repair_pack,
        "preflight_artifact": preflight,
    }


def _realistic_verified_handoff_inputs() -> dict:
    readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    selected_extract = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=readiness
    )
    extract_result = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected_extract
    )
    review_packet = build_websearch_exact_candidate_review_packet(
        extract_result_artifact=extract_result
    )
    preflight = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet
    )
    diagnostic = build_grokfast_websearch_packet_diagnostic(
        review_packet_artifact=review_packet,
        manager_outputs=build_fixture_live_manager_outputs(
            review_packet_artifact=review_packet
        ),
        live_provider_used=True,
    )
    diagnostic["preflight_ref"] = {
        "preflight_ref_source": "run_accurate_intake_grokfast_websearch_packet_smoke",
        "artifact_type": preflight.get("artifact_type"),
        "status": preflight.get("status"),
        "ready_for_live_extract_diagnostic": preflight.get("ready_for_live_extract_diagnostic"),
        "ready_for_runtime_truth": preflight.get("ready_for_runtime_truth"),
        "review_packet_authorized": True,
        "review_packet_count": preflight["summary"].get("review_packet_count"),
        "case_matrix_case_count": preflight["summary"].get("case_matrix_case_count"),
        "case_matrix_fixed_required_cases": preflight["summary"].get(
            "case_matrix_fixed_required_cases"
        ),
        "case_matrix_negative_case_count": preflight["summary"].get(
            "case_matrix_negative_case_count"
        ),
        "case_matrix_modifier_guard_cases": preflight["summary"].get(
            "case_matrix_modifier_guard_cases"
        ),
        "case_matrix_live_provider_invoked": preflight["summary"].get(
            "case_matrix_live_provider_invoked"
        ),
        "case_matrix_websearch_invoked": preflight["summary"].get(
            "case_matrix_websearch_invoked"
        ),
        "preflight_artifact_digest_algorithm": PREFLIGHT_DIGEST_ALGORITHM,
        "preflight_artifact_digest_scope": PREFLIGHT_DIGEST_SCOPE,
        "preflight_artifact_digest": websearch_live_extract_preflight_digest(preflight),
    }
    live_report = build_websearch_live_diagnostic_report(
        diagnostic_artifact=diagnostic,
        preflight_artifact=preflight,
    )
    probe = build_websearch_manager_contract_probe(diagnostic_artifact=diagnostic)
    repair_pack = build_websearch_manager_contract_repair_pack(
        contract_probe_artifact=probe
    )
    handoff = build_websearch_manager_contract_handoff(
        live_diagnostic_report=live_report,
        contract_probe_artifact=probe,
        repair_pack_artifact=repair_pack,
        preflight_artifact=preflight,
    )
    return {
        "manager_contract_handoff_artifact": handoff,
        "live_diagnostic_report": live_report,
        "contract_probe_artifact": probe,
        "repair_pack_artifact": repair_pack,
        "preflight_artifact": preflight,
    }


def _fooddb_status_packet() -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
        "next_required_slices": ["await_manager_contract_owner_repair"],
    }


def test_websearch_candidate_lane_status_packet_summarizes_deterministic_lane() -> None:
    artifact = build_websearch_candidate_lane_status_packet()
    pipeline_summary = build_websearch_candidate_pipeline_diagnostic()["summary"]

    assert artifact["artifact_type"] == "accurate_intake_websearch_candidate_lane_status_packet_v1"
    assert artifact["classification"] == "deterministic_websearch_candidate_lane_status_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["source_policy_max_search_attempts"] == 2
    assert artifact["summary"]["source_policy_max_results"] == 5
    assert artifact["summary"]["source_adapter_guard_status"] == "pass"
    assert artifact["summary"]["source_adapter_guard_case_count"] == 3
    assert artifact["summary"]["source_adapter_guard_max_results_hard_cap"] == 20
    assert artifact["summary"]["pipeline_case_count"] >= 4
    assert artifact["summary"]["extract_candidate_allowed_count"] >= 1
    assert artifact["summary"]["pipeline_exact_review_candidate_count"] >= 6
    assert artifact["summary"]["pipeline_disambiguation_candidate_count"] >= 5
    assert artifact["summary"]["pipeline_blocked_candidate_count"] >= 4
    assert artifact["summary"]["pipeline_policy_blocked_exact_candidate_count"] >= 1
    assert artifact["summary"]["pipeline_weak_candidate_count"] >= 3
    assert artifact["summary"]["candidate_packet_case_count"] == 6
    assert artifact["summary"]["pipeline_case_count"] == 23
    assert pipeline_summary["candidate_packet_count"] == sum(
        artifact["summary"][key]
        for key in (
            "pipeline_exact_review_candidate_count",
            "pipeline_disambiguation_candidate_count",
            "pipeline_blocked_candidate_count",
            "pipeline_policy_blocked_exact_candidate_count",
            "pipeline_weak_candidate_count",
        )
    )
    assert artifact["summary"]["candidate_only_packet_count"] == 6
    assert artifact["summary"]["manager_projection_case_count"] == 6
    assert artifact["summary"]["manager_projection_compact_count"] == 6
    assert artifact["summary"]["upstream_fooddb_gate_status"] == "not_provided"
    assert artifact["summary"]["manager_contract_gate_status"] == "not_provided"
    assert artifact["next_required_slices"] == ["inspect_fooddb_status_packet"]


def test_websearch_candidate_lane_status_packet_blocks_when_source_adapter_guard_blocks() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        source_adapter_guard_artifact={
            "artifact_type": "accurate_intake_websearch_source_adapter_guard_v1",
            "status": "blocked",
            "blockers": ["raw_provider_truth_marker"],
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_provider_used": False,
            "live_websearch_used": False,
            "readiness_claimed": False,
            "summary": {
                "case_count": 3,
                "truth_field_leak_count": 1,
                "max_results_hard_cap": 20,
            },
        }
    )

    assert artifact["summary"]["source_adapter_guard_status"] == "blocked_on_source_adapter_guard"
    assert artifact["source_adapter_gate"]["truth_field_leak_count"] == 1
    assert artifact["next_required_slices"] == ["inspect_websearch_source_adapter_guard"]


def test_websearch_candidate_lane_status_packet_blocks_source_adapter_guard_overclaims() -> None:
    for forbidden_key in (
        "runtime_truth_changed",
        "mutation_changed",
        "live_provider_used",
        "live_websearch_used",
        "readiness_claimed",
    ):
        guard = {
            "artifact_type": "accurate_intake_websearch_source_adapter_guard_v1",
            "status": "pass",
            "blockers": [],
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_provider_used": False,
            "live_websearch_used": False,
            "readiness_claimed": False,
            "summary": {
                "case_count": 3,
                "truth_field_leak_count": 0,
                "max_results_hard_cap": 20,
            },
        }
        guard[forbidden_key] = True

        artifact = build_websearch_candidate_lane_status_packet(
            source_adapter_guard_artifact=guard
        )

        assert artifact["summary"]["source_adapter_guard_status"] == (
            "blocked_on_source_adapter_guard"
        )
        assert artifact["next_required_slices"] == ["inspect_websearch_source_adapter_guard"]


def test_websearch_candidate_lane_status_packet_blocks_inconsistent_source_adapter_guard_summary() -> None:
    base_guard = {
        "artifact_type": "accurate_intake_websearch_source_adapter_guard_v1",
        "status": "pass",
        "blockers": [],
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "case_count": 3,
            "truth_field_leak_count": 0,
            "max_results_hard_cap": 20,
        },
    }
    summary_mutations = (
        {"case_count": 0},
        {"truth_field_leak_count": 1},
        {"max_results_hard_cap": 999},
    )

    for mutation in summary_mutations:
        guard = {**base_guard, "summary": {**base_guard["summary"], **mutation}}

        artifact = build_websearch_candidate_lane_status_packet(
            source_adapter_guard_artifact=guard
        )

        assert artifact["summary"]["source_adapter_guard_status"] == (
            "blocked_on_source_adapter_guard"
        )
        assert artifact["next_required_slices"] == ["inspect_websearch_source_adapter_guard"]


def test_websearch_candidate_lane_status_packet_blocks_on_fooddb_manager_contract_gate() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet=_fooddb_status_packet()
    )

    assert artifact["summary"]["upstream_fooddb_gate_status"] == "blocked_on_fooddb_upstream_gate"
    assert artifact["summary"]["upstream_fooddb_next_required_slice"] == "await_manager_contract_owner_repair"
    assert artifact["next_required_slices"] == ["await_manager_contract_owner_repair"]


def test_websearch_candidate_lane_status_packet_allows_live_only_when_fooddb_explicitly_points_to_websearch() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        **_verified_handoff_inputs(),
    )

    assert artifact["summary"]["upstream_fooddb_gate_status"] == "clear_for_websearch_lane"
    assert artifact["summary"]["manager_contract_gate_status"] == "clear_for_websearch_lane"
    assert artifact["next_required_slices"] == ["grokfast_websearch_packet_live_diagnostic"]


def test_websearch_candidate_lane_status_packet_requires_manager_contract_handoff_when_fooddb_clear() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        }
    )

    assert artifact["summary"]["upstream_fooddb_gate_status"] == "clear_for_websearch_lane"
    assert artifact["summary"]["manager_contract_gate_status"] == "not_provided"
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_on_manager_contract_handoff() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact={
            "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
            "status": "ready_for_manager_contract_owner",
            "selected_next_step": "tighten_websearch_manager_contract_prompt_or_transport",
        },
    )

    assert artifact["summary"]["upstream_fooddb_gate_status"] == "clear_for_websearch_lane"
    assert artifact["summary"]["manager_contract_gate_status"] == "blocked_on_manager_contract_owner"
    assert artifact["next_required_slices"] == [
        "tighten_websearch_manager_contract_prompt_or_transport"
    ]


def test_websearch_candidate_lane_status_packet_allows_live_when_manager_contract_unblocked() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        **_verified_handoff_inputs(),
    )

    assert artifact["summary"]["manager_contract_gate_status"] == "clear_for_websearch_lane"
    assert artifact["next_required_slices"] == ["grokfast_websearch_packet_live_diagnostic"]


def test_websearch_candidate_lane_status_packet_allows_realistic_live_bundle_contract_chain() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        **_realistic_verified_handoff_inputs(),
    )

    assert artifact["summary"]["manager_contract_gate_status"] == "clear_for_websearch_lane"
    assert artifact["manager_contract_gate"]["blockers"] == []
    assert artifact["next_required_slices"] == ["grokfast_websearch_packet_live_diagnostic"]


def test_websearch_candidate_lane_status_packet_blocks_unverified_unblocked_manager_contract() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact={
            "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
            "status": "websearch_contract_unblocked",
            "selected_next_step": "inspect_websearch_status_packet",
            "summary": {"alignment_blocker_count": 0},
        },
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert (
        "manager_contract_handoff_source_artifacts_missing"
        in artifact["manager_contract_gate"]["blockers"]
    )
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_mismatched_handoff_source_chain() -> None:
    inputs = _verified_handoff_inputs()
    probe = {
        **inputs["contract_probe_artifact"],
        "summary": {
            **inputs["contract_probe_artifact"]["summary"],
            "case_count": 0,
        },
    }

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=probe,
        repair_pack_artifact=inputs["repair_pack_artifact"],
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "manager_contract_handoff_derivation_mismatch" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_mismatched_sanitized_handoff_maps() -> None:
    inputs = _verified_handoff_inputs()
    probe = {
        **inputs["contract_probe_artifact"],
        "summary": {
            **inputs["contract_probe_artifact"]["summary"],
            "aggregate_missing_required_fields": {"intent": 1},
        },
    }

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=probe,
        repair_pack_artifact=inputs["repair_pack_artifact"],
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "manager_contract_handoff_derivation_mismatch" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_vacuous_verified_handoff_chain() -> None:
    preflight = _clear_preflight_artifact()
    live_report = _live_report(preflight_artifact=preflight)
    probe = {
        "artifact_type": "accurate_intake_websearch_manager_contract_probe",
        "status": "pass",
        "contract_failure_detected": False,
        "summary": {
            "case_count": 0,
            "fail_count": 0,
            "aggregate_missing_required_fields": {},
            "next_recommended_slice": "narrow_prompt_schema_intent_alias_probe",
        },
    }
    repair_pack = _repair_pack()
    handoff = build_websearch_manager_contract_handoff(
        live_diagnostic_report=live_report,
        contract_probe_artifact=probe,
        repair_pack_artifact=repair_pack,
        preflight_artifact=preflight,
    )

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=handoff,
        live_diagnostic_report=live_report,
        contract_probe_artifact=probe,
        repair_pack_artifact=repair_pack,
        preflight_artifact=preflight,
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "manager_contract_handoff_probe_evidence_missing" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_summary_only_probe_chain() -> None:
    preflight = _clear_preflight_artifact()
    live_report = _live_report(preflight_artifact=preflight)
    probe = {
        "artifact_type": "accurate_intake_websearch_manager_contract_probe",
        "status": "pass",
        "contract_failure_detected": False,
        "summary": {
            "case_count": 2,
            "fail_count": 0,
            "aggregate_missing_required_fields": {},
            "next_recommended_slice": "narrow_prompt_schema_intent_alias_probe",
        },
    }
    repair_pack = _repair_pack()
    handoff = build_websearch_manager_contract_handoff(
        live_diagnostic_report=live_report,
        contract_probe_artifact=probe,
        repair_pack_artifact=repair_pack,
        preflight_artifact=preflight,
    )

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=handoff,
        live_diagnostic_report=live_report,
        contract_probe_artifact=probe,
        repair_pack_artifact=repair_pack,
        preflight_artifact=preflight,
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "manager_contract_handoff_probe_cases_missing" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_non_pass_probe_case_chain() -> None:
    inputs = _verified_handoff_inputs()
    probe = {
        **inputs["contract_probe_artifact"],
        "cases": [
            {**inputs["contract_probe_artifact"]["cases"][0], "status": "fail"},
            inputs["contract_probe_artifact"]["cases"][1],
        ],
    }

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=probe,
        repair_pack_artifact=inputs["repair_pack_artifact"],
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "manager_contract_handoff_probe_case_not_pass" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_minimal_pass_probe_cases() -> None:
    preflight = _clear_preflight_artifact()
    live_report = _live_report(preflight_artifact=preflight)
    probe = {
        "artifact_type": "accurate_intake_websearch_manager_contract_probe",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "contract_failure_detected": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "manager_contract_changed": False,
        "prompt_changed": False,
        "schema_changed": False,
        "cases": [
            {
                "status": "pass",
                "failure_families": [],
                "raw_manager_output_included": False,
                "provider_trace_included": False,
            },
            {
                "status": "pass",
                "failure_families": [],
                "raw_manager_output_included": False,
                "provider_trace_included": False,
            },
        ],
        "summary": {
            "case_count": 2,
            "fail_count": 0,
            "aggregate_missing_required_fields": {},
            "next_recommended_slice": "narrow_prompt_schema_intent_alias_probe",
        },
        "non_claims": [
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_runtime_mutation",
            "no_websearch_runtime_truth",
            "no_readiness_claim",
        ],
    }
    repair_pack = _repair_pack()
    handoff = build_websearch_manager_contract_handoff(
        live_diagnostic_report=live_report,
        contract_probe_artifact=probe,
        repair_pack_artifact=repair_pack,
        preflight_artifact=preflight,
    )

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=handoff,
        live_diagnostic_report=live_report,
        contract_probe_artifact=probe,
        repair_pack_artifact=repair_pack,
        preflight_artifact=preflight,
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "manager_contract_handoff_probe_case_id_missing" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert "manager_contract_handoff_probe_case_missing_required_fields_missing" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_probe_case_missing_failure_families() -> None:
    inputs = _verified_handoff_inputs()
    case_without_failure_families = dict(inputs["contract_probe_artifact"]["cases"][0])
    case_without_failure_families.pop("failure_families")
    probe = {
        **inputs["contract_probe_artifact"],
        "cases": [
            case_without_failure_families,
            inputs["contract_probe_artifact"]["cases"][1],
        ],
    }

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=probe,
        repair_pack_artifact=inputs["repair_pack_artifact"],
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "manager_contract_handoff_probe_case_failure_families_missing" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_probe_case_extra_raw_payload() -> None:
    inputs = _verified_handoff_inputs()
    case_with_raw_payload = {
        **inputs["contract_probe_artifact"]["cases"][0],
        "raw_manager_output": {"intent": "log_food_item"},
    }
    probe = {
        **inputs["contract_probe_artifact"],
        "cases": [
            case_with_raw_payload,
            inputs["contract_probe_artifact"]["cases"][1],
        ],
    }

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=probe,
        repair_pack_artifact=inputs["repair_pack_artifact"],
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "manager_contract_handoff_probe_case_unexpected_keys" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_probe_case_raw_observed_keys() -> None:
    inputs = _verified_handoff_inputs()
    case_with_raw_observed_keys = {
        **inputs["contract_probe_artifact"]["cases"][0],
        "observed_keys": ["provider_trace", "raw_manager_output"],
    }
    probe = {
        **inputs["contract_probe_artifact"],
        "cases": [
            case_with_raw_observed_keys,
            inputs["contract_probe_artifact"]["cases"][1],
        ],
    }

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=probe,
        repair_pack_artifact=inputs["repair_pack_artifact"],
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "manager_contract_handoff_probe_case_observed_keys_unexpected" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_source_artifact_overclaims() -> None:
    inputs = _verified_handoff_inputs()
    probe = {**inputs["contract_probe_artifact"], "readiness_claimed": True}
    repair_pack = {**inputs["repair_pack_artifact"], "prompt_changed": True}

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=probe,
        repair_pack_artifact=repair_pack,
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "contract_probe_claimed_readiness" in artifact["manager_contract_gate"]["blockers"]
    assert "repair_pack_changed_prompt" in artifact["manager_contract_gate"]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_live_report_overclaims() -> None:
    inputs = _verified_handoff_inputs()
    live_report = {**inputs["live_diagnostic_report"], "shared_contract_changed": True}

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=live_report,
        contract_probe_artifact=inputs["contract_probe_artifact"],
        repair_pack_artifact=inputs["repair_pack_artifact"],
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "live_report_changed_shared_contract" in artifact["manager_contract_gate"][
        "blockers"
    ]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_preflight_overclaims() -> None:
    inputs = _verified_handoff_inputs()
    preflight = {**inputs["preflight_artifact"], "product_readiness_claimed": True}

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=inputs["contract_probe_artifact"],
        repair_pack_artifact=inputs["repair_pack_artifact"],
        preflight_artifact=preflight,
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "preflight_claimed_product_readiness" in artifact["manager_contract_gate"][
        "blockers"
    ]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_missing_source_non_claims() -> None:
    inputs = _verified_handoff_inputs()
    probe = dict(inputs["contract_probe_artifact"])
    probe.pop("non_claims")

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=probe,
        repair_pack_artifact=inputs["repair_pack_artifact"],
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "contract_probe_non_claims_missing" in artifact["manager_contract_gate"][
        "blockers"
    ]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_incomplete_source_non_claims() -> None:
    inputs = _verified_handoff_inputs()
    preflight = {
        **inputs["preflight_artifact"],
        "non_claims": ["no_live_websearch_call"],
    }
    live_report = _live_report(preflight_artifact=preflight)
    handoff = build_websearch_manager_contract_handoff(
        live_diagnostic_report=live_report,
        contract_probe_artifact=inputs["contract_probe_artifact"],
        repair_pack_artifact=inputs["repair_pack_artifact"],
        preflight_artifact=preflight,
    )

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=handoff,
        live_diagnostic_report=live_report,
        contract_probe_artifact=inputs["contract_probe_artifact"],
        repair_pack_artifact=inputs["repair_pack_artifact"],
        preflight_artifact=preflight,
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "preflight_missing_non_claim.no_runtime_mutation" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert "preflight_missing_non_claim.no_manager_context_change" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_repair_pack_map_drift() -> None:
    inputs = _verified_handoff_inputs()
    repair_pack = {
        **inputs["repair_pack_artifact"],
        "summary": {
            **inputs["repair_pack_artifact"]["summary"],
            "aggregate_missing_required_fields": {"intent": 1},
        },
    }

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=inputs["contract_probe_artifact"],
        repair_pack_artifact=repair_pack,
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "repair_pack_non_empty_missing_field_map_for_unblocked_handoff" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_non_exact_clean_repair_maps() -> None:
    inputs = _verified_handoff_inputs()
    repair_pack = {
        **inputs["repair_pack_artifact"],
        "summary": {
            **inputs["repair_pack_artifact"]["summary"],
            "aggregate_missing_required_fields": {"intent": "0"},
        },
    }

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=inputs["contract_probe_artifact"],
        repair_pack_artifact=repair_pack,
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "repair_pack_non_empty_missing_field_map_for_unblocked_handoff" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_vacuous_repair_pack_clean_evidence() -> None:
    inputs = _verified_handoff_inputs()
    repair_pack = {
        **inputs["repair_pack_artifact"],
        "summary": {"case_count": 0},
    }
    repair_pack.pop("cases")

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=inputs["contract_probe_artifact"],
        repair_pack_artifact=repair_pack,
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "repair_pack_missing_clean_missing_field_map_for_unblocked_handoff" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert "repair_pack_cases_missing_for_unblocked_handoff" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_blocks_non_pass_repair_pack_case() -> None:
    inputs = _verified_handoff_inputs()
    repair_pack = {
        **inputs["repair_pack_artifact"],
        "summary": {
            **inputs["repair_pack_artifact"]["summary"],
            "case_count": 1,
        },
        "cases": [
            {
                "case_id": "case_001",
                "status": "fail",
                "failure_families": ["manager_output_contract_violation"],
                "missing_required_fields": ["intent"],
                "shape_patterns": ["intent_type_present_intent_missing"],
            }
        ],
    }

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact=inputs["manager_contract_handoff_artifact"],
        live_diagnostic_report=inputs["live_diagnostic_report"],
        contract_probe_artifact=inputs["contract_probe_artifact"],
        repair_pack_artifact=repair_pack,
        preflight_artifact=inputs["preflight_artifact"],
    )

    assert artifact["summary"]["manager_contract_gate_status"] == (
        "blocked_on_manager_contract_handoff"
    )
    assert "repair_pack_non_pass_case_for_unblocked_handoff" in artifact[
        "manager_contract_gate"
    ]["blockers"]
    assert artifact["next_required_slices"] == ["inspect_websearch_manager_contract_handoff"]


def test_websearch_candidate_lane_status_packet_rejects_unexpected_manager_contract_artifact() -> None:
    try:
        build_websearch_candidate_lane_status_packet(
            manager_contract_handoff_artifact={"artifact_type": "wrong"}
        )
    except ValueError as exc:
        assert "unsupported_websearch_status_manager_contract_handoff" in str(exc)
    else:
        raise AssertionError("unexpected manager contract artifact type must fail")


def test_websearch_candidate_lane_status_packet_rejects_unexpected_source_adapter_guard() -> None:
    try:
        build_websearch_candidate_lane_status_packet(
            source_adapter_guard_artifact={"artifact_type": "wrong"}
        )
    except ValueError as exc:
        assert "unsupported_websearch_status_source_adapter_guard" in str(exc)
    else:
        raise AssertionError("unexpected source adapter guard artifact type must fail")


def test_websearch_candidate_lane_status_packet_rejects_empty_source_adapter_guard() -> None:
    try:
        build_websearch_candidate_lane_status_packet(source_adapter_guard_artifact={})
    except ValueError as exc:
        assert "unsupported_websearch_status_source_adapter_guard" in str(exc)
    else:
        raise AssertionError("empty source adapter guard artifact must fail")


def test_websearch_candidate_lane_status_packet_sanitizes_manager_contract_next_step() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        manager_contract_handoff_artifact={
            "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
            "status": "ready_for_manager_contract_owner",
            "selected_next_step": "raw_response_excerpt forbidden",
        },
    )

    serialized = str(artifact)
    assert "raw_response_excerpt" not in serialized
    assert "forbidden" not in serialized
    assert artifact["next_required_slices"] == [
        "tighten_websearch_manager_contract_prompt_or_transport"
    ]


def test_websearch_candidate_lane_status_packet_blocks_other_fooddb_pending_states() -> None:
    for next_required in (
        "common_serving_anchor_expansion",
        "manager_fooddb_packet_seam_smoke",
        "grokfast_fooddb_packet_live_diagnostic",
    ):
        artifact = build_websearch_candidate_lane_status_packet(
            fooddb_status_packet={
                "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
                "next_required_slices": [next_required],
            }
        )
        assert artifact["summary"]["upstream_fooddb_gate_status"] == "blocked_on_fooddb_upstream_gate"
        assert artifact["next_required_slices"] == [next_required]


def test_websearch_candidate_lane_status_packet_sanitizes_fooddb_next_required_slice() -> None:
    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet={
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["raw_response_excerpt forbidden"],
        },
        manager_contract_handoff_artifact={
            "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
            "status": "websearch_contract_unblocked",
            "selected_next_step": "inspect_websearch_status_packet",
        },
    )

    serialized = str(artifact)
    assert "raw_response_excerpt" not in serialized
    assert "forbidden" not in serialized
    assert artifact["summary"]["upstream_fooddb_next_required_slice"] == "inspect_fooddb_status_packet"
    assert artifact["next_required_slices"] == ["inspect_fooddb_status_packet"]


def test_websearch_candidate_lane_status_packet_excludes_raw_and_truth_payloads() -> None:
    artifact = build_websearch_candidate_lane_status_packet()
    serialized = str(artifact)

    for token in (
        "raw_hits",
        "raw_search_results",
        "runtime_truth_allowed': True",
        "likely_kcal",
        "kcal_range",
        "adapter_kind",
        "storage_backend",
        "supabase",
        "snippet",
        "source_url",
        "raw_provider_truth_marker",
    ):
        assert token not in serialized


def test_websearch_candidate_lane_status_packet_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_candidate_lane_status_packet import main

    fooddb_input = tmp_path / "fooddb_status.json"
    output = tmp_path / "websearch_status.json"
    write_json_artifact(fooddb_input, _fooddb_status_packet())

    assert (
        main(
            [
                "--fooddb-status-packet",
                str(fooddb_input),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_candidate_lane_status_packet_v1"
    assert artifact["next_required_slices"] == ["await_manager_contract_owner_repair"]


def test_websearch_candidate_lane_status_packet_script_accepts_manager_contract_gate(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_candidate_lane_status_packet import main

    fooddb_input = tmp_path / "fooddb_status.json"
    handoff_input = tmp_path / "handoff.json"
    output = tmp_path / "websearch_status.json"
    write_json_artifact(
        fooddb_input,
        {
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
    )
    write_json_artifact(
        handoff_input,
        {
            "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
            "status": "ready_for_manager_contract_owner",
            "selected_next_step": "tighten_websearch_manager_contract_prompt_or_transport",
        },
    )

    assert (
        main(
            [
                "--fooddb-status-packet",
                str(fooddb_input),
                "--manager-contract-handoff-artifact",
                str(handoff_input),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["next_required_slices"] == [
        "tighten_websearch_manager_contract_prompt_or_transport"
    ]


def test_websearch_candidate_lane_status_packet_script_accepts_verified_handoff_chain(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_candidate_lane_status_packet import main

    inputs = _verified_handoff_inputs()
    paths = {
        "fooddb": tmp_path / "fooddb_status.json",
        "handoff": tmp_path / "handoff.json",
        "live": tmp_path / "live.json",
        "probe": tmp_path / "probe.json",
        "repair": tmp_path / "repair.json",
        "preflight": tmp_path / "preflight.json",
    }
    output = tmp_path / "websearch_status.json"
    write_json_artifact(
        paths["fooddb"],
        {
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
    )
    write_json_artifact(paths["handoff"], inputs["manager_contract_handoff_artifact"])
    write_json_artifact(paths["live"], inputs["live_diagnostic_report"])
    write_json_artifact(paths["probe"], inputs["contract_probe_artifact"])
    write_json_artifact(paths["repair"], inputs["repair_pack_artifact"])
    write_json_artifact(paths["preflight"], inputs["preflight_artifact"])

    assert (
        main(
            [
                "--fooddb-status-packet",
                str(paths["fooddb"]),
                "--manager-contract-handoff-artifact",
                str(paths["handoff"]),
                "--live-diagnostic-report",
                str(paths["live"]),
                "--contract-probe-artifact",
                str(paths["probe"]),
                "--repair-pack-artifact",
                str(paths["repair"]),
                "--preflight-artifact",
                str(paths["preflight"]),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["summary"]["manager_contract_gate_status"] == "clear_for_websearch_lane"
    assert artifact["next_required_slices"] == ["grokfast_websearch_packet_live_diagnostic"]


def test_websearch_candidate_lane_status_packet_script_accepts_live_bundle_manifest(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_candidate_lane_status_packet import main

    inputs = _verified_handoff_inputs()
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    paths = {
        "fooddb": tmp_path / "fooddb_status.json",
        "handoff": bundle_dir / "websearch_contract_handoff.json",
        "probe": bundle_dir / "websearch_contract_probe.json",
        "repair": bundle_dir / "websearch_contract_repair.json",
        "live": bundle_dir / "websearch_live_report.json",
        "preflight": bundle_dir / "websearch_live_preflight.json",
        "manifest": bundle_dir / "websearch_live_manifest.json",
    }
    output = tmp_path / "websearch_status.json"

    write_json_artifact(
        paths["fooddb"],
        {
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
    )
    write_json_artifact(paths["handoff"], inputs["manager_contract_handoff_artifact"])
    write_json_artifact(paths["probe"], inputs["contract_probe_artifact"])
    write_json_artifact(paths["repair"], inputs["repair_pack_artifact"])
    write_json_artifact(paths["live"], inputs["live_diagnostic_report"])
    write_json_artifact(paths["preflight"], inputs["preflight_artifact"])
    write_json_artifact(
        paths["manifest"],
        {
            "artifact_type": "accurate_intake_websearch_live_diagnostic_bundle_manifest",
            "artifacts": {
                "report": str(paths["live"]),
                "preflight": str(paths["preflight"]),
                "manager_contract_handoff": str(paths["handoff"]),
                "manager_contract_probe": str(paths["probe"]),
                "manager_contract_repair_pack": str(paths["repair"]),
            },
        },
    )

    assert (
        main(
            [
                "--fooddb-status-packet",
                str(paths["fooddb"]),
                "--live-bundle-manifest",
                str(paths["manifest"]),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["summary"]["manager_contract_gate_status"] == "clear_for_websearch_lane"
    assert artifact["next_required_slices"] == ["grokfast_websearch_packet_live_diagnostic"]


def test_websearch_candidate_lane_status_packet_rejects_unexpected_fooddb_artifact_type() -> None:
    try:
        build_websearch_candidate_lane_status_packet(
            fooddb_status_packet={"artifact_type": "wrong", "next_required_slices": []}
        )
    except ValueError as exc:
        assert "unsupported_websearch_status_fooddb_packet" in str(exc)
    else:
        raise AssertionError("unexpected FoodDB status packet type must fail")


def test_websearch_candidate_lane_status_packet_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_candidate_lane_status_packet.py"),
        Path("scripts/build_accurate_intake_websearch_candidate_lane_status_packet.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "Tavily",
        "requests.",
        "httpx.",
        "allow_live",
        "run_live",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
