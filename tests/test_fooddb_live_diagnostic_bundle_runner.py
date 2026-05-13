from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from app.shared.infra.json_artifacts import read_json_artifact
from scripts.run_accurate_intake_fooddb_live_diagnostic_bundle import (
    _artifact_paths,
    _build_manifest,
    _build_pre_provider_artifacts,
    main,
)


def test_fooddb_live_diagnostic_bundle_fixture_mode_builds_full_bundle(tmp_path: Path) -> None:
    exit_code = main(["--output-dir", str(tmp_path)])

    assert exit_code == 0
    manifest = read_json_artifact(
        tmp_path / "accurate_intake_fooddb_live_diagnostic_bundle_manifest.json"
    )
    approved_artifact = read_json_artifact(
        tmp_path / "accurate_intake_approved_packet_ready_fooddb_full_current_shell.json"
    )
    real_manager_e2e = read_json_artifact(tmp_path / "accurate_intake_fooddb_real_manager_e2e.json")
    manager_packet_smoke = read_json_artifact(
        tmp_path / "accurate_intake_fooddb_manager_packet_smoke.json"
    )
    preflight = read_json_artifact(
        tmp_path / "accurate_intake_grokfast_fooddb_diagnostic_preflight.json"
    )
    diagnostic = read_json_artifact(tmp_path / "accurate_intake_grokfast_fooddb_packet_smoke.json")
    report = read_json_artifact(tmp_path / "accurate_intake_fooddb_live_diagnostic_report.json")
    probe = read_json_artifact(tmp_path / "accurate_intake_fooddb_manager_contract_probe.json")
    repair_pack = read_json_artifact(
        tmp_path / "accurate_intake_fooddb_manager_contract_repair_pack.json"
    )
    handoff = read_json_artifact(tmp_path / "accurate_intake_fooddb_manager_contract_handoff.json")
    handoff_inspection = read_json_artifact(
        tmp_path / "accurate_intake_fooddb_manager_contract_handoff_inspection.json"
    )
    failure_taxonomy_inspection = read_json_artifact(
        tmp_path / "accurate_intake_fooddb_live_failure_taxonomy_inspection.json"
    )
    post_contract_status = read_json_artifact(
        tmp_path / "accurate_intake_fooddb_evidence_status_post_contract.json"
    )
    status_packet_inspection = read_json_artifact(
        tmp_path / "accurate_intake_fooddb_status_packet_inspection.json"
    )

    assert manifest["bundle_status"] == "pass"
    assert manifest["mode"] == "fixture"
    assert manifest["live_provider_used"] is False
    assert manifest["live_websearch_used"] is False
    assert manifest["runtime_truth_changed"] is False
    assert manifest["runtime_mutation_attempted"] is False
    assert manifest["readiness_claimed"] is False
    assert manifest["approved_packet_ready_selection_profile"] == "full_current_shell"
    assert manifest["approved_packet_ready_item_count"] == 1000
    assert manifest["real_manager_e2e_status"] == "pass"
    assert manifest["real_manager_e2e_case_count"] == 8
    assert manifest["real_manager_e2e_pass_count"] == 8
    assert manifest["seam_status"] == "fixture_only_live_not_checked"
    assert approved_artifact["summary"]["selection_profile"] == "full_current_shell"
    assert approved_artifact["summary"]["packet_ready_item_count"] == 1000
    assert real_manager_e2e["artifact_type"] == "accurate_intake_fooddb_real_manager_e2e"
    assert real_manager_e2e["summary"]["case_count"] == 8
    assert real_manager_e2e["summary"]["pass_count"] == 8
    assert preflight["clear_to_run_live_diagnostic"] is True
    assert preflight["next_required_slice"] == "grokfast_fooddb_packet_live_diagnostic"
    router_readiness = read_json_artifact(
        tmp_path / "accurate_intake_food_evidence_retriever_router_readiness.json"
    )
    live_runner_readiness = read_json_artifact(
        tmp_path / "accurate_intake_grokfast_fooddb_live_runner_readiness_packet.json"
    )
    assert router_readiness["status"] == "pass"
    assert live_runner_readiness["status"] == "pass"
    assert live_runner_readiness["ready_for_grokfast_fooddb_packet_live_diagnostic"] is True
    assert manager_packet_smoke["summary"]["approved_packet_ready_case_count"] == 1000
    assert manager_packet_smoke["summary"]["approved_packet_ready_lane_counts"] == {
        "exact_item_card": 250,
        "generic_common_serving": 400,
        "listed_component": 350,
    }
    assert diagnostic["packet_artifact_type"] == "accurate_intake_fooddb_real_manager_e2e"
    assert diagnostic["summary"]["case_count"] == 8
    assert diagnostic["summary"]["pass_count"] == 8
    assert diagnostic["live_provider_used"] is False
    assert diagnostic["preflight_ref"]["artifact_type"] == preflight["artifact_type"]
    assert diagnostic["preflight_ref"]["status"] == preflight["status"]
    assert diagnostic["router_readiness_ref"]["artifact_type"] == router_readiness["artifact_type"]
    assert diagnostic["router_readiness_ref"]["status"] == router_readiness["status"]
    assert (
        diagnostic["live_runner_readiness_ref"]["artifact_type"]
        == live_runner_readiness["artifact_type"]
    )
    assert diagnostic["live_runner_readiness_ref"]["status"] == live_runner_readiness["status"]
    assert report["source_live_provider_used"] is False
    assert report["next_recommended_slice"] == "run_explicit_grokfast_fooddb_packet_live_diagnostic"
    assert probe["artifact_type"] == "accurate_intake_fooddb_manager_contract_probe"
    assert probe["contract_failure_detected"] is False
    assert probe["next_recommended_slice"] == "run_explicit_grokfast_fooddb_packet_live_diagnostic"
    assert repair_pack["artifact_type"] == "accurate_intake_fooddb_manager_contract_repair_pack"
    assert repair_pack["summary"]["case_count"] == 8
    assert handoff["artifact_type"] == "accurate_intake_fooddb_manager_contract_handoff_v1"
    assert handoff["status"] == "insufficient_contract_handoff_evidence"
    assert handoff["handoff_ready"] is False
    assert handoff["selected_next_step"] == "inspect_fooddb_live_failure_taxonomy"
    assert handoff_inspection["artifact_type"] == (
        "accurate_intake_fooddb_manager_contract_handoff_inspection_v1"
    )
    assert handoff_inspection["summary"]["next_safe_slice"] == "inspect_fooddb_live_failure_taxonomy"
    assert failure_taxonomy_inspection["artifact_type"] == (
        "accurate_intake_fooddb_live_failure_taxonomy_inspection_v1"
    )
    assert (
        failure_taxonomy_inspection["summary"]["next_safe_slice"]
        == "run_explicit_grokfast_fooddb_packet_live_diagnostic"
    )
    assert (
        post_contract_status["summary"]["manager_contract_handoff_status"]
        == "insufficient_contract_handoff_evidence"
    )
    assert post_contract_status["next_required_slices"] == ["inspect_contract_handoff_status"]
    assert status_packet_inspection["status"] == "pass"
    assert status_packet_inspection["summary"]["next_safe_slice"] == "inspect_contract_handoff_status"
    assert manifest["manager_contract_probe_detected_failure"] is False
    assert manifest["manager_contract_handoff_status"] == "insufficient_contract_handoff_evidence"
    assert manifest["manager_contract_handoff_ready"] is False
    assert manifest["manager_contract_selected_next_step"] == "inspect_fooddb_live_failure_taxonomy"
    assert manifest["next_recommended_slice"] == "run_explicit_grokfast_fooddb_packet_live_diagnostic"


