from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_pl_ce_local_review_decision_pack import (
    REQUIRED_PL_CE_LOCAL_REVIEW_EVIDENCE,
    build_pl_ce_local_review_decision_pack,
)


def _evidence(**overrides: dict) -> dict:
    evidence = {
        "browser_shell_smoke": {
            "artifact_type": "accurate_intake_browser_shell_smoke",
            "status": "pass",
            "browser_executed": True,
            "live_llm_invoked": False,
            "web_tavily_used": False,
        },
        "browser_fixture_dogfood": {
            "artifact_type": "accurate_intake_browser_one_day_fixture_dogfood",
            "status": "browser_fixture_pass",
            "fixture_evidence_used": True,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
        },
        "browser_realistic_dogfood": {
            "artifact_type": "accurate_intake_browser_realistic_web_dogfood_v2",
            "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
            "fixture_evidence_used": True,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
        },
        "pl_ce_review_bundle": {
            "artifact_type": "accurate_intake_product_loop_review_bundle_v1",
            "status": "product_loop_context_diagnostic_ready_for_human_review",
            "ready_for_fdb_integration": False,
            "real_fooddb_pass_claimed": False,
        },
        "context_review": {
            "artifact_type": "accurate_intake_context_review_artifact",
            "status": "generated",
            "context_engineering_fault_claimed": False,
        },
        "context_target_candidate_eval": {
            "artifact_type": "accurate_intake_context_target_candidate_eval",
            "status": "generated",
            "deterministic_selected_target": False,
        },
        "context_window_diagnostic": {
            "artifact_type": "accurate_intake_context_window_diagnostic",
            "status": "generated",
            "long_term_memory_used": False,
            "proactive_or_rescue_used": False,
        },
        "local_operator_data_hygiene_bundle": {
            "artifact_type": "accurate_intake_local_operator_data_hygiene_bundle",
            "status": "local_operator_data_hygiene_ready",
            "local_only": True,
            "contains_personal_diet_logs": True,
            "do_not_commit": True,
            "writes_performed": False,
            "import_allowed": False,
            "production_db_used": False,
            "fooddb_truth_updated": False,
        },
        "mvp_gate": {"status": "pass"},
    }
    evidence.update(overrides)
    return evidence


def test_pl_ce_local_review_pack_prepares_human_review_without_live_or_fooddb_claims() -> None:
    pack = build_pl_ce_local_review_decision_pack(_evidence())

    assert pack["artifact_type"] == "accurate_intake_pl_ce_local_review_decision_pack"
    assert pack["status"] == "ready_for_human_pl_ce_review"
    assert pack["required_evidence"] == list(REQUIRED_PL_CE_LOCAL_REVIEW_EVIDENCE)
    assert pack["ready_for_live_diagnostic_decision"] is False
    assert pack["ready_for_fdb_integration"] is False
    assert pack["live_llm_invoked"] is False
    assert pack["web_tavily_used"] is False
    assert pack["real_fooddb_pass_claimed"] is False
    assert pack["private_self_use_approved"] is False
    assert pack["product_readiness_claimed"] is False
    assert pack["review_required_before_provider_call"] is True
    assert pack["missing_evidence"] == []
    assert pack["blockers"] == []


def test_pl_ce_local_review_pack_blocks_overclaim_and_missing_context_or_hygiene_bundle() -> None:
    pack = build_pl_ce_local_review_decision_pack(
        _evidence(
            browser_realistic_dogfood={
                "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
                "real_fooddb_pass_claimed": True,
            },
            pl_ce_review_bundle={"status": "missing"},
            local_operator_data_hygiene_bundle={},
        )
    )

    assert pack["status"] == "blocked"
    assert "pl_ce_review_bundle" in pack["missing_evidence"]
    assert "local_operator_data_hygiene_bundle" in pack["missing_evidence"]
    assert "browser_realistic_dogfood_real_fooddb_overclaim" in pack["blockers"]
    assert pack["ready_for_live_diagnostic_decision"] is False


def test_pl_ce_local_review_pack_blocks_unsafe_local_operator_hygiene_flags() -> None:
    pack = build_pl_ce_local_review_decision_pack(
        _evidence(
            local_operator_data_hygiene_bundle={
                "artifact_type": "accurate_intake_local_operator_data_hygiene_bundle",
                "status": "local_operator_data_hygiene_ready",
                "writes_performed": True,
                "import_allowed": True,
                "production_db_used": True,
                "fooddb_truth_updated": True,
            }
        )
    )

    assert pack["status"] == "blocked"
    assert "local_operator_data_hygiene_bundle_writes_performed" in pack["blockers"]
    assert "local_operator_data_hygiene_bundle_import_allowed" in pack["blockers"]
    assert "local_operator_data_hygiene_bundle_production_db_used" in pack["blockers"]
    assert "local_operator_data_hygiene_bundle_fooddb_truth_updated" in pack["blockers"]
    assert pack["ready_for_live_diagnostic_decision"] is False


def test_pl_ce_local_review_pack_script_writes_artifact(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "pl_ce_pack.json"
    evidence_path.write_text(json.dumps(_evidence(), ensure_ascii=False), encoding="utf-8")

    from scripts.build_accurate_intake_pl_ce_local_review_decision_pack import main

    exit_code = main(["--evidence-json", str(evidence_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "ready_for_human_pl_ce_review"
    assert artifact["ready_for_live_diagnostic_decision"] is False
