from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_macro_contract import MACRO_CONTRACT
from scripts.build_accurate_intake_product_loop_handoff_v3 import (
    build_product_loop_handoff_v3,
)


def _product_loop_evidence(**overrides: dict) -> dict:
    evidence = {
        "browser_shell_smoke": {"status": "pass", "browser_executed": True},
        "local_web_candidate": _local_web_candidate(),
        "browser_fixture_dogfood": {
            "status": "browser_fixture_pass",
            "fixture_evidence_used": True,
            "real_fooddb_pass_claimed": False,
        },
        "local_dogfood_hygiene": {"status": "pass"},
        "browser_realistic_dogfood": {
            "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
            "fixture_evidence_used": True,
            "real_fooddb_pass_claimed": False,
        },
        "operator_review": {
            "artifact_type": "accurate_intake_dogfood_operator_review_surface",
            "status": "browser_diagnostic_review_with_fixture_evidence_gap",
            "claim_scope": "local_dogfood_operator_review_surface",
            "local_only": True,
            "do_not_commit": True,
            "food_kb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "classification_policy": {
                "food_kb_truth_update_allowed": False,
                "frontend_semantic_owner": False,
            },
        },
        "mvp_gate": {"status": "pass"},
    }
    evidence.update(overrides)
    return evidence


def _local_web_candidate(**chain_overrides: object) -> dict:
    chain = {
        "browser_artifact_count": 7,
        "browser_executed_count": 7,
        "all_required_browser_artifacts_executed": True,
        "product_pages_self_use_flow_checked": True,
        "today_macro_runtime_mirror_checked": True,
        "renderer_source_closure_checked": True,
        "context_target_browser_closure_checked": True,
        "body_noplan_degraded_checked": True,
        "body_observation_same_truth_checked": True,
        "live_llm_invoked": False,
        "fooddb_evidence_used": False,
        "websearch_evidence_used": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "frontend_semantic_owner": False,
    }
    chain.update(chain_overrides)
    return {
        "local_web_self_use_candidate_v2": {
            "candidate_prepared": True,
            "blockers": [],
            "appshell_browser_evidence_chain": chain,
        }
    }


def _fooddb_artifact(
    *,
    fixture_or_real: str = "real",
    source_quality: str = "approved",
    ready_for_product_loop: bool = True,
    macro_contract: dict | None = None,
) -> dict:
    if macro_contract is None:
        macro_contract = MACRO_CONTRACT
    return {
        "approved_packet_ready_evidence_artifact": {
            "path": "artifacts/fdb/approved_packet_ready.json",
            "schema_version": "food_evidence_v1",
            "fixture_or_real": fixture_or_real,
            "source_quality": source_quality,
            "ready_for_product_loop": ready_for_product_loop,
            "macro_contract": macro_contract,
        }
    }


def test_handoff_missing_fooddb_artifact_waits_without_claiming_real_pass() -> None:
    pack = build_product_loop_handoff_v3(_product_loop_evidence())

    assert pack["artifact_type"] == "accurate_intake_product_loop_handoff_v3"
    assert pack["status"] == "product_loop_handoff_waiting_for_fdb_artifact"
    assert pack["fooddb_artifact_status"] == "blocked_waiting_for_fdb_artifact"
    assert pack["ready_for_fdb_integration"] is False
    assert pack["real_fooddb_pass_claimed"] is False
    assert pack["dogfood_pass"] is False
    assert pack["product_readiness_claimed"] is False
    assert pack["shared_contract_changed"] is False
    assert pack["product_loop_evidence_status"]["local_web_candidate"]["status"] == (
        "candidate_prepared"
    )
    assert pack["appshell_browser_evidence_chain"]["browser_artifact_count"] == 7
    assert pack["appshell_browser_evidence_chain"]["all_required_browser_artifacts_executed"] is True
    assert pack["appshell_browser_evidence_chain"]["live_llm_invoked"] is False
    assert pack["appshell_browser_evidence_chain"]["fooddb_evidence_used"] is False
    assert pack["appshell_browser_evidence_chain"]["websearch_evidence_used"] is False