def test_fooddb_live_diagnostic_bundle_live_mode_requires_explicit_allow_live(
    tmp_path: Path,
) -> None:
    exit_code = main(["--mode", "live", "--output-dir", str(tmp_path)])

    assert exit_code == 2
    manifest = read_json_artifact(
        tmp_path / "accurate_intake_fooddb_live_diagnostic_bundle_manifest.json"
    )
    diagnostic = read_json_artifact(tmp_path / "accurate_intake_grokfast_fooddb_packet_smoke.json")
    probe = read_json_artifact(tmp_path / "accurate_intake_fooddb_manager_contract_probe.json")
    repair_pack = read_json_artifact(
        tmp_path / "accurate_intake_fooddb_manager_contract_repair_pack.json"
    )
    handoff = read_json_artifact(tmp_path / "accurate_intake_fooddb_manager_contract_handoff.json")
    post_contract_status = read_json_artifact(
        tmp_path / "accurate_intake_fooddb_evidence_status_post_contract.json"
    )

    assert manifest["bundle_status"] == "blocked_or_failed"
    assert manifest["mode"] == "live"
    assert manifest["allow_live"] is False
    assert manifest["live_provider_used"] is False
    assert manifest["runtime_truth_changed"] is False
    assert manifest["runtime_mutation_attempted"] is False
    assert diagnostic["status"] == "blocked"
    assert diagnostic["failure_family"] == "live_mode_requires_explicit_allow_live"
    assert probe["artifact_type"] == "accurate_intake_fooddb_manager_contract_probe"
    assert repair_pack["artifact_type"] == "accurate_intake_fooddb_manager_contract_repair_pack"
    assert handoff["artifact_type"] == "accurate_intake_fooddb_manager_contract_handoff_v1"
    assert (
        manifest["manager_contract_handoff_status"]
        == post_contract_status["summary"]["manager_contract_handoff_status"]
    )
    assert (
        manifest["manager_contract_selected_next_step"]
        == post_contract_status["integration_status"]["manager_contract_selected_next_step"]
    )


