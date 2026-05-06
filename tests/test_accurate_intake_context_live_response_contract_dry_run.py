from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import REQUIRED_CASE_IDS
from app.composition.accurate_intake_context_live_provider_input_preflight import (
    build_context_live_provider_input_preflight_artifact,
)
from app.composition.accurate_intake_context_live_response_contract_dry_run import (
    build_context_live_response_contract_dry_run_artifact,
)


def test_context_live_response_contract_dry_run_validates_fixture_manager_outputs_without_live_calls() -> None:
    artifact = build_context_live_response_contract_dry_run_artifact()

    assert artifact["artifact_type"] == "accurate_intake_context_live_response_contract_dry_run"
    assert artifact["status"] == "pass"
    assert artifact["diagnostic_only"] is True
    assert artifact["plan_only"] is True
    assert artifact["fixture_only"] is True
    assert artifact["provider_call_ready"] is False
    assert artifact["human_approval_required_before_live_provider"] is True
    assert artifact["semantic_owner"] == "fixture_manager_structured_decision_for_dry_run_only"
    assert artifact["deterministic_role"] == "validate_provider_response_contract_not_select_intent"
    assert artifact["deterministic_selected_intent"] is False
    assert artifact["raw_text_intent_router_used"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["live_provider_invoked"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["blockers"] == []
    assert artifact["summary"]["case_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["validated_response_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["blocked_response_count"] == 0
    assert artifact["summary"]["target_candidate_response_count"] >= 1
    assert artifact["summary"]["ambiguity_preserved_response_count"] >= 1
    assert artifact["summary"]["mutation_request_count"] == 0


def test_context_live_response_contract_dry_run_rejects_schema_extra_fields_and_mutation() -> None:
    artifact = build_context_live_response_contract_dry_run_artifact()
    responses = list(artifact["fixture_responses"])
    responses[0] = {
        **dict(responses[0]),
        "manager_intent": "food_log_candidate",
        "mutation_request": {
            "requested": True,
            "reason": "bad_live_probe_mutation",
            "unapproved_extra": "not allowed",
        },
        "unapproved_extra_field": "not allowed",
    }
    responses[3] = {
        **dict(responses[3]),
        "target_resolution": {
            **dict(responses[3]["target_resolution"]),
            "selected_target_id": "boba",
        },
    }

    blocked = build_context_live_response_contract_dry_run_artifact(fixture_responses=responses)

    case_id = str(responses[0]["case_id"])
    assert blocked["status"] == "blocked"
    assert f"{case_id}.manager_intent_mismatch" in blocked["blockers"]
    assert f"{case_id}.mutation_requested" in blocked["blockers"]
    assert f"{case_id}.mutation_request_extra_field:unapproved_extra" in blocked["blockers"]
    assert f"{case_id}.response_extra_field:unapproved_extra_field" in blocked["blockers"]
    assert "context_live_004_remove_previous_item.target_resolution_extra_field:selected_target_id" in blocked[
        "blockers"
    ]


def test_context_live_response_contract_dry_run_rejects_missing_target_or_ambiguity_contract() -> None:
    artifact = build_context_live_response_contract_dry_run_artifact()
    responses = list(artifact["fixture_responses"])
    target_case = next(
        index
        for index, row in enumerate(responses)
        if row["case_id"] == "context_live_004_remove_previous_item"
    )
    ambiguity_case = next(
        index
        for index, row in enumerate(responses)
        if row["case_id"] == "context_live_011_ambiguous_back_reference"
    )
    responses[target_case] = {
        **dict(responses[target_case]),
        "target_resolution": {"status": "not_applicable", "candidate_ids": []},
    }
    responses[ambiguity_case] = {
        **dict(responses[ambiguity_case]),
        "target_resolution": {"status": "candidates_available", "candidate_ids": ["rice"]},
    }

    blocked = build_context_live_response_contract_dry_run_artifact(fixture_responses=responses)

    assert blocked["status"] == "blocked"
    assert "context_live_004_remove_previous_item.target_candidates_not_available" in blocked["blockers"]
    assert "context_live_004_remove_previous_item.target_candidate_ids_missing" in blocked["blockers"]
    assert "context_live_011_ambiguous_back_reference.ambiguity_not_preserved" in blocked["blockers"]


def test_context_live_response_contract_dry_run_accepts_live_manager_resolved_target() -> None:
    artifact = build_context_live_response_contract_dry_run_artifact()
    responses = list(artifact["fixture_responses"])
    target_case = next(
        index
        for index, row in enumerate(responses)
        if row["case_id"] == "context_live_004_remove_previous_item"
    )
    responses[target_case] = {
        **dict(responses[target_case]),
        "target_resolution": {"status": "resolved", "candidate_ids": ["boba"]},
    }

    result = build_context_live_response_contract_dry_run_artifact(fixture_responses=responses)

    assert result["status"] == "pass"
    assert result["summary"]["target_candidate_response_count"] >= 1


def test_context_live_response_contract_dry_run_requires_clean_provider_input_preflight() -> None:
    preflight = build_context_live_provider_input_preflight_artifact()
    preflight["status"] = "blocked"
    preflight["provider_call_ready"] = True
    preflight["live_provider_invoked"] = True

    blocked = build_context_live_response_contract_dry_run_artifact(
        context_live_provider_input_preflight=preflight
    )

    assert blocked["status"] == "blocked"
    assert "provider_input_preflight.status_not_pass" in blocked["blockers"]
    assert "provider_input_preflight.provider_call_ready" in blocked["blockers"]
    assert "provider_input_preflight.live_provider_invoked" in blocked["blockers"]


def test_context_live_response_contract_dry_run_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_context_live_response_contract_dry_run import main

    output_path = tmp_path / "response-contract.json"

    assert main(["--output", str(output_path)]) == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["summary"]["validated_response_count"] == len(REQUIRED_CASE_IDS)


def test_context_live_response_contract_dry_run_is_wired_into_product_pages_ci() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "build_accurate_intake_context_live_provider_input_preflight.py" in workflow
    assert "build_accurate_intake_context_live_response_contract_dry_run.py" in workflow
    assert "accurate_intake_context_live_provider_input_preflight_ci.json" in workflow
    assert "accurate_intake_context_live_response_contract_dry_run_ci.json" in workflow


def test_context_live_response_contract_dry_run_source_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_context_live_response_contract_dry_run.py"),
        Path("scripts/build_accurate_intake_context_live_response_contract_dry_run.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "live_llm_invoked = True",
        "live_provider_invoked = True",
        "fooddb_used = True",
        "manager_context_packet_schema_changed = True",
    ]

    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source
