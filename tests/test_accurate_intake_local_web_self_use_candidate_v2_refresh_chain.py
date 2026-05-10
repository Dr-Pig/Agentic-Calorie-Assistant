from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_accurate_intake_local_web_self_use_candidate_v2_gate_runner import (
    _required_payloads,
)
from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS,
)
from tests.test_current_shell_compatibility_browser_activation_evidence_gate import (
    _valid_inputs as _valid_browser_gate_inputs,
)
from tests.test_current_shell_compatibility_product_pages_self_use_flow_gate import (
    _valid_inputs as _valid_product_pages_flow_inputs,
)


def _clone(payload: dict[str, object]) -> dict[str, object]:
    return json.loads(json.dumps(payload, ensure_ascii=False))


def _browser_fixture_dogfood_payload() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_browser_one_day_fixture_dogfood",
        "status": "browser_fixture_pass",
        "fixture_evidence_used": True,
        "fixture_fooddb_evidence_used": True,
        "fooddb_evidence_used": False,
        "fooddb_evidence_used_normalized_for_local_review": True,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "product_readiness_claimed": False,
        "manager_dogfood_summary": {
            "macro_present_evidence_seen": True,
            "macro_missing_evidence_seen": True,
        },
    }


def _browser_realistic_dogfood_payload() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_browser_realistic_web_dogfood_v2",
        "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
        "fixture_evidence_used": True,
        "real_fooddb_pass_claimed": False,
    }


def _one_day_realistic_dogfood_payload() -> dict[str, object]:
    return {
        "one_day_realistic_web_dogfood": {
            "status": "pass",
            "browser_executed": False,
            "live_provider_called": False,
            "kimi_activated": False,
            "production_db_touched": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": [],
            "turns": [
                {"turn_id": "target_001"},
                {"turn_id": "breakfast_001"},
                {"turn_id": "lunch_001"},
                {"turn_id": "tea_001"},
                {"turn_id": "dinner_draft_001"},
                {"turn_id": "dinner_basket_001"},
                {"turn_id": "dinner_remove_001"},
                {"turn_id": "query_001"},
            ],
            "evidence": {
                "approved_fooddb_evidence_fixture_used": True,
                "fooddb_evidence_used": True,
                "macro_present_evidence_seen": True,
                "macro_missing_evidence_seen": True,
                "food_evidence_gap_observed": False,
                "evidence_gap_observed": False,
                "same_truth_verified": "not_checked",
                "dogfood_review_queue_compatible": "not_checked",
                "local_data_hygiene_respected": "not_checked",
            },
        }
    }


