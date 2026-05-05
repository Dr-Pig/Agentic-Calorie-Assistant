from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_pre_live_self_use_decision_pack import (
    REQUIRED_PRE_LIVE_EVIDENCE,
    build_pre_live_self_use_decision_pack,
)


def _evidence(**overrides: dict) -> dict:
    evidence = {
        "phase_c_gate": {"status": "pass"},
        "accurate_intake_mvp_gate": {"status": "pass"},
        "browser_shell_smoke": {"status": "pass", "browser_executed": True},
        "chat_history_reload_gate": {"status": "pass"},
        "free_text_manual_target_gate": {"status": "pass"},
        "dogfood_review_queue": {"status": "generated"},
        "local_dogfood_data_hygiene": {"status": "pass"},
        "local_operator_data_hygiene_bundle": {
            "status": "local_operator_data_hygiene_ready",
            "writes_performed": False,
            "import_allowed": False,
            "production_db_used": False,
            "fooddb_truth_updated": False,
        },
        "pl_ce_local_review_decision_pack": {
            "status": "ready_for_human_pl_ce_review",
            "shared_contract_changed": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "real_fooddb_pass_claimed": False,
            "private_self_use_approved": False,
        },
        "context_live_diagnostic_case_matrix": {
            "status": "pass",
            "plan_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "live_provider_approved": False,
            "fooddb_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {
                "case_count": 11,
                "compound_cases": 1,
            },
        },
    }
    evidence.update(overrides)
    return evidence


def test_pre_live_decision_pack_lists_required_evidence_without_approving_live() -> None:
    pack = build_pre_live_self_use_decision_pack(_evidence())

    assert pack["artifact_type"] == "accurate_intake_pre_live_self_use_decision_pack"
    assert pack["status"] == "generated"
    assert pack["claim_scope"] == "pre_live_local_web_self_use_decision_pack"
    assert pack["required_evidence"] == list(REQUIRED_PRE_LIVE_EVIDENCE)
    assert pack["selected_option"] == "ready_for_human_limited_live_canary_decision"
    assert pack["missing_evidence"] == []
    assert pack["live_llm_invoked"] is False
    assert pack["live_canary_approved"] is False
    assert pack["kimi_active_runtime_default_allowed"] is False
    assert pack["product_readiness_claimed"] is False
    assert pack["runtime_web_activation_approved"] is False
    assert pack["blockers"] == []


def test_pre_live_decision_pack_stays_local_when_review_or_data_hygiene_evidence_missing() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            dogfood_review_queue={"status": "missing"},
            local_dogfood_data_hygiene={"status": "blocked"},
            local_operator_data_hygiene_bundle={},
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert pack["live_canary_approved"] is False
    assert pack["missing_evidence"] == [
        "dogfood_review_queue",
        "local_dogfood_data_hygiene",
        "local_operator_data_hygiene_bundle",
    ]


def test_pre_live_decision_pack_blocks_unsafe_operator_data_hygiene_flags() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            local_operator_data_hygiene_bundle={
                "status": "local_operator_data_hygiene_ready",
                "writes_performed": True,
                "import_allowed": True,
                "production_db_used": True,
                "fooddb_truth_updated": True,
            },
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "local_operator_data_hygiene_bundle_writes_performed" in pack["blockers"]
    assert "local_operator_data_hygiene_bundle_import_allowed" in pack["blockers"]
    assert "local_operator_data_hygiene_bundle_production_db_used" in pack["blockers"]
    assert "local_operator_data_hygiene_bundle_fooddb_truth_updated" in pack["blockers"]
    assert pack["live_canary_approved"] is False


def test_pre_live_decision_pack_requires_browser_executed_evidence_before_human_live_decision() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(browser_shell_smoke={"status": "blocked", "browser_executed": False})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "browser_shell_smoke" in pack["missing_evidence"]
    assert pack["evidence_status"]["browser_shell_smoke"]["browser_executed"] is False