def test_fooddb_live_diagnostic_bundle_can_scope_fixture_to_single_case(
    tmp_path: Path,
) -> None:
    exit_code = main(
        [
            "--output-dir",
            str(tmp_path),
            "--case-id",
            "generic_macro_hidden_boba",
        ]
    )

    assert exit_code == 0
    manifest = read_json_artifact(
        tmp_path / "accurate_intake_fooddb_live_diagnostic_bundle_manifest.json"
    )
    diagnostic = read_json_artifact(tmp_path / "accurate_intake_grokfast_fooddb_packet_smoke.json")

    assert manifest["bundle_status"] == "pass"
    assert manifest["selected_case_ids"] == ["generic_macro_hidden_boba"]
    assert manifest["diagnostic_case_count"] == 1
    assert diagnostic["selected_case_ids"] == ["generic_macro_hidden_boba"]
    assert diagnostic["summary"]["case_count"] == 1
    assert [case["case_id"] for case in diagnostic["cases"]] == ["generic_macro_hidden_boba"]


def test_fooddb_live_diagnostic_bundle_manifest_uses_post_contract_status_packet(
    tmp_path: Path,
) -> None:
    paths = _artifact_paths(tmp_path)

    manifest = _build_manifest(
        mode="fixture",
        allow_live=False,
        paths=paths,
        diagnostic_exit=0,
        diagnostic={"live_provider_used": False, "live_websearch_used": False},
        report={
            "seam_status": "fixture_only_live_not_checked",
            "next_recommended_slice": "run_explicit_grokfast_fooddb_packet_live_diagnostic",
        },
        preflight={"clear_to_run_live_diagnostic": True, "status": "clear"},
        live_runner_readiness={"status": "pass"},
        contract_artifacts={
            "approved_packet_ready_artifact": {
                "summary": {
                    "selection_profile": "full_current_shell",
                    "packet_ready_item_count": 1000,
                }
            },
            "real_manager_e2e": {
                "status": "pass",
                "summary": {
                    "case_count": 8,
                    "pass_count": 8,
                },
            },
            "manager_contract_probe": {"contract_failure_detected": False},
            "manager_contract_handoff": {
                "status": "unexpected_new_status",
                "handoff_ready": True,
                "selected_next_step": "raw_handoff_value",
            },
            "manager_contract_handoff_inspection": {
                "summary": {"next_safe_slice": "repair_artifact_alignment_required"},
            },
            "fooddb_live_failure_taxonomy_inspection": {
                "summary": {"next_safe_slice": "run_explicit_grokfast_fooddb_packet_live_diagnostic"},
            },
            "fooddb_status_packet_inspection": {
                "summary": {"next_safe_slice": "inspect_contract_handoff_status"},
            },
            "fooddb_status_packet_post_contract": {
                "summary": {
                    "manager_contract_handoff_status": "blocked_contract_handoff_alignment",
                    "manager_contract_owner_handoff_ready": False,
                },
                "integration_status": {
                    "manager_contract_selected_next_step": "inspect_contract_handoff_status"
                },
            },
        },
    )

    assert manifest["manager_contract_handoff_status"] == "blocked_contract_handoff_alignment"
    assert manifest["manager_contract_handoff_ready"] is False
    assert manifest["manager_contract_selected_next_step"] == "inspect_contract_handoff_status"
    assert manifest["next_recommended_slice"] == "repair_artifact_alignment_required"


