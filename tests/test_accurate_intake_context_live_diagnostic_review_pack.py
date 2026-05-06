from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import REQUIRED_CASE_IDS
from app.composition.accurate_intake_context_live_diagnostic_review_pack import (
    REQUIRED_INPUTS,
    build_context_live_diagnostic_review_pack_artifact,
)


def _valid_inputs(*, live: bool = False) -> dict[str, dict[str, object]]:
    provider_count = len(REQUIRED_CASE_IDS)
    canary = (
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_canary",
            "status": "live_diagnostic_pass",
            "provider_mode": "live",
            "live_invoked": True,
            "live_llm_invoked": True,
            "live_provider_invoked": True,
            "provider_profile_model": "grok-4-fast",
            "semantic_owner": "live_manager_provider",
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "raw_text_intent_router_used": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "readiness_claimed": False,
            "response_contract_status": "pass",
            "blockers": [],
            "summary": {
                "provider_input_count": provider_count,
                "provider_output_count": provider_count,
                "validated_response_count": provider_count,
                "blocked_response_count": 0,
                "target_candidate_response_count": 4,
                "ambiguity_preserved_response_count": 3,
            },
        }
        if live
        else {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_canary",
            "status": "not_invoked",
            "provider_mode": "not_invoked",
            "live_invoked": False,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "provider_profile_model": "grok-4-fast",
            "semantic_owner": "not_invoked",
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "raw_text_intent_router_used": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "readiness_claimed": False,
            "response_contract_status": "not_available",
            "blockers": ["missing_provider_token"],
            "failure_family": "missing_provider_token",
            "summary": {
                "provider_input_count": provider_count,
                "provider_output_count": 0,
                "validated_response_count": 0,
                "blocked_response_count": 0,
                "target_candidate_response_count": 0,
                "ambiguity_preserved_response_count": 0,
            },
        }
    )
    return {
        "context_live_diagnostic_case_matrix": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_case_matrix",
            "status": "pass",
            "fixed_case_matrix_used": True,
            "case_ids": list(REQUIRED_CASE_IDS),
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {
                "case_count": provider_count,
                "target_candidate_cases": 4,
                "pending_pin_cases": 2,
                "ambiguity_cases": 3,
            },
            "blockers": [],
        },
        "context_live_diagnostic_anti_overfit_guard": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_anti_overfit_guard",
            "status": "pass",
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "summary": {
                "fixed_case_matrix_used": True,
                "distinct_intent_count": 8,
                "distinct_workflow_effect_count": 8,
                "holdout_utterance_variant_count": 22,
                "case_count": provider_count,
            },
            "blockers": [],
        },
        "context_live_provider_input_preflight": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_provider_input_preflight",
            "status": "pass",
            "provider_call_ready": False,
            "human_approval_required_before_live_provider": True,
            "fixed_case_matrix_used": True,
            "provider_inputs": [{"case_id": case_id} for case_id in REQUIRED_CASE_IDS],
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": [],
            "summary": {"provider_input_count": provider_count},
        },
        "context_live_response_contract_dry_run": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_response_contract_dry_run",
            "status": "pass",
            "diagnostic_only": True,
            "plan_only": True,
            "fixture_only": True,
            "provider_call_ready": False,
            "human_approval_required_before_live_provider": True,
            "full_matrix_required": True,
            "semantic_owner": "fixture_manager_structured_decision_for_dry_run_only",
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "raw_text_intent_router_used": False,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": [],
            "summary": {
                "case_count": provider_count,
                "validated_response_count": provider_count,
                "blocked_response_count": 0,
                "target_candidate_response_count": 4,
                "ambiguity_preserved_response_count": 3,
            },
        },
        "context_live_diagnostic_canary": canary,
    }