def test_pre_live_decision_pack_requires_pl_ce_local_review_gate_before_human_live_decision() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(pl_ce_local_review_decision_pack={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "pl_ce_local_review_decision_pack" in pack["missing_evidence"]
    assert pack["ready_for_pl_ce_local_review"] is False
    assert pack["ready_for_live_diagnostic_decision"] is False


def test_pre_live_decision_pack_requires_context_live_case_matrix_before_human_live_decision() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(context_live_diagnostic_case_matrix={})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_diagnostic_case_matrix" in pack["missing_evidence"]
    assert pack["ready_for_live_diagnostic_decision"] is False


def test_pre_live_decision_pack_blocks_unsafe_context_live_case_matrix() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            context_live_diagnostic_case_matrix={
                "status": "pass",
                "plan_only": False,
                "live_provider_invoked": True,
                "live_provider_approved": True,
                "fooddb_used": True,
                "summary": {"case_count": 3, "compound_cases": 0},
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "context_live_diagnostic_case_matrix" in pack["missing_evidence"]
    assert "context_live_diagnostic_case_matrix_live_provider_invoked" in pack["blockers"]
    assert "context_live_diagnostic_case_matrix_live_provider_approved" in pack["blockers"]
    assert "context_live_diagnostic_case_matrix_fooddb_used" in pack["blockers"]
    assert "context_live_diagnostic_case_matrix_case_count_too_low" in pack["blockers"]
    assert "context_live_diagnostic_case_matrix_compound_case_missing" in pack["blockers"]


def test_pre_live_decision_pack_blocks_when_pl_ce_local_review_gate_is_blocked() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            pl_ce_local_review_decision_pack={
                "status": "blocked",
                "ready_for_live_diagnostic_decision": False,
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "pl_ce_local_review_decision_pack" in pack["missing_evidence"]
    assert pack["ready_for_pl_ce_local_review"] is False
    assert pack["live_canary_approved"] is False


def test_pre_live_decision_pack_blocks_pl_ce_local_review_overclaims() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(
            pl_ce_local_review_decision_pack={
                "status": "ready_for_human_pl_ce_review",
                "ready_for_live_diagnostic_decision": True,
                "ready_for_fdb_integration": True,
                "real_fooddb_pass_claimed": True,
                "private_self_use_approved": True,
            }
        )
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "pl_ce_local_review_decision_pack_ready_for_live_diagnostic_decision" in pack["blockers"]
    assert "pl_ce_local_review_decision_pack_ready_for_fdb_integration" in pack["blockers"]
    assert "pl_ce_local_review_decision_pack_real_fooddb_pass_claimed" in pack["blockers"]
    assert "pl_ce_local_review_decision_pack_private_self_use_approved" in pack["blockers"]
    assert pack["ready_for_pl_ce_local_review"] is False
    assert pack["ready_for_live_diagnostic_decision"] is False


def test_pre_live_decision_pack_blocks_shared_contract_changes() -> None:
    for flag in (
        "shared_contract_changed",
        "manager_context_packet_schema_changed",
        "nutrition_evidence_store_port_changed",
        "food_evidence_record_schema_changed",
        "packet_ready_anchor_schema_changed",
        "packetizer_format_changed",
        "basket_semantics_changed",
        "food_evidence_promotion_policy_changed",
    ):
        pack = build_pre_live_self_use_decision_pack(
            _evidence(pl_ce_local_review_decision_pack={
                "status": "ready_for_human_pl_ce_review",
                flag: True,
            })
        )

        assert pack["selected_option"] == "stay_local_self_use"
        assert f"pl_ce_local_review_decision_pack_{flag}" in pack["blockers"]
        assert pack["ready_for_pl_ce_local_review"] is False


def test_pre_live_decision_pack_does_not_accept_pl_ce_status_for_other_evidence() -> None:
    pack = build_pre_live_self_use_decision_pack(
        _evidence(phase_c_gate={"status": "ready_for_human_pl_ce_review"})
    )

    assert pack["selected_option"] == "stay_local_self_use"
    assert "phase_c_gate" in pack["missing_evidence"]
    assert pack["ready_for_pl_ce_local_review"] is True


def test_pre_live_decision_pack_script_writes_artifact(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "pre_live_pack.json"
    evidence_path.write_text(json.dumps(_evidence(), ensure_ascii=False), encoding="utf-8")

    from scripts.build_accurate_intake_pre_live_self_use_decision_pack import main

    exit_code = main(["--evidence-json", str(evidence_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["selected_option"] == "ready_for_human_limited_live_canary_decision"
    assert artifact["live_canary_approved"] is False