def test_handoff_blocks_missing_or_stale_local_web_candidate() -> None:
    missing = build_product_loop_handoff_v3(
        _product_loop_evidence(local_web_candidate={})
    )
    assert missing["status"] == "blocked"
    assert "missing_product_loop_evidence:local_web_candidate" in missing["blockers"]

    stale = build_product_loop_handoff_v3(
        _product_loop_evidence(
            local_web_candidate=_local_web_candidate(
                browser_executed_count=5,
                context_target_browser_closure_checked=False,
            )
        )
    )
    assert stale["status"] == "blocked"
    assert "local_web_candidate_browser_artifact_count_mismatch" in stale["blockers"]
    assert "local_web_candidate_context_target_browser_closure_missing" in stale["blockers"]


def test_handoff_blocks_local_web_candidate_live_or_fooddb_overclaims() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(
            local_web_candidate=_local_web_candidate(
                live_llm_invoked=True,
                fooddb_evidence_used=True,
                websearch_evidence_used=True,
                frontend_semantic_owner=True,
            )
        )
    )

    assert pack["status"] == "blocked"
    assert "local_web_candidate_live_llm_invoked" in pack["blockers"]
    assert "local_web_candidate_fooddb_evidence_used" in pack["blockers"]
    assert "local_web_candidate_websearch_evidence_used" in pack["blockers"]
    assert "local_web_candidate_frontend_semantic_owner" in pack["blockers"]


def test_handoff_fixture_fooddb_artifact_still_does_not_claim_real_fooddb_pass() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact=_fooddb_artifact(fixture_or_real="fixture"),
    )

    assert pack["status"] == "product_loop_handoff_waiting_for_fdb_artifact"
    assert pack["fooddb_artifact_status"] == "fixture_not_real_fooddb"
    assert pack["ready_for_fdb_integration"] is False
    assert pack["real_fooddb_pass_claimed"] is False
    assert pack["fooddb_evidence_used"] is False


def test_handoff_invalid_fooddb_metadata_blocks_without_autofix() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact={"approved_packet_ready_evidence_artifact": {"fixture_or_real": "real"}},
    )

    assert pack["status"] == "blocked"
    assert pack["fooddb_artifact_status"] == "blocked_invalid_fooddb_metadata"
    assert pack["ready_for_fdb_integration"] is False
    assert pack["autofix_attempted"] is False
    assert any(item.startswith("fooddb_metadata_missing:") for item in pack["blockers"])


def test_handoff_blocks_real_fooddb_artifact_without_macro_contract() -> None:
    artifact = _fooddb_artifact()
    del artifact["approved_packet_ready_evidence_artifact"]["macro_contract"]

    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact=artifact,
    )

    assert pack["status"] == "blocked"
    assert pack["fooddb_artifact_status"] == "blocked_invalid_fooddb_macro_contract"
    assert pack["ready_for_fdb_integration"] is False
    assert "fooddb_macro_contract_missing" in pack["blockers"]
    assert pack["autofix_attempted"] is False
    assert pack["fooddb_truth_updated"] is False


def test_handoff_blocks_fooddb_macro_contract_missing_required_packet_fields() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact=_fooddb_artifact(
            macro_contract={
                "packet_fields": [
                    "protein_g",
                    "carbs_g",
                    "fat_g",
                    "macro_visibility_status",
                ],
                "macro_truth_owner": "fooddb_approved_packet",
                "missing_macro_policy": "preserve_null_do_not_invent",
            }
        ),
    )

    assert pack["status"] == "blocked"
    assert pack["fooddb_artifact_status"] == "blocked_invalid_fooddb_macro_contract"
    assert "fooddb_macro_packet_field_missing:macro_source_basis" in pack["blockers"]
    assert "fooddb_macro_packet_field_missing:macro_confidence" in pack["blockers"]


def test_handoff_blocks_stale_fooddb_macro_contract_without_source_class_policy() -> None:
    stale_macro_contract = {
        "packet_fields": [
            "protein_g",
            "carbs_g",
            "fat_g",
            "macro_visibility_status",
            "macro_source_basis",
            "macro_confidence",
        ],
        "macro_truth_owner": "fooddb_approved_packet",
        "missing_macro_policy": "preserve_null_do_not_invent",
    }

    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact=_fooddb_artifact(macro_contract=stale_macro_contract),
    )

    assert pack["status"] == "blocked"
    assert pack["fooddb_artifact_status"] == "blocked_invalid_fooddb_macro_contract"
    assert "fooddb_macro_runtime_policy_missing" in pack["blockers"]
    assert "fooddb_macro_source_class_policy_missing" in pack["blockers"]


