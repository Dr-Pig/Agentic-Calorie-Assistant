from __future__ import annotations

import json
from pathlib import Path

from tests.test_accurate_intake_local_web_self_use_candidate_v2_gate_runner import (
    _required_payloads,
)
from tests.test_accurate_intake_pl_ce_browser_activation_evidence_gate import (
    _valid_inputs as _valid_browser_gate_inputs,
)
from tests.test_accurate_intake_pl_ce_product_pages_self_use_flow_gate import (
    _valid_inputs as _valid_product_pages_flow_inputs,
)


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _merge_write(path: Path, payload: dict[str, object]) -> None:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(existing, dict):
            merged = dict(existing)
            merged.update(payload)
            _write(path, merged)
            return
    _write(path, payload)


def _seed_required_gate_inputs(artifact_dir: Path, *, omit_browser_target_ui: bool = False) -> None:
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
        target_path = artifact_dir / module.PRODUCT_PAGES_FLOW_ARTIFACT_PATHS[group_id].name
        _write(target_path, payload)

    browser_input_groups = (
        "pl_ce_local_mvp_candidate_bundle",
        "product_pages_browser_smoke",
        "product_pages_seven_day_diary_smoke",
        "product_pages_short_term_context_smoke",
        "product_pages_visual_qa",
        "fixture_full_product_loop_e2e",
    )
    for group_id in browser_input_groups:
        target_path = artifact_dir / module.BROWSER_GATE_ARTIFACT_PATHS[group_id].name
        _merge_write(target_path, browser_gate_inputs[group_id])
    if not omit_browser_target_ui:
        target_path = (
            artifact_dir
            / module.BROWSER_GATE_ARTIFACT_PATHS["product_pages_target_candidate_ui_smoke"].name
        )
        _merge_write(target_path, browser_gate_inputs["product_pages_target_candidate_ui_smoke"])


def test_refresh_chain_honestly_blocks_current_repo_truth_until_upstream_runtime_gates_are_green(
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

    assert exit_code == 1
    assert printed["status"] == "blocked"
    assert printed["candidate_prepared"] is False
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
    assert pre_live_pack["selected_option"] == "stay_local_self_use"
    assert pre_live_pack["ready_for_live_diagnostic_decision"] is False
    assert candidate["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "pre-live selected option: stay_local_self_use" in candidate[
        "local_web_self_use_candidate_v2"
    ]["blockers"]
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


def test_refresh_chain_honestly_blocks_when_browser_activation_dependencies_are_missing(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import run_accurate_intake_local_web_self_use_candidate_v2_refresh_chain as module

    artifact_dir = tmp_path / "artifacts"
    _seed_required_gate_inputs(artifact_dir, omit_browser_target_ui=True)

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

    assert exit_code == 1
    assert printed["status"] == "blocked"
    assert printed["candidate_prepared"] is False
    assert browser_activation["status"] == "blocked"
    assert (
        "product_pages_target_candidate_ui_smoke.unexpected_status:missing"
        in browser_activation["blockers"]
    )
    assert pre_live_pack["selected_option"] == "stay_local_self_use"
    assert pre_live_pack["ready_for_live_diagnostic_decision"] is False


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