def test_fooddb_live_diagnostic_bundle_records_required_artifact_refs(
    tmp_path: Path,
) -> None:
    main(["--output-dir", str(tmp_path)])

    manifest = read_json_artifact(
        tmp_path / "accurate_intake_fooddb_live_diagnostic_bundle_manifest.json"
    )
    required_refs = {
        "retrieval_eval_wall",
        "approved_packet_ready_artifact",
        "real_manager_e2e",
        "fooddb_status_packet",
        "manager_packet_smoke",
        "index_backend_parity",
        "case_matrix",
        "preflight",
        "router_readiness",
        "live_runner_readiness",
        "diagnostic",
        "report",
        "manager_contract_probe",
        "manager_contract_repair_pack",
        "manager_contract_handoff",
        "manager_contract_handoff_inspection",
        "fooddb_live_failure_taxonomy_inspection",
        "fooddb_status_packet_inspection",
        "fooddb_status_packet_post_contract",
    }

    assert required_refs.issubset(set(manifest["artifacts"]))
    for key in required_refs:
        assert Path(manifest["artifacts"][key]).exists()


def test_fooddb_live_diagnostic_bundle_creates_missing_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "nested" / "bundle"

    exit_code = main(["--output-dir", str(output_dir)])

    assert exit_code == 0
    assert (
        output_dir / "accurate_intake_fooddb_live_diagnostic_bundle_manifest.json"
    ).exists()