@pytest.fixture(autouse=True)
def _fast_expensive_refresh_chain_generators(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module
    from tests.test_accurate_intake_session_context_carryover_qa_bundle import (
        _valid_inputs as _valid_session_context_inputs,
    )
    from tests.test_accurate_intake_context_quality_pack import (
        _short_term_context_smoke,
    )
    from app.composition.accurate_intake_session_context_carryover_qa_bundle import (
        build_session_context_carryover_qa_bundle_artifact,
    )
    from scripts.build_accurate_intake_context_quality_pack import (
        build_context_quality_pack_report,
    )

    gate_payloads = _required_payloads()
    product_page_payloads = _valid_product_pages_flow_inputs()
    browser_gate_payloads = _valid_browser_gate_inputs()
    session_context_payloads = _valid_session_context_inputs()
    mvp_gate_summary = _clone(gate_payloads["accurate_intake_mvp_gate"])
    mvp_gate_summary["groups"] = [
        {"group_id": "ledger_truth_and_read_model", "status": "pass"}
    ]
    session_context_bundle = build_session_context_carryover_qa_bundle_artifact(
        session_context_payloads
    )
    context_quality_pack = build_context_quality_pack_report(
        short_term_context_smoke=_short_term_context_smoke(),
        require_runtime_trace_input=True,
    )
    short_term_context = _clone(product_page_payloads["product_pages_short_term_context_smoke"])
    short_term_context.update(browser_gate_payloads["product_pages_short_term_context_smoke"])
    short_term_context.update(
        {
            "browser_execution_required": True,
            "chat_context_status_ui_rendered": True,
            "today_no_meal_before_followup_answer": True,
            "today_consumed_zero_before_followup_answer": True,
            "fake_provider_calls": [
                {
                    "stage": "entry",
                    "context_policy_version_present": True,
                    "loaded_context_summary_present": True,
                    "omitted_context_summary_present": True,
                    "pending_followup_pin_present": False,
                    "raw_user_input_used_for_fixture_selection": False,
                },
                {
                    "stage": "execution_after_followup",
                    "context_policy_version_present": True,
                    "loaded_context_summary_present": True,
                    "omitted_context_summary_present": True,
                    "pending_followup_pin_present": True,
                    "raw_user_input_used_for_fixture_selection": False,
                },
            ],
        }
    )
    fast_payloads = {
        "_generate_accurate_intake_mvp_gate_summary": mvp_gate_summary,
        "_generate_product_pages_browser_smoke": {
            **product_page_payloads["product_pages_browser_smoke"],
            **browser_gate_payloads["product_pages_browser_smoke"],
            "browser_execution_required": True,
        },
        "_generate_product_pages_seven_day_diary_smoke": {
            **product_page_payloads["product_pages_seven_day_diary_smoke"],
            **browser_gate_payloads["product_pages_seven_day_diary_smoke"],
            "browser_execution_required": True,
        },
        "_generate_product_pages_body_noplan_degraded_smoke": {
            **product_page_payloads["product_pages_body_noplan_degraded_smoke"],
            **browser_gate_payloads["product_pages_body_noplan_degraded_smoke"],
            "browser_execution_required": True,
            "manager_provider_call_count": 0,
        },
        "_generate_product_pages_short_term_context_smoke": short_term_context,
        "_generate_product_pages_target_candidate_ui_smoke": {
            **product_page_payloads["product_pages_target_candidate_ui_smoke"],
            **browser_gate_payloads["product_pages_target_candidate_ui_smoke"],
            "browser_execution_required": True,
        },
        "_generate_product_pages_visual_qa": {
            **product_page_payloads["product_pages_visual_qa"],
            **browser_gate_payloads["product_pages_visual_qa"],
            "browser_execution_required": True,
        },
        "_generate_fixture_full_product_loop_e2e": {
            **product_page_payloads["fixture_full_product_loop_e2e"],
            **browser_gate_payloads["fixture_full_product_loop_e2e"],
            "diagnostic_only": True,
            "local_only": True,
        },
        "build_context_quality_pack_report": {
            **context_quality_pack,
            "ready_for_live_diagnostic_decision": False,
        },
        "build_pl_ce_context_coverage_matrix_artifact": session_context_payloads[
            "context_coverage_matrix"
        ],
        "build_session_context_carryover_qa_bundle_artifact": session_context_bundle,
        "build_browser_one_day_fixture_dogfood_report": _browser_fixture_dogfood_payload(),
        "build_browser_realistic_web_dogfood_v2_report": _browser_realistic_dogfood_payload(),
        "build_one_day_realistic_web_dogfood_report": _one_day_realistic_dogfood_payload(),
    }
    for name, payload in fast_payloads.items():
        monkeypatch.setattr(
            module,
            name,
            lambda *args, _payload=payload, **kwargs: _clone(_payload),
        )


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _assert_refresh_chain_closeout_pass(exit_code: int, printed: dict[str, object]) -> None:
    assert exit_code == 0
    assert printed["status"] == "pass"
    closeout = printed["closeout_navigation"]
    assert closeout["first_blocking_gate"] is None
    assert closeout["non_claims"] == {
        "product_ready": False,
        "web_ready": False,
        "private_self_use_approved": False,
        "production_ready": False,
        "live_llm_ready": False,
        "fooddb_truth_promoted": False,
    }
    assert printed["private_self_use_approved"] is False
    assert printed["product_readiness_claimed"] is False
    assert printed["real_fooddb_pass_claimed"] is False
    assert printed["live_llm_invoked"] is False
    assert printed["web_tavily_used"] is False
    assert printed["fooddb_evidence_used"] is False


def _merge_write(path: Path, payload: dict[str, object]) -> None:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(existing, dict):
            merged = dict(existing)
            merged.update(payload)
            _write(path, merged)
            return
    _write(path, payload)


def _seed_required_gate_inputs(
    artifact_dir: Path,
    *,
    omit_browser_target_ui: bool = False,
    omit_fixture_full_product_loop_e2e: bool = False,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    gate_payloads = _required_payloads()
    browser_gate_inputs = _valid_browser_gate_inputs()
    product_pages_flow_inputs = _valid_product_pages_flow_inputs()

    skipped_gate_groups = {
        "manager_tool_surface_inventory",
        "manager_tool_choice_regression_wall",
        "non_fooddb_read_only_tool_loop_fake_smoke",
        "non_fooddb_mutation_tool_guard_smoke",
        "browser_activation_evidence_gate",
    }
    for group_id, payload in gate_payloads.items():
        if group_id in skipped_gate_groups:
            continue
        target_path = artifact_dir / module.DEFAULT_EVIDENCE_PATHS[group_id].name
        _write(target_path, payload)

    for group_id, payload in product_pages_flow_inputs.items():
        if group_id == "product_pages_target_candidate_ui_smoke" and omit_browser_target_ui:
            continue
        if group_id == "fixture_full_product_loop_e2e" and omit_fixture_full_product_loop_e2e:
            continue
        target_path = artifact_dir / module.PRODUCT_PAGES_FLOW_ARTIFACT_PATHS[group_id].name
        _write(target_path, payload)

    browser_input_groups = (
        (
            CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
            CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
        ),
        ("product_pages_browser_smoke", "product_pages_browser_smoke"),
        ("product_pages_seven_day_diary_smoke", "product_pages_seven_day_diary_smoke"),
        ("product_pages_short_term_context_smoke", "product_pages_short_term_context_smoke"),
        ("product_pages_visual_qa", "product_pages_visual_qa"),
        ("product_pages_body_noplan_degraded_smoke", "product_pages_body_noplan_degraded_smoke"),
        ("fixture_full_product_loop_e2e", "fixture_full_product_loop_e2e"),
        ("product_pages_self_use_flow_gate", "product_pages_self_use_flow_gate"),
    )
    for path_group_id, payload_group_id in browser_input_groups:
        if path_group_id == "fixture_full_product_loop_e2e" and omit_fixture_full_product_loop_e2e:
            continue
        target_path = artifact_dir / module.BROWSER_GATE_ARTIFACT_PATHS[path_group_id].name
        _merge_write(target_path, browser_gate_inputs[payload_group_id])
    if not omit_browser_target_ui:
        target_path = (
            artifact_dir
            / module.BROWSER_GATE_ARTIFACT_PATHS["product_pages_target_candidate_ui_smoke"].name
        )
        _merge_write(target_path, browser_gate_inputs["product_pages_target_candidate_ui_smoke"])

    product_loop_support = {
        "browser_fixture_dogfood": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_browser_one_day_fixture_dogfood",
            "status": "browser_fixture_pass",
            "fixture_evidence_used": True,
            "fixture_fooddb_evidence_used": True,
            "fooddb_evidence_used": False,
            "fooddb_evidence_used_normalized_for_local_review": True,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "manager_dogfood_summary": {
                "macro_present_evidence_seen": True,
                "macro_missing_evidence_seen": True,
            },
        },
        "browser_realistic_dogfood": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_browser_realistic_web_dogfood_v2",
            "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
            "fixture_evidence_used": True,
            "real_fooddb_pass_claimed": False,
        },
        "one_day_realistic_dogfood": _one_day_realistic_dogfood_payload(),
        "operator_review": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_dogfood_operator_review_surface",
            "status": "diagnostic_review_with_approved_evidence",
            "source_artifact": "accurate_intake_one_day_realistic_web_dogfood",
            "source_status": "pass",
            "claim_scope": "local_dogfood_operator_review_surface",
            "local_only": True,
            "do_not_commit": True,
            "food_kb_truth_updated": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_readiness_claimed": False,
            "classification_policy": {
                "food_kb_truth_update_allowed": False,
                "frontend_semantic_owner": False,
            },
        },
    }
    for group_id, payload in product_loop_support.items():
        _write(artifact_dir / module.PRODUCT_LOOP_HANDOFF_EVIDENCE_FILENAMES[group_id], payload)