def test_handoff_blocks_fooddb_macro_contract_without_shadow_schema() -> None:
    stale_macro_contract = dict(MACRO_CONTRACT)
    stale_macro_contract.pop("shadow_schema")

    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact=_fooddb_artifact(macro_contract=stale_macro_contract),
    )

    assert pack["status"] == "blocked"
    assert pack["fooddb_artifact_status"] == "blocked_invalid_fooddb_macro_contract"
    assert "fooddb_macro_shadow_schema_missing" in pack["blockers"]


def test_handoff_blocks_fooddb_macro_shadow_schema_missing_generic_range() -> None:
    stale_macro_contract = json.loads(json.dumps(MACRO_CONTRACT))
    stale_macro_contract["shadow_schema"]["generic_common_serving"]["macro_fields"].remove(
        "protein_g_range"
    )

    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact=_fooddb_artifact(macro_contract=stale_macro_contract),
    )

    assert pack["status"] == "blocked"
    assert pack["fooddb_artifact_status"] == "blocked_invalid_fooddb_macro_contract"
    assert "fooddb_macro_shadow_schema_generic_missing:protein_g_range" in pack["blockers"]


def test_handoff_valid_real_fooddb_metadata_allows_validation_only_integration() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact=_fooddb_artifact(),
    )

    assert pack["status"] == "product_loop_handoff_ready_for_fdb_integration_validation"
    assert pack["fooddb_artifact_status"] == "approved_packet_ready_evidence_metadata_valid"
    assert pack["ready_for_fdb_integration"] is True
    assert pack["fooddb_input_mode"] == "approved_packet_ready_metadata_validation_only"
    assert pack["fooddb_validation"]["metadata"]["macro_contract"]["macro_truth_owner"] == (
        "fooddb_approved_packet"
    )
    assert pack["real_fooddb_pass_claimed"] is False
    assert pack["dogfood_pass"] is False


def test_handoff_blocks_product_loop_overclaims_before_fooddb_validation() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(
            browser_realistic_dogfood={
                "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
                "fixture_evidence_used": True,
                "real_fooddb_pass_claimed": True,
            }
        ),
        fooddb_artifact=_fooddb_artifact(),
    )

    assert pack["status"] == "blocked"
    assert "browser_realistic_dogfood_real_fooddb_overclaim" in pack["blockers"]
    assert pack["ready_for_fdb_integration"] is False


def test_handoff_blocks_non_operator_review_artifact_shape() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(
            operator_review={
                "artifact_type": "accurate_intake_current_shell_compatibility_local_review_decision_pack",
                "status": "browser_diagnostic_review_with_fixture_evidence_gap",
                "claim_scope": "local_dogfood_operator_review_surface",
                "local_only": True,
                "do_not_commit": True,
                "food_kb_truth_updated": False,
                "real_fooddb_pass_claimed": False,
                "dogfood_pass": False,
                "product_readiness_claimed": False,
                "private_self_use_approved": False,
                "classification_policy": {
                    "food_kb_truth_update_allowed": False,
                    "frontend_semantic_owner": False,
                },
            }
        ),
        fooddb_artifact=_fooddb_artifact(),
    )

    assert pack["status"] == "blocked"
    assert "operator_review_invalid_artifact_type" in pack["blockers"]
    assert pack["ready_for_fdb_integration"] is False


def test_handoff_blocks_operator_review_missing_local_review_boundary_fields() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(
            operator_review={
                "artifact_type": "accurate_intake_dogfood_operator_review_surface",
                "status": "browser_diagnostic_review_with_fixture_evidence_gap",
                "local_only": True,
                "food_kb_truth_updated": False,
                "real_fooddb_pass_claimed": False,
                "dogfood_pass": False,
                "product_readiness_claimed": False,
                "private_self_use_approved": False,
            }
        ),
        fooddb_artifact=_fooddb_artifact(),
    )

    assert pack["status"] == "blocked"
    assert "operator_review_claim_scope_invalid" in pack["blockers"]
    assert "operator_review_missing_do_not_commit" in pack["blockers"]
    assert "operator_review_food_kb_truth_update_allowed" in pack["blockers"]
    assert "operator_review_frontend_semantic_owner" in pack["blockers"]
    assert pack["ready_for_fdb_integration"] is False