def test_fooddb_live_diagnostic_bundle_uses_configured_small_anchor_store(
    tmp_path: Path,
) -> None:
    configured_store = tmp_path / "custom_small_anchor_store.json"
    configured_store.write_text("{}", encoding="utf-8")
    captured: dict[str, Any] = {}

    class _DummyIndex:
        def load_records(self) -> tuple[object, ...]:
            return ()

    def _fake_from_path(path: Path) -> _DummyIndex:
        captured["path"] = path
        return _DummyIndex()

    def _fake_build_retrieval_eval_wall(*, retrieval_records: object) -> dict[str, Any]:
        return {
            "artifact_type": "accurate_intake_retrieval_eval_wall_v1",
            "summary": {
                "fail_count": 0,
                "next_required_slice": "grokfast_fooddb_packet_live_diagnostic",
                "websearch_runtime_truth_allowed_count": 0,
            },
            "live_provider_used": False,
            "live_websearch_used": False,
            "readiness_claimed": False,
        }

    def _fake_build_manager_packet_smoke(
        *,
        retrieval_records: object,
        approved_packet_ready_artifact: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        assert approved_packet_ready_artifact is not None
        assert approved_packet_ready_artifact["summary"]["selection_profile"] == "full_current_shell"
        return {
            "artifact_type": "accurate_intake_fooddb_manager_packet_smoke",
            "summary": {
                "case_count": 5,
                "compact_packet_pass_count": 5,
                "approved_packet_ready_case_count": 1000,
                "raw_source_rows_included": False,
                "candidate_only_records_included": False,
                "full_fooddb_included": False,
            },
            "runtime_truth_changed": False,
            "runtime_mutation_attempted": False,
            "live_provider_used": False,
            "manager_context_changed": False,
            "packetizer_format_changed": False,
            "readiness_claimed": False,
            "approved_packet_ready_artifact_ref": {
                "selection_profile": "full_current_shell",
                "packet_ready_item_count": 1000,
            },
        }

    def _fake_build_index_backend_parity(*, local_index: object, sqlite_db_path: Path) -> dict[str, Any]:
        return {
            "artifact_type": "accurate_intake_fooddb_index_backend_parity_v1",
            "status": "pass",
            "summary": {
                "fail_count": 0,
                "backend_count": 3,
                "backend_labels": ["local_json", "sqlite_fts", "supabase_rows"],
            },
            "cases": [],
            "next_required_slice": "grokfast_fooddb_packet_live_diagnostic",
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_changed": False,
            "packetizer_format_changed": False,
            "live_provider_used": False,
            "live_websearch_used": False,
            "readiness_claimed": False,
        }

    def _fake_build_real_manager_e2e(
        *,
        approved_packet_ready_artifact: dict[str, Any],
        semantic_small_anchor_records: object | None = None,
    ) -> dict[str, Any]:
        assert approved_packet_ready_artifact["summary"]["selection_profile"] == "full_current_shell"
        return {
            "artifact_type": "accurate_intake_fooddb_real_manager_e2e",
            "status": "pass",
            "summary": {
                "case_count": 8,
                "pass_count": 8,
            },
            "live_provider_used": False,
            "runtime_truth_changed": False,
            "runtime_mutation_attempted": False,
        }

    def _fake_case_matrix() -> dict[str, Any]:
        return {
            "artifact_type": "accurate_intake_fooddb_grokfast_packet_live_diagnostic_case_matrix",
            "status": "pass",
            "plan_only": True,
            "live_provider_invoked": False,
            "websearch_invoked": False,
            "shared_contract_changed": False,
            "non_claims": [
                "not_full_self_use_gate",
                "not_websearch_exact_card_gate",
                "not_final_response_quality_gate",
                "not_production_readiness",
                "not_private_self_use_approval",
                "not_kimi_activation",
                "not_runtime_mutation_gate",
            ],
            "summary": {
                "case_count": 8,
                "modifier_guard_cases": 2,
                "bare_basket_cases": 1,
                "listed_basket_cases": 1,
                "query_only_cases": 1,
                "macro_hidden_cases": 1,
                "websearch_cases": 0,
                "exact_card_cases": 1,
            },
            "cases": [],
        }

    def _fake_status_packet(
        *,
        small_anchor_payload: dict[str, Any],
        tfda_source_payload: dict[str, Any],
        exact_card_payload: dict[str, Any],
        contract_handoff_artifact: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
            "summary": {
                "manager_fooddb_packet_seam_gate_status": "pass",
                "manager_contract_handoff_status": (
                    "not_run" if contract_handoff_artifact is None else "insufficient_contract_handoff_evidence"
                ),
                "manager_contract_owner_handoff_ready": False,
            },
            "next_required_slices": (
                ["grokfast_fooddb_packet_live_diagnostic"]
                if contract_handoff_artifact is None
                else ["inspect_contract_handoff_status"]
            ),
            "live_provider_used": False,
            "live_websearch_used": False,
            "readiness_claimed": False,
            "runtime_truth_changed": False,
        }

    with (
        patch(
            "scripts.run_accurate_intake_fooddb_live_diagnostic_bundle.LocalSmallAnchorFoodEvidenceIndex.from_path",
            side_effect=_fake_from_path,
        ),
        patch(
            "scripts.run_accurate_intake_fooddb_live_diagnostic_bundle.build_retrieval_eval_wall",
            side_effect=_fake_build_retrieval_eval_wall,
        ),
        patch(
            "scripts.run_accurate_intake_fooddb_live_diagnostic_bundle.build_fooddb_manager_packet_smoke",
            side_effect=_fake_build_manager_packet_smoke,
        ),
        patch(
            "scripts.run_accurate_intake_fooddb_live_diagnostic_bundle._build_index_backend_parity",
            side_effect=_fake_build_index_backend_parity,
        ),
        patch(
            "scripts.run_accurate_intake_fooddb_live_diagnostic_bundle.build_fooddb_real_manager_e2e",
            side_effect=_fake_build_real_manager_e2e,
        ),
        patch(
            "scripts.run_accurate_intake_fooddb_live_diagnostic_bundle.build_fooddb_grokfast_live_diagnostic_case_matrix_artifact",
            side_effect=_fake_case_matrix,
        ),
        patch(
            "scripts.run_accurate_intake_fooddb_live_diagnostic_bundle.build_fooddb_evidence_status_packet",
            side_effect=_fake_status_packet,
        ),
    ):
        _build_pre_provider_artifacts(
            paths=_artifact_paths(tmp_path),
            source_payloads={
                "small_anchor_payload": {},
                "tfda_source_payload": {},
                "exact_card_payload": {},
            },
            small_anchor_store_path=configured_store,
        )

    assert captured["path"] == configured_store