def _seed_local_review_gate_inputs(artifact_dir: Path) -> None:
    from scripts.build_current_shell_compatibility_local_review_evidence_manifest import (
        DEFAULT_EVIDENCE_PATHS as LOCAL_REVIEW_EVIDENCE_PATHS,
    )
    from tests.test_current_shell_compatibility_local_review_gate_runner import (
        _required_payloads as _required_local_review_payloads,
    )

    for group_id, payload in _required_local_review_payloads().items():
        target_path = artifact_dir / LOCAL_REVIEW_EVIDENCE_PATHS[group_id].name
        if not target_path.exists():
            _write(target_path, payload)


def test_refresh_chain_prepares_candidate_when_upstream_runtime_and_browser_evidence_are_green(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"
    _seed_required_gate_inputs(artifact_dir)

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    browser_activation = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["browser_activation_evidence_gate"]
        ).read_text(encoding="utf-8")
    )
    pre_live_evidence = json.loads(
        (artifact_dir / module.REFRESHED_ARTIFACT_FILENAMES["pre_live_evidence"]).read_text(
            encoding="utf-8"
        )
    )
    pre_live_pack = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["pre_live_decision_pack"]
        ).read_text(encoding="utf-8")
    )
    dogfood_review_queue = json.loads(
        (
            artifact_dir / module.DEFAULT_EVIDENCE_PATHS["dogfood_review_queue"].name
        ).read_text(encoding="utf-8")
    )
    today_macro_mirror_gate = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["today_macro_mirror_gate"]
        ).read_text(encoding="utf-8")
    )
    body_observation_same_truth_gate = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["body_observation_same_truth_gate"]
        ).read_text(encoding="utf-8")
    )
    bootstrap_same_truth_gate = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["bootstrap_same_truth_gate"]
        ).read_text(encoding="utf-8")
    )
    clarify_commit_correction_same_truth_gate = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["clarify_commit_correction_same_truth_gate"]
        ).read_text(encoding="utf-8")
    )
    candidate = json.loads(
        (
            artifact_dir / module.REFRESHED_ARTIFACT_FILENAMES["local_web_candidate"]
        ).read_text(encoding="utf-8")
    )
    approved_fooddb_artifact = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["approved_packet_ready_fooddb_artifact"]
        ).read_text(encoding="utf-8")
    )
    product_loop_handoff = json.loads(
        (
            artifact_dir / module.REFRESHED_ARTIFACT_FILENAMES["product_loop_handoff"]
        ).read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert printed["status"] == "pass"
    assert printed["closeout_navigation"] == {
        "missing_evidence": [],
        "stale_evidence": [],
        "first_blocking_gate": None,
        "non_claims": {
            "product_ready": False,
            "web_ready": False,
            "private_self_use_approved": False,
            "production_ready": False,
            "live_llm_ready": False,
            "fooddb_truth_promoted": False,
        },
    }
    assert printed["candidate_prepared"] is True
    assert printed["route_backed_macro_checked"] is True
    assert printed["route_backed_macro_closeout_status"] == "pass"
    route_backed_macro = printed["route_backed_macro_closeout"]
    assert route_backed_macro["macro_present_exact_item"]["current_budget"]["consumed_kcal"] == 300
    assert route_backed_macro["macro_present_exact_item"]["current_budget"]["consumed_protein"] == 12
    assert route_backed_macro["macro_present_exact_item"]["current_budget"]["consumed_carbs"] == 48
    assert route_backed_macro["macro_present_exact_item"]["current_budget"]["consumed_fat"] == 6
    assert route_backed_macro["macro_present_exact_item"]["current_budget"]["show_macro"] is True
    assert (
        route_backed_macro["macro_present_exact_item"]["approved_exact_macro_trace"][
            "macro_truth_owner"
        ]
        == "fooddb_approved_packet"
    )
    assert (
        route_backed_macro["macro_missing_exact_item"]["current_budget"]["consumed_kcal"]
        == 130
    )
    assert route_backed_macro["macro_missing_exact_item"]["current_budget"]["show_macro"] is False
    assert (
        route_backed_macro["macro_missing_exact_item"]["approved_exact_macro_trace"][
            "macro_visibility_status"
        ]
        == "hidden_missing_source"
    )
    assert route_backed_macro["non_claims"]["real_fooddb_pass_claimed"] is False
    assert route_backed_macro["non_claims"]["product_readiness_claimed"] is False
    assert route_backed_macro["non_claims"]["private_self_use_approved"] is False
    assert browser_activation["status"] == "browser_activation_evidence_ready_for_human_review"
    assert browser_activation["pass_type"] == "contract"
    assert (
        browser_activation["appshell_claim_boundary"]["status"]
        == "ready_for_runtime_and_browser_claims"
    )
    assert browser_activation["appshell_claim_boundary"]["runtime_backed_claim_ready"] is True
    assert browser_activation["appshell_claim_boundary"]["browser_executed_claim_ready"] is True
    assert pre_live_evidence["_evidence_metadata"]["status"] == "complete"
    assert pre_live_evidence["non_fooddb_manager_tool_contract"]["status"] == (
        "non_fooddb_manager_tool_contract_ready_for_human_review"
    )
    assert today_macro_mirror_gate["status"] == "today_macro_mirror_gate_ready_for_human_review"
    assert (
        bootstrap_same_truth_gate["status"]
        == "bootstrap_same_truth_gate_ready_for_human_review"
    )
    assert (
        body_observation_same_truth_gate["status"]
        == "body_observation_same_truth_gate_ready_for_human_review"
    )
    assert (
        clarify_commit_correction_same_truth_gate["status"]
        == "clarify_commit_correction_same_truth_gate_ready_for_human_review"
    )
    assert pre_live_pack["selected_option"] == "ready_for_human_limited_live_canary_decision"
    assert "ready_for_live_diagnostic_decision" not in pre_live_pack
    assert dogfood_review_queue["review_candidate_count"] == 0
    assert dogfood_review_queue["review_candidates"] == []
    assert candidate["local_web_self_use_candidate_v2"]["candidate_prepared"] is True
    assert candidate["local_web_self_use_candidate_v2"]["route_backed_macro_checked"] is True
    assert (
        candidate["local_web_self_use_candidate_v2"]["route_backed_macro_closeout_status"]
        == "pass"
    )
    assert candidate["local_web_self_use_candidate_v2"]["blockers"] == []
    chain = candidate["local_web_self_use_candidate_v2"]["appshell_browser_evidence_chain"]
    assert printed["appshell_browser_evidence_chain"] == chain
    assert chain["browser_artifact_count"] == 7
    assert chain["browser_executed_count"] == 7
    assert chain["all_required_browser_artifacts_executed"] is True
    assert chain["product_pages_self_use_flow_checked"] is True
    assert chain["self_use_flow_gate_strongest_pass_type"] == "browser_executed"
    assert chain["today_macro_runtime_mirror_checked"] is True
    assert chain["renderer_source_closure_checked"] is True
    assert chain["context_target_browser_closure_checked"] is True
    assert chain["body_noplan_degraded_checked"] is True
    assert chain["live_llm_invoked"] is False
    assert chain["fooddb_evidence_used"] is False
    assert chain["websearch_evidence_used"] is False
    assert approved_fooddb_artifact["status"] == "approved_packet_ready_fooddb_artifact_ready"
    assert approved_fooddb_artifact["ready_for_other_tracks"] is True
    assert approved_fooddb_artifact["fixture_or_real"] == "real"
    assert (
        approved_fooddb_artifact["approved_packet_ready_evidence_artifact"]["macro_contract"][
            "macro_truth_owner"
        ]
        == "fooddb_approved_packet"
    )
    assert product_loop_handoff["status"] == (
        "product_loop_handoff_ready_for_fdb_integration_validation"
    )
    assert product_loop_handoff["fooddb_artifact_status"] == (
        "approved_packet_ready_evidence_metadata_valid"
    )
    assert product_loop_handoff["ready_for_fdb_integration"] is True
    assert "one_day_realistic_dogfood" in product_loop_handoff[
        "product_loop_required_evidence"
    ]
    assert "browser_realistic_dogfood" not in product_loop_handoff[
        "product_loop_required_evidence"
    ]
    assert product_loop_handoff["product_loop_evidence_status"][
        "one_day_realistic_dogfood"
    ] == {
        "present": True,
        "status": "pass",
        "blockers": [],
    }
    assert product_loop_handoff["fooddb_contract_validation"] == {
        "source": "one_day_realistic_web_dogfood.evidence",
        "packet_evidence_consumed": True,
        "approved_fooddb_evidence_fixture_used": True,
        "fooddb_evidence_used": True,
        "macro_present_evidence_seen": True,
        "macro_missing_evidence_seen": True,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "product_readiness_claimed": False,
    }
    assert product_loop_handoff["fooddb_evidence_used"] is False
    assert product_loop_handoff["real_fooddb_pass_claimed"] is False
    assert product_loop_handoff["dogfood_pass"] is False
    assert product_loop_handoff["product_readiness_claimed"] is False
    assert product_loop_handoff["private_self_use_approved"] is False
    assert printed["approved_fooddb_artifact_status"] == (
        "approved_packet_ready_fooddb_artifact_ready"
    )
    assert printed["product_loop_handoff_status"] == (
        "product_loop_handoff_ready_for_fdb_integration_validation"
    )
    assert printed["ready_for_fdb_integration_validation"] is True
    assert printed["fooddb_evidence_used"] is False
    assert printed["real_fooddb_pass_claimed"] is False
    assert json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["product_pages_self_use_flow_gate"]
        ).read_text(encoding="utf-8")
    )["summary"]["three_distinct_pages_verified"] is True
    assert json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["context_live_diagnostic_gate"]
        ).read_text(encoding="utf-8")
    )["holdout_plan_required"] is True