def test_handoff_blocks_operator_review_readiness_overclaims() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(
            operator_review={
                "artifact_type": "accurate_intake_dogfood_operator_review_surface",
                "status": "browser_diagnostic_review_with_fixture_evidence_gap",
                "claim_scope": "local_dogfood_operator_review_surface",
                "local_only": False,
                "do_not_commit": True,
                "food_kb_truth_updated": True,
                "fooddb_truth_updated": True,
                "real_fooddb_pass_claimed": True,
                "dogfood_pass": True,
                "product_readiness_claimed": True,
                "private_self_use_approved": True,
                "production_readiness_claimed": True,
                "production_selected": True,
                "production_db_used": True,
                "live_llm_invoked": True,
                "web_tavily_used": True,
                "classification_policy": {
                    "food_kb_truth_update_allowed": True,
                    "frontend_semantic_owner": True,
                },
            }
        ),
        fooddb_artifact=_fooddb_artifact(),
    )

    assert pack["status"] == "blocked"
    assert "operator_review_not_local_only" in pack["blockers"]
    assert "operator_review_food_kb_truth_updated" in pack["blockers"]
    assert "operator_review_fooddb_truth_updated" in pack["blockers"]
    assert "operator_review_real_fooddb_overclaim" in pack["blockers"]
    assert "operator_review_dogfood_pass_overclaim" in pack["blockers"]
    assert "operator_review_product_readiness_overclaim" in pack["blockers"]
    assert "operator_review_private_self_use_overclaim" in pack["blockers"]
    assert "operator_review_production_readiness_overclaim" in pack["blockers"]
    assert "operator_review_production_selected" in pack["blockers"]
    assert "operator_review_production_db_used" in pack["blockers"]
    assert "operator_review_live_llm_invoked" in pack["blockers"]
    assert "operator_review_web_tavily_used" in pack["blockers"]
    assert "operator_review_food_kb_truth_update_allowed" in pack["blockers"]
    assert "operator_review_frontend_semantic_owner" in pack["blockers"]
    assert pack["ready_for_fdb_integration"] is False


def test_handoff_script_never_reads_unapproved_fooddb_inputs_as_truth() -> None:
    source = Path("scripts/build_accurate_intake_product_loop_handoff_v3.py").read_text(
        encoding="utf-8"
    )

    assert "approved_packet_ready_metadata_validation_only" in source
    for fragment in (
        "raw_source",
        "staging_candidates",
        "validator_only_candidates",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "NutritionEvidenceStorePort",
        "packetizer",
    ):
        assert fragment not in source


def test_handoff_cli_writes_waiting_artifact(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "handoff.json"
    evidence_path.write_text(
        json.dumps(_product_loop_evidence(), ensure_ascii=False),
        encoding="utf-8",
    )

    from scripts.build_accurate_intake_product_loop_handoff_v3 import main

    exit_code = main(["--evidence-json", str(evidence_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "product_loop_handoff_waiting_for_fdb_artifact"
    assert artifact["fooddb_artifact_status"] == "blocked_waiting_for_fdb_artifact"


def test_handoff_runbook_documents_validation_only_gate() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md").read_text(
        encoding="utf-8-sig"
    )

    assert "build_accurate_intake_product_loop_handoff_v3.py" in runbook
    assert "--local-web-candidate artifacts/accurate_intake_local_web_self_use_candidate_v2.json" in runbook
    assert "ready_for_fdb_integration=false" in runbook
    assert "blocked_waiting_for_fdb_artifact" in runbook
    assert "Invalid FoodDB metadata blocks the gate" in runbook


def test_fooddb_handoff_docs_require_macro_packet_contract() -> None:
    activation_plan = Path(
        "docs/quality/ACCURATE_INTAKE_FOODDB_WEBSEARCH_LLM_ACTIVATION_PLAN.md"
    ).read_text(encoding="utf-8-sig")
    track_status = Path(
        "docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md"
    ).read_text(encoding="utf-8-sig")

    for text in (activation_plan, track_status):
        assert "macro_contract" in text
        assert "macro_visibility_status" in text
        assert "macro_source_basis" in text
        assert "missing_macro_policy" in text
        assert "shadow_schema" in text
