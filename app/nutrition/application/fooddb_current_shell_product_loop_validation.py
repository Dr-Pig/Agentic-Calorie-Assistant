from __future__ import annotations

from typing import Any

from .approved_packet_ready_validation import validate_approved_packet_ready_items


def validate_current_shell_product_loop_fooddb_handoff(
    *,
    product_loop_handoff: dict[str, Any] | None,
    approved_packet_ready_artifact: dict[str, Any] | None,
    fooddb_manager_packet_smoke: dict[str, Any] | None,
) -> dict[str, Any]:
    if not product_loop_handoff and not approved_packet_ready_artifact:
        return {"status": "not_evaluated", "blockers": []}

    handoff = product_loop_handoff if isinstance(product_loop_handoff, dict) else {}
    approved = (
        approved_packet_ready_artifact
        if isinstance(approved_packet_ready_artifact, dict)
        else {}
    )
    packet_validation = validate_approved_packet_ready_items(approved)
    smoke_summary = _approved_manager_packet_smoke_summary(
        fooddb_manager_packet_smoke,
        expected_case_count=packet_validation["item_count"],
    )
    contract_validation = _object_dict(handoff.get("fooddb_contract_validation"))
    blockers: list[str] = []
    if handoff.get("status") != "product_loop_handoff_ready_for_fdb_integration_validation":
        blockers.append("product_loop_handoff_not_ready_for_validation")
    if handoff.get("ready_for_fdb_integration") is not True:
        blockers.append("product_loop_handoff_ready_flag_not_true")
    if handoff.get("fooddb_input_mode") != "approved_packet_ready_metadata_validation_only":
        blockers.append("product_loop_handoff_not_validation_only")
    if contract_validation.get("source") != "one_day_realistic_web_dogfood.evidence":
        blockers.append("product_loop_handoff_not_one_day_evidence_backed")
    for field, blocker in (
        ("packet_evidence_consumed", "product_loop_handoff_packet_evidence_not_consumed"),
        (
            "approved_fooddb_evidence_fixture_used",
            "product_loop_handoff_approved_evidence_not_consumed",
        ),
        ("macro_present_evidence_seen", "product_loop_handoff_macro_present_not_seen"),
        ("macro_missing_evidence_seen", "product_loop_handoff_macro_missing_not_seen"),
    ):
        if contract_validation.get(field) is not True:
            blockers.append(blocker)
    for field, blocker in (
        ("fooddb_truth_updated", "product_loop_handoff_fooddb_truth_updated"),
        ("non_approved_fooddb_inputs_consumed", "product_loop_handoff_non_approved_inputs"),
        ("real_fooddb_pass_claimed", "product_loop_handoff_real_fooddb_overclaim"),
        ("dogfood_pass", "product_loop_handoff_dogfood_overclaim"),
        ("product_readiness_claimed", "product_loop_handoff_product_overclaim"),
        ("private_self_use_approved", "product_loop_handoff_private_self_use_overclaim"),
        ("production_db_used", "product_loop_handoff_production_db_used"),
        ("live_llm_invoked", "product_loop_handoff_live_llm_invoked"),
        ("web_tavily_used", "product_loop_handoff_web_tavily_used"),
    ):
        if handoff.get(field) is True:
            blockers.append(blocker)
    if approved.get("status") != "approved_packet_ready_fooddb_artifact_ready":
        blockers.append("approved_packet_ready_artifact_not_ready")
    if approved.get("ready_for_other_tracks") is not True:
        blockers.append("approved_packet_ready_artifact_not_track_ready")
    if packet_validation["status"] != "approved_packet_ready_items_valid":
        blockers.extend(
            f"approved_packet_ready_items.{blocker}"
            for blocker in packet_validation["blockers"]
        )
    blockers.extend(smoke_summary["blockers"])
    return {
        "status": "validation_only_pass" if not blockers else "blocked",
        "claim_scope": "current_shell_product_loop_fooddb_validation_only",
        "source_handoff_status": handoff.get("status") or "missing",
        "fooddb_contract_validation_source": contract_validation.get("source") or "missing",
        "approved_packet_ready_items": packet_validation,
        "approved_manager_packet_smoke": smoke_summary,
        "next_allowed_fooddb_scope": "bounded_packet_contract_implementation_only"
        if not blockers
        else "blocked",
        "broad_fooddb_expansion_allowed": False,
        "runtime_truth_promotion_allowed": False,
        "live_or_websearch_probe_allowed": False,
        "fooddb_truth_updated": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "blockers": blockers,
    }


def _approved_manager_packet_smoke_summary(
    payload: dict[str, Any] | None,
    *,
    expected_case_count: int,
) -> dict[str, Any]:
    smoke = payload if isinstance(payload, dict) else {}
    summary = _object_dict(smoke.get("summary"))
    blockers: list[str] = []
    if smoke.get("artifact_type") != "accurate_intake_fooddb_manager_packet_smoke":
        blockers.append("fooddb_manager_packet_smoke_missing")
    if smoke.get("live_provider_used") is True:
        blockers.append("fooddb_manager_packet_smoke_live_provider_used")
    if smoke.get("runtime_truth_changed") is True:
        blockers.append("fooddb_manager_packet_smoke_runtime_truth_changed")
    if smoke.get("product_loop_integration_claimed") is True:
        blockers.append("fooddb_manager_packet_smoke_product_loop_overclaim")
    if summary.get("approved_packet_ready_case_count") != expected_case_count:
        blockers.append("fooddb_manager_packet_smoke_approved_case_count_mismatch")
    for field, blocker in (
        ("raw_source_rows_included", "fooddb_manager_packet_smoke_raw_rows_included"),
        ("candidate_only_records_included", "fooddb_manager_packet_smoke_candidate_records"),
        ("full_fooddb_included", "fooddb_manager_packet_smoke_full_fooddb_included"),
    ):
        if summary.get(field) is True:
            blockers.append(blocker)
    return {
        "approved_packet_ready_case_count": summary.get("approved_packet_ready_case_count", 0),
        "approved_packet_ready_lane_counts": _object_dict(
            summary.get("approved_packet_ready_lane_counts")
        ),
        "raw_source_rows_included": summary.get("raw_source_rows_included") is True,
        "candidate_only_records_included": summary.get("candidate_only_records_included") is True,
        "full_fooddb_included": summary.get("full_fooddb_included") is True,
        "blockers": blockers,
    }


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


__all__ = ["validate_current_shell_product_loop_fooddb_handoff"]