def test_refresh_chain_reuses_existing_expensive_closeout_artifacts(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"
    _seed_required_gate_inputs(artifact_dir)

    def fail_if_regenerated(*_args, **_kwargs):
        raise AssertionError("expensive closeout artifact should be reused")

    for name in [
        "_generate_accurate_intake_mvp_gate_summary",
        "_generate_product_pages_browser_smoke",
        "_generate_product_pages_seven_day_diary_smoke",
        "_generate_product_pages_body_noplan_degraded_smoke",
        "_generate_product_pages_target_candidate_ui_smoke",
        "_generate_product_pages_visual_qa",
        "_generate_fixture_full_product_loop_e2e",
    ]:
        monkeypatch.setattr(module, name, fail_if_regenerated)

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert printed["status"] == "pass"
    assert printed["closeout_navigation"]["first_blocking_gate"] is None


def test_refresh_chain_regenerates_current_shell_local_review_decision_from_evidence_inputs(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"
    _seed_required_gate_inputs(artifact_dir)
    _seed_local_review_gate_inputs(artifact_dir)
    local_review_decision_path = (
        artifact_dir / module.DEFAULT_EVIDENCE_PATHS[CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID].name
    )
    local_review_decision_path.unlink()

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)
    manifest = json.loads(
        (
            artifact_dir
            / "accurate_intake_current_shell_compatibility_local_review_evidence_manifest.json"
        ).read_text(encoding="utf-8")
    )
    decision = json.loads(local_review_decision_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["status"] == "pass"
    assert manifest["_manifest_metadata"]["status"] == "complete"
    assert decision["status"] == CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS
    assert decision["ready_for_live_diagnostic_decision"] is False
    assert decision["ready_for_fdb_integration"] is False


def test_refresh_chain_generates_fixture_dependency_before_browser_activation_gate(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"
    _seed_required_gate_inputs(artifact_dir, omit_fixture_full_product_loop_e2e=True)

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)
    browser_activation = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["browser_activation_evidence_gate"]
        ).read_text(encoding="utf-8")
    )
    pre_live_pack = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["pre_live_decision_pack"]
        ).read_text(encoding="utf-8")
    )
    product_loop_handoff = json.loads(
        (
            artifact_dir / module.REFRESHED_ARTIFACT_FILENAMES["product_loop_handoff"]
        ).read_text(encoding="utf-8")
    )
    fixture_loop = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["fixture_full_product_loop_e2e"]
        ).read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert printed["status"] == "pass"
    assert (
        "fixture_full_product_loop_e2e"
        not in printed["closeout_navigation"]["missing_evidence"]
    )
    assert printed["closeout_navigation"]["first_blocking_gate"] is None
    assert printed["closeout_navigation"]["non_claims"]["private_self_use_approved"] is False
    assert printed["closeout_navigation"]["non_claims"]["product_ready"] is False
    assert printed["candidate_prepared"] is True
    assert printed["ready_for_fdb_integration_validation"] is True
    assert browser_activation["status"] == "browser_activation_evidence_ready_for_human_review"
    assert browser_activation["blockers"] == []
    assert pre_live_pack["selected_option"] == "ready_for_human_limited_live_canary_decision"
    assert "ready_for_live_diagnostic_decision" not in pre_live_pack
    assert fixture_loop["status"] == "fixture_product_loop_e2e_diagnostic_pass"
    assert fixture_loop["product_readiness_claimed"] is False
    assert fixture_loop["private_self_use_approved"] is False
    assert product_loop_handoff["status"] == (
        "product_loop_handoff_ready_for_fdb_integration_validation"
    )
    assert product_loop_handoff["ready_for_fdb_integration"] is True
    assert product_loop_handoff["fooddb_artifact_status"] == (
        "approved_packet_ready_evidence_metadata_valid"
    )
    assert product_loop_handoff["real_fooddb_pass_claimed"] is False