def test_live_review_pack_accepts_pre_live_not_invoked_canary_without_readiness_claims() -> None:
    artifact = build_context_live_diagnostic_review_pack_artifact(_valid_inputs(live=False))

    assert artifact["artifact_type"] == "accurate_intake_context_live_diagnostic_review_pack"
    assert artifact["status"] == "context_live_diagnostic_review_ready_without_live_canary"
    assert artifact["required_inputs"] == list(REQUIRED_INPUTS)
    assert artifact["blockers"] == []
    assert artifact["live_canary_status"] == "not_invoked"
    assert artifact["live_llm_invoked"] is False
    assert artifact["live_provider_invoked"] is False
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["summary"]["fixed_case_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["live_provider_output_count"] == 0


def test_live_review_pack_accepts_gate_disallowed_not_invoked_canary() -> None:
    inputs = _valid_inputs(live=False)
    inputs["context_live_diagnostic_canary"]["failure_family"] = "live_provider_not_allowed_by_gate"
    inputs["context_live_diagnostic_canary"]["blockers"] = ["live_provider_not_allowed_by_gate"]

    artifact = build_context_live_diagnostic_review_pack_artifact(inputs)

    assert artifact["status"] == "context_live_diagnostic_review_ready_without_live_canary"
    assert artifact["live_canary_status"] == "not_invoked"
    assert artifact["live_llm_invoked"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False


def test_live_review_pack_accepts_live_canary_as_diagnostic_evidence_only() -> None:
    artifact = build_context_live_diagnostic_review_pack_artifact(_valid_inputs(live=True))

    assert artifact["status"] == "context_live_diagnostic_review_ready_with_live_canary"
    assert artifact["live_canary_status"] == "live_diagnostic_pass"
    assert artifact["live_llm_invoked"] is True
    assert artifact["live_provider_invoked"] is True
    assert artifact["semantic_owner"] == "live_manager_provider"
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["summary"]["live_provider_output_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["live_blocked_response_count"] == 0


def test_live_review_pack_blocks_anti_overfit_or_dry_run_gaps() -> None:
    inputs = _valid_inputs(live=False)
    inputs["context_live_diagnostic_anti_overfit_guard"]["summary"]["distinct_intent_count"] = 1  # type: ignore[index]
    inputs["context_live_response_contract_dry_run"]["summary"]["blocked_response_count"] = 1  # type: ignore[index]

    artifact = build_context_live_diagnostic_review_pack_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_diagnostic_anti_overfit_guard.distinct_intent_count_too_low" in artifact["blockers"]
    assert "context_live_response_contract_dry_run.blocked_response_count_nonzero" in artifact["blockers"]


def test_live_review_pack_blocks_live_canary_overclaims_or_contract_failure() -> None:
    inputs = _valid_inputs(live=True)
    inputs["context_live_diagnostic_canary"]["status"] = "blocked"
    inputs["context_live_diagnostic_canary"]["blockers"] = ["context_live_001.manager_intent_mismatch"]
    inputs["context_live_diagnostic_canary"]["fooddb_used"] = True
    inputs["context_live_diagnostic_canary"]["product_readiness_claimed"] = True

    artifact = build_context_live_diagnostic_review_pack_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_diagnostic_canary.unexpected_status:blocked" in artifact["blockers"]
    assert "context_live_diagnostic_canary.upstream_blockers_present" in artifact["blockers"]
    assert "context_live_diagnostic_canary.fooddb_used" in artifact["blockers"]
    assert "context_live_diagnostic_canary.product_readiness_claimed" in artifact["blockers"]
    assert artifact["fooddb_used"] is False
    assert artifact["product_readiness_claimed"] is False


def test_live_review_pack_cli_writes_from_existing_artifacts(tmp_path: Path, capsys) -> None:
    from scripts.build_accurate_intake_context_live_diagnostic_review_pack import main

    output_path = tmp_path / "live-review-pack.json"
    args = ["--output", str(output_path)]
    for group_id, payload in _valid_inputs(live=True).items():
        artifact_path = tmp_path / f"{group_id}.json"
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        args.extend(["--artifact", f"{group_id}={artifact_path}"])

    exit_code = main(args)
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["status"] == "context_live_diagnostic_review_ready_with_live_canary"
    assert artifact["status"] == "context_live_diagnostic_review_ready_with_live_canary"


def test_live_review_pack_source_stays_out_of_fooddb_websearch_and_shared_schema() -> None:
    source_paths = (
        Path("app/composition/accurate_intake_context_live_diagnostic_review_pack.py"),
        Path("scripts/build_accurate_intake_context_live_diagnostic_review_pack.py"),
    )
    forbidden = (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "ManagerContextPacket",
        "TavilyClient",
        "selected_extract",
        "fooddb_used = True",
        "web_tavily_used = True",
        "product_readiness_claimed = True",
        "private_self_use_approved = True",
    )
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source