def test_refresh_chain_generates_static_product_page_inputs_before_reporting_browser_blocker(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    _assert_refresh_chain_closeout_pass(exit_code, printed)
    navigation = printed["closeout_navigation"]
    assert "ui_same_truth_contract" not in navigation["missing_evidence"]

    static_artifacts = {
        "ui_same_truth_contract": "accurate_intake_ui_same_truth_render_contract.json",
        "product_pages_renderer_source_map": (
            "accurate_intake_product_pages_renderer_source_map.json"
        ),
        "today_macro_runtime_mirror_gate": (
            "accurate_intake_today_macro_runtime_mirror_gate.json"
        ),
        "product_pages_renderer_source_closure_gate": (
            "accurate_intake_product_pages_renderer_source_closure_gate.json"
        ),
    }
    for filename in static_artifacts.values():
        assert (artifact_dir / filename).exists()

    ui_contract = json.loads(
        (artifact_dir / static_artifacts["ui_same_truth_contract"]).read_text(encoding="utf-8")
    )
    renderer_source_map = json.loads(
        (artifact_dir / static_artifacts["product_pages_renderer_source_map"]).read_text(
            encoding="utf-8"
        )
    )
    today_macro_runtime = json.loads(
        (artifact_dir / static_artifacts["today_macro_runtime_mirror_gate"]).read_text(
            encoding="utf-8"
        )
    )
    renderer_closure = json.loads(
        (
            artifact_dir
            / static_artifacts["product_pages_renderer_source_closure_gate"]
        ).read_text(encoding="utf-8")
    )
    assert ui_contract["status"] == "pass"
    assert renderer_source_map["status"] == "product_pages_renderer_source_map_ready_for_human_review"
    assert today_macro_runtime["status"] == "today_macro_runtime_mirror_gate_ready_for_browser"
    assert renderer_closure["status"] == "product_pages_renderer_source_closure_ready_for_browser"
    assert today_macro_runtime["frontend_semantic_owner"] is False
    assert renderer_closure["mutation_authority"] is False


def test_refresh_chain_generates_required_product_pages_browser_smoke_before_next_blocker(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    browser_smoke_path = (
        artifact_dir / module.PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["product_pages_browser_smoke"].name
    )
    browser_smoke = json.loads(browser_smoke_path.read_text(encoding="utf-8"))

    _assert_refresh_chain_closeout_pass(exit_code, printed)
    assert browser_smoke["status"] == "pass"
    assert browser_smoke["browser_executed"] is True
    assert browser_smoke["browser_execution_required"] is True
    assert browser_smoke["fooddb_triad_same_truth_non_claims"]["real_fooddb_pass_claimed"] is False
    assert browser_smoke["fooddb_triad_same_truth_non_claims"]["product_readiness_claimed"] is False
    assert "product_pages_browser_smoke" not in printed["closeout_navigation"]["missing_evidence"]


def test_refresh_chain_generates_required_seven_day_diary_smoke_before_next_blocker(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    seven_day_path = (
        artifact_dir
        / module.PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["product_pages_seven_day_diary_smoke"].name
    )
    seven_day = json.loads(seven_day_path.read_text(encoding="utf-8"))

    _assert_refresh_chain_closeout_pass(exit_code, printed)
    assert seven_day["status"] == "pass"
    assert seven_day["browser_executed"] is True
    assert seven_day["browser_execution_required"] is True
    assert seven_day["day_count_checked"] == 7
    assert seven_day["seven_day_window_checked"] is True
    assert seven_day["product_readiness_claimed"] is False
    assert seven_day["private_self_use_approved"] is False
    assert (
        "product_pages_seven_day_diary_smoke"
        not in printed["closeout_navigation"]["missing_evidence"]
    )


def test_refresh_chain_generates_required_body_noplan_smoke_before_next_blocker(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    body_noplan_path = (
        artifact_dir
        / module.PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["product_pages_body_noplan_degraded_smoke"].name
    )
    body_noplan = json.loads(body_noplan_path.read_text(encoding="utf-8"))

    _assert_refresh_chain_closeout_pass(exit_code, printed)
    assert body_noplan["status"] == "pass"
    assert body_noplan["browser_executed"] is True
    assert body_noplan["browser_execution_required"] is True
    assert body_noplan["no_plan_body_status_rendered"] is True
    assert body_noplan["body_targets_hidden_for_no_plan"] is True
    assert body_noplan["today_no_plan_budget_rendered"] is True
    assert body_noplan["manager_provider_call_count"] == 0
    assert body_noplan["no_bootstrap_or_mutation_post"] is True
    assert (
        "product_pages_body_noplan_degraded_smoke"
        not in printed["closeout_navigation"]["missing_evidence"]
    )


def test_refresh_chain_product_pages_flow_consumes_generated_body_same_truth_gate(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    body_same_truth_path = (
        artifact_dir
        / module.REFRESHED_ARTIFACT_FILENAMES["body_observation_same_truth_gate"]
    )
    body_same_truth = json.loads(body_same_truth_path.read_text(encoding="utf-8"))

    _assert_refresh_chain_closeout_pass(exit_code, printed)
    assert body_same_truth["status"] == "body_observation_same_truth_gate_ready_for_human_review"
    assert body_same_truth["pass_type"] == "browser_executed"
    assert "body_observation_same_truth_gate" not in printed["closeout_navigation"]["missing_evidence"]


def test_refresh_chain_generates_required_short_term_context_smoke_before_next_blocker(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    short_term_path = (
        artifact_dir
        / module.PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["product_pages_short_term_context_smoke"].name
    )
    short_term = json.loads(short_term_path.read_text(encoding="utf-8"))

    _assert_refresh_chain_closeout_pass(exit_code, printed)
    assert short_term["status"] == "pass"
    assert short_term["browser_executed"] is True
    assert short_term["browser_execution_required"] is True
    assert short_term["browser_reload_checked"] is True
    assert short_term["pending_followup_created"] is True
    assert short_term["pending_followup_reloaded"] is True
    assert short_term["loaded_context_summary_present"] is True
    assert short_term["pending_pins_present_after_followup"] is True
    assert short_term["chat_history_context_fields_reloaded"] is True
    assert short_term["product_pages_no_debug_trace"] is True
    assert (
        "product_pages_short_term_context_smoke"
        not in printed["closeout_navigation"]["missing_evidence"]
    )


def test_refresh_chain_generates_required_target_candidate_ui_smoke_before_next_blocker(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    target_candidate_path = (
        artifact_dir
        / module.PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["product_pages_target_candidate_ui_smoke"].name
    )
    target_candidate = json.loads(target_candidate_path.read_text(encoding="utf-8"))

    _assert_refresh_chain_closeout_pass(exit_code, printed)
    assert target_candidate["status"] == "pass"
    assert target_candidate["browser_executed"] is True
    assert target_candidate["browser_execution_required"] is True
    assert target_candidate["target_candidate_surface_checked"] is True
    assert target_candidate["target_candidate_count_rendered"] == 2
    assert target_candidate["target_candidate_names_rendered"] == ["luwei", "milk tea"]
    assert target_candidate["target_candidate_list_read_only"] is True
    assert target_candidate["manager_provider_call_count"] == 0
    assert (
        "product_pages_target_candidate_ui_smoke"
        not in printed["closeout_navigation"]["missing_evidence"]
    )


def test_refresh_chain_generates_required_context_target_browser_closure_before_next_blocker(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    closure_path = (
        artifact_dir
        / module.PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["product_pages_context_target_browser_closure"].name
    )
    closure = json.loads(closure_path.read_text(encoding="utf-8"))

    _assert_refresh_chain_closeout_pass(exit_code, printed)
    assert closure["status"] == "context_target_browser_closure_ready_for_self_use_flow_gate"
    assert closure["pass_type"] == "browser_executed"
    assert closure["browser_executed"] is True
    assert closure["context_engineering_present"] is True
    assert closure["session_state_injected"] is True
    assert closure["pending_meal_or_correction_context_present"] is True
    assert closure["target_candidate_list_read_only"] is True
    assert closure["frontend_selects_target"] is False
    assert closure["product_readiness_claimed"] is False
    assert closure["private_self_use_approved"] is False
    assert (
        "product_pages_context_target_browser_closure"
        not in printed["closeout_navigation"]["missing_evidence"]
    )


def test_refresh_chain_generates_required_visual_qa_before_next_blocker(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    visual_qa_path = artifact_dir / module.PRODUCT_PAGES_FLOW_ARTIFACT_PATHS[
        "product_pages_visual_qa"
    ].name
    visual_qa = json.loads(visual_qa_path.read_text(encoding="utf-8"))

    _assert_refresh_chain_closeout_pass(exit_code, printed)
    assert visual_qa["status"] == "pass"
    assert visual_qa["browser_executed"] is True
    assert visual_qa["browser_execution_required"] is True
    assert visual_qa["desktop_screenshots_captured"] is True
    assert visual_qa["mobile_screenshots_captured"] is True
    assert visual_qa["three_distinct_pages_verified"] is True
    assert visual_qa["desktop_no_overflow"] is True
    assert visual_qa["mobile_no_overflow"] is True
    assert visual_qa["visible_trace_debug_terms_absent"] is True
    assert "product_pages_visual_qa" not in printed["closeout_navigation"]["missing_evidence"]


def test_refresh_chain_generates_required_fixture_full_product_loop_before_next_blocker(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    fixture_loop_path = artifact_dir / module.PRODUCT_PAGES_FLOW_ARTIFACT_PATHS[
        "fixture_full_product_loop_e2e"
    ].name
    fixture_loop = json.loads(fixture_loop_path.read_text(encoding="utf-8"))

    _assert_refresh_chain_closeout_pass(exit_code, printed)
    assert fixture_loop["status"] == "fixture_product_loop_e2e_diagnostic_pass"
    assert fixture_loop["browser_executed"] is True
    assert fixture_loop["diagnostic_only"] is True
    assert fixture_loop["local_only"] is True
    assert fixture_loop["product_readiness_claimed"] is False
    assert fixture_loop["private_self_use_approved"] is False
    assert (
        "fixture_full_product_loop_e2e"
        not in printed["closeout_navigation"]["missing_evidence"]
    )


def test_local_mvp_candidate_bundle_consumes_generated_fixture_full_loop(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module
    from tests.test_accurate_intake_pl_ce_local_mvp_candidate_bundle import _valid_inputs

    valid_inputs = _valid_inputs()
    artifact_dir = tmp_path / "artifacts"
    _write(
        artifact_dir / module.PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["ui_same_truth_contract"].name,
        valid_inputs["ui_same_truth_contract"],
    )
    _write(
        artifact_dir / module.PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["fixture_full_product_loop_e2e"].name,
        valid_inputs["fixture_full_product_loop_e2e"],
    )
    monkeypatch.setattr(module, "build_context_conditioned_intent_wall_artifact", lambda: valid_inputs["context_conditioned_intent_wall"])
    monkeypatch.setattr(module, "build_short_term_context_runtime_replay_artifact", lambda: valid_inputs["short_term_context_runtime_replay"])
    monkeypatch.setattr(module, "build_fake_provider_context_smoke_artifact", lambda: {"artifact_type": "fake_context", "status": "pass"})
    monkeypatch.setattr(module, "build_context_quality_pack_report", lambda: valid_inputs["context_quality_pack"])
    monkeypatch.setattr(module, "build_pl_ce_context_coverage_matrix_artifact", lambda **_: valid_inputs["context_coverage_matrix"])
    monkeypatch.setattr(module, "build_context_live_diagnostic_case_matrix_artifact", lambda: valid_inputs["context_live_diagnostic_case_matrix"])
    monkeypatch.setattr(module, "build_context_live_diagnostic_anti_overfit_guard_artifact", lambda _: valid_inputs["context_live_diagnostic_anti_overfit_guard"])
    monkeypatch.setattr(module, "build_fixture_evidence_packet_emulator_artifact", lambda: valid_inputs["fixture_packet_emulator"])
    monkeypatch.setattr(module, "build_correction_removal_fixture_flow_artifact", lambda: valid_inputs["correction_removal_fixture_flow"])
    monkeypatch.setattr(module, "build_responder_input_contract_fake_smoke_artifact", lambda: valid_inputs["responder_input_contract_fake_smoke"])
    monkeypatch.setattr(module, "build_fake_provider_tool_loop_smoke_artifact", lambda **_: valid_inputs["fake_provider_tool_loop_smoke"])
    monkeypatch.setattr(module, "build_review_eval_candidate_pipeline_report", lambda **_: valid_inputs["review_eval_candidate_pipeline"])
    monkeypatch.setattr(module, "build_local_operator_data_hygiene_bundle", lambda **_: valid_inputs["local_operator_data_hygiene_bundle"])

    bundle = module._generate_current_shell_local_mvp_candidate_bundle(
        artifacts_dir=artifact_dir,
        mvp_gate_summary=valid_inputs["mvp_gate_summary"],
    )

    assert bundle["status"] == "pl_ce_local_mvp_candidate_ready_for_human_review"
    assert bundle["blockers"] == []
    fixture_status = bundle["included_artifact_statuses"]["fixture_full_product_loop_e2e"]
    assert fixture_status["present"] is True
    assert fixture_status["status"] == "fixture_product_loop_e2e_diagnostic_pass"


def test_refresh_chain_generates_local_mvp_candidate_bundle_before_browser_activation(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)

    bundle_path = artifact_dir / module.BROWSER_GATE_ARTIFACT_PATHS[
        CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID
    ].name
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    browser_activation = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["browser_activation_evidence_gate"]
        ).read_text(encoding="utf-8")
    )

    _assert_refresh_chain_closeout_pass(exit_code, printed)
    assert bundle["status"] == "pl_ce_local_mvp_candidate_ready_for_human_review"
    assert bundle["local_only"] is True
    assert bundle["diagnostic_only"] is True
    assert bundle["product_readiness_claimed"] is False
    assert bundle["private_self_use_approved"] is False
    assert browser_activation["status"] == "browser_activation_evidence_ready_for_human_review"
    assert browser_activation["blockers"] == []
    assert (
        CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID
        not in printed["closeout_navigation"]["missing_evidence"]
    )
    assert printed["closeout_navigation"]["first_blocking_gate"] is None


def test_refresh_chain_aligns_legacy_prelive_inputs_to_current_shell_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)
    pre_live_evidence = json.loads(
        (artifact_dir / module.REFRESHED_ARTIFACT_FILENAMES["pre_live_evidence"]).read_text(
            encoding="utf-8"
        )
    )
    pre_live_pack = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["pre_live_decision_pack"]
        ).read_text(encoding="utf-8")
    )

    _assert_refresh_chain_closeout_pass(exit_code, printed)
    missing = set(printed["closeout_navigation"]["missing_evidence"])
    stale_legacy_groups = {
        "browser_shell_smoke",
        "chat_history_reload_gate",
        "free_text_manual_target_gate",
        "local_dogfood_data_hygiene",
        "ui_context_alignment_pack",
        "manager_intent_readiness_review_pack",
        "context_conditioned_intent_wall",
    }
    assert missing.isdisjoint(stale_legacy_groups)
    assert pre_live_evidence["_evidence_metadata"]["status"] != "blocked_missing_evidence"
    assert (
        pre_live_pack["selected_option"]
        == "ready_for_human_limited_live_canary_decision"
    )
    blockers = set(pre_live_pack.get("blockers") or [])
    assert not any(blocker.startswith("ui_context_alignment_pack.") for blocker in blockers)
    assert not any(
        blocker.startswith("manager_intent_readiness_review_pack.")
        for blocker in blockers
    )
    assert "ready_for_live_diagnostic_decision" not in pre_live_pack
    assert printed["private_self_use_approved"] is False
    assert printed["product_readiness_claimed"] is False


def test_refresh_chain_generates_current_shell_local_review_inputs_before_closeout_clear(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)
    local_review_manifest = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES[
                "current_shell_compatibility_local_review_evidence_manifest"
            ]
        ).read_text(encoding="utf-8")
    )
    local_review_decision = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES[
                "current_shell_compatibility_local_review_decision_pack"
            ]
        ).read_text(encoding="utf-8")
    )
    pre_live_pack = json.loads(
        (
            artifact_dir
            / module.REFRESHED_ARTIFACT_FILENAMES["pre_live_decision_pack"]
        ).read_text(encoding="utf-8")
    )
    product_loop_handoff = json.loads(
        (
            artifact_dir / module.REFRESHED_ARTIFACT_FILENAMES["product_loop_handoff"]
        ).read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert printed["status"] == "pass"
    assert local_review_manifest["_manifest_metadata"]["status"] == "complete"
    assert local_review_decision["status"] == CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS
    assert local_review_decision["ready_for_live_diagnostic_decision"] is False
    assert local_review_decision["ready_for_fdb_integration"] is False
    assert pre_live_pack["selected_option"] == "ready_for_human_limited_live_canary_decision"
    assert (
        CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_GROUP_ID
        not in printed["closeout_navigation"]["missing_evidence"]
    )
    assert printed["closeout_navigation"]["first_blocking_gate"] is None
    assert printed["candidate_prepared"] is True
    assert printed["ready_for_fdb_integration_validation"] is True
    assert printed["product_loop_handoff_status"] == (
        "product_loop_handoff_ready_for_fdb_integration_validation"
    )
    assert product_loop_handoff["ready_for_fdb_integration"] is True
    assert product_loop_handoff["real_fooddb_pass_claimed"] is False
    assert product_loop_handoff["dogfood_pass"] is False
    assert printed["private_self_use_approved"] is False
    assert printed["product_readiness_claimed"] is False


def test_refresh_chain_generates_operator_review_before_product_loop_handoff(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"

    exit_code = module.main(["--artifacts-dir", str(artifact_dir)])
    printed = json.loads(capsys.readouterr().out)
    operator_review = json.loads(
        (
            artifact_dir
            / module.PRODUCT_LOOP_HANDOFF_EVIDENCE_FILENAMES["operator_review"]
        ).read_text(encoding="utf-8")
    )
    product_loop_handoff = json.loads(
        (
            artifact_dir / module.REFRESHED_ARTIFACT_FILENAMES["product_loop_handoff"]
        ).read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert printed["status"] == "pass"
    assert operator_review["artifact_type"] == "accurate_intake_dogfood_operator_review_surface"
    assert operator_review["status"] == "diagnostic_review_with_approved_evidence"
    assert operator_review["source_artifact"] == "accurate_intake_one_day_realistic_web_dogfood"
    assert operator_review["source_status"] == "pass"
    assert operator_review["local_only"] is True
    assert operator_review["real_fooddb_pass_claimed"] is False
    assert operator_review["dogfood_pass"] is False
    assert operator_review["product_readiness_claimed"] is False
    assert operator_review["private_self_use_approved"] is False
    assert operator_review["food_kb_truth_updated"] is False
    assert product_loop_handoff["product_loop_evidence_status"]["operator_review"][
        "status"
    ] == "diagnostic_review_with_approved_evidence"
    assert "operator_review_not_diagnostic_review" not in product_loop_handoff["blockers"]
    assert "operator_review_real_fooddb_overclaim" not in product_loop_handoff["blockers"]
    assert product_loop_handoff["ready_for_fdb_integration"] is True
    assert product_loop_handoff["real_fooddb_pass_claimed"] is False
    assert product_loop_handoff["dogfood_pass"] is False


def test_closeout_navigation_reports_stale_evidence_without_readiness_claims() -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    navigation = module._build_closeout_navigation(
        [
            (
                "product_pages_self_use_flow_gate",
                {
                    "status": "blocked",
                    "blockers": [
                        "product_pages_browser_smoke.unexpected_status:old_contract",
                    ],
                },
            )
        ]
    )

    assert navigation["missing_evidence"] == []
    assert navigation["stale_evidence"] == ["product_pages_browser_smoke"]
    assert navigation["first_blocking_gate"] == {
        "gate_id": "product_pages_self_use_flow_gate",
        "status": "blocked",
        "blocker_count": 1,
        "first_blocker": "product_pages_browser_smoke.unexpected_status:old_contract",
    }
    assert navigation["non_claims"]["product_ready"] is False
    assert navigation["non_claims"]["web_ready"] is False


def test_refresh_chain_source_stays_out_of_fooddb_live_and_shared_contract_boundaries() -> None:
    source = Path(
        "scripts/run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain.py"
    ).read_text(encoding="utf-8")

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "builderspace_adapter",
        "live_llm_invoked = True",
        "fooddb_evidence_used = True",
        "private_self_use_approved = True",
        "product_readiness_claimed = True",
    ):
        assert fragment not in source

    assert "build_approved_packet_ready_fooddb_artifact" in source
    assert "build_product_loop_handoff_v3" in source
