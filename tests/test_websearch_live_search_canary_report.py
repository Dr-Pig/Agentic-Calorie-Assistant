from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_live_search_canary_report import (
    build_websearch_live_search_canary_report,
)


def _canary_artifact(*, status: str = "pass", case_status: str = "pass") -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_live_search_diagnostic_canary_v1",
        "status": status,
        "classification": "diagnostic_canary_harness_only",
        "claim_scope": "websearch_live_search_diagnostic_canary_without_runtime_truth",
        "blockers": [] if status == "pass" else ["live_search_permission_required"],
        "live_permission_granted": status == "pass",
        "search_port_used": status == "pass",
        "extract_port_used": status == "pass",
        "live_provider_used": False,
        "live_websearch_used": False,
        "runtime_truth_changed": False,
        "websearch_runtime_truth_allowed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "readiness_claimed": False,
        "ready_for_runtime_truth": False,
        "summary": {
            "case_count": 1 if status == "pass" else 0,
            "pass_count": 1 if status == "pass" and case_status == "pass" else 0,
            "fail_count": 0 if status == "pass" and case_status == "pass" else 1,
            "search_port_call_count": 1 if status == "pass" else 0,
            "extract_port_call_count": 1 if status == "pass" else 0,
            "runtime_truth_allowed_count": 0,
        },
        "cases": [
            {
                "case_id": "websearch_exact_brand_fixture_canary",
                "status": case_status,
                "runtime_truth_allowed": False,
                "runtime_mutation_allowed": False,
                "exact_card_created": False,
                "trace": {
                    "attempted": True,
                    "accepted_extract_packet_id": "pkt_web_extract_fixture",
                    "rejected_web_candidates_used_as_evidence": False,
                    "truth_boundary": {
                        "trace_only": True,
                        "web_candidate_truth_authority": False,
                        "accepted_extract_packet_truth_authority": False,
                        "runtime_web_activation_recommended": False,
                    },
                },
            }
        ]
        if status == "pass"
        else [],
    }


def test_websearch_live_search_canary_report_keeps_clean_canary_trace_only() -> None:
    report = build_websearch_live_search_canary_report(
        canary_artifact=_canary_artifact()
    )

    assert report["artifact_type"] == "accurate_intake_websearch_live_search_canary_report_v1"
    assert report["status"] == "trace_only_canary_clean"
    assert report["selected_option"] == "trace_only_canary_continues"
    assert report["runtime_web_activation_approved"] is False
    assert report["runtime_web_activation_recommended"] is False
    assert report["ready_for_runtime_truth"] is False
    assert report["requires_owner_decision"] is False
    assert report["next_required_slice"] == "websearch_trace_only_canary_observation_or_exact_lane_decision"
    assert report["evidence_summary"]["case_count"] == 1
    assert report["evidence_summary"]["failure_count"] == 0


def test_websearch_live_search_canary_report_blocks_failed_or_not_invoked_canary() -> None:
    for artifact in (
        _canary_artifact(status="blocked"),
        _canary_artifact(status="pass", case_status="fail"),
    ):
        report = build_websearch_live_search_canary_report(canary_artifact=artifact)
        assert report["status"] == "blocked"
        assert report["selected_option"] == "no_live_search_seam"
        assert report["runtime_web_activation_approved"] is False
        assert report["next_required_slice"] == "inspect_websearch_live_search_canary_blockers"


def test_websearch_live_search_canary_report_blocks_overclaiming_or_truthy_inputs() -> None:
    expected_blockers = {
        "live_provider_used": "input_used_live_provider",
        "runtime_truth_changed": "input_runtime_truth_changed",
        "websearch_runtime_truth_allowed": "input_websearch_runtime_truth_allowed",
        "runtime_mutation_allowed": "input_runtime_mutation_allowed",
        "mutation_changed": "input_mutation_changed",
        "runtime_web_activation_approved": "input_runtime_web_activation_approved",
        "runtime_web_activation_recommended": "input_runtime_web_activation_recommended",
        "shared_contract_changed": "input_shared_contract_changed",
        "manager_context_changed": "input_manager_context_changed",
        "manager_context_packet_changed": "input_manager_context_packet_changed",
        "manager_context_packet_schema_changed": "input_manager_context_packet_schema_changed",
        "packetizer_format_changed": "input_packetizer_format_changed",
        "packetizer_changed": "input_packetizer_changed",
        "readiness_claimed": "input_readiness_claimed",
        "ready_for_runtime_truth": "input_ready_for_runtime_truth",
        "ready_for_runtime_mutation": "input_ready_for_runtime_mutation",
        "nutrition_evidence_store_port_changed": "input_nutrition_evidence_store_port_changed",
        "basket_semantics_changed": "input_basket_semantics_changed",
        "product_loop_activated": "input_product_loop_activated",
        "product_loop_integration_claimed": "input_product_loop_integration_claimed",
        "ce_activated": "input_ce_activated",
        "context_engineering_changed": "input_context_engineering_changed",
        "webshell_activated": "input_webshell_activated",
        "webshell_changed": "input_webshell_changed",
    }
    for key, blocker in expected_blockers.items():
        artifact = _canary_artifact()
        artifact[key] = True
        report = build_websearch_live_search_canary_report(canary_artifact=artifact)
        assert report["status"] == "blocked"
        assert blocker in report["input_integrity"]["blockers"]
        assert report["runtime_web_activation_approved"] is False


def test_websearch_live_search_canary_report_blocks_input_blockers_even_when_status_pass() -> None:
    artifact = _canary_artifact()
    artifact["blockers"] = ["source_license_unknown"]

    report = build_websearch_live_search_canary_report(canary_artifact=artifact)

    assert report["status"] == "blocked"
    assert report["selected_option"] == "no_live_search_seam"
    assert report["evidence_summary"]["input_blocker_count"] == 1
    assert report["runtime_web_activation_approved"] is False
    assert report["next_required_slice"] == "inspect_websearch_live_search_canary_blockers"


def test_websearch_live_search_canary_report_blocks_summary_fail_count_even_when_cases_pass() -> None:
    artifact = _canary_artifact()
    artifact["summary"]["fail_count"] = 1

    report = build_websearch_live_search_canary_report(canary_artifact=artifact)

    assert report["status"] == "blocked"
    assert report["selected_option"] == "no_live_search_seam"
    assert report["evidence_summary"]["summary_fail_count"] == 1
    assert report["runtime_web_activation_recommended"] is False


def test_websearch_live_search_canary_report_blocks_live_websearch_from_trace_only_path() -> None:
    artifact = _canary_artifact()
    artifact["live_websearch_used"] = True

    report = build_websearch_live_search_canary_report(canary_artifact=artifact)

    assert report["status"] == "blocked"
    assert "input_used_external_live_websearch" in report["input_integrity"]["blockers"]
    assert report["selected_option"] == "no_live_search_seam"


def test_websearch_live_search_canary_report_blocks_truth_boundary_drift() -> None:
    artifact = _canary_artifact()
    artifact["cases"][0]["trace"]["truth_boundary"]["accepted_extract_packet_truth_authority"] = True

    report = build_websearch_live_search_canary_report(canary_artifact=artifact)

    assert report["status"] == "blocked"
    assert "case_accepted_extract_packet_claimed_truth" in report["input_integrity"]["blockers"]


def test_websearch_live_search_canary_report_rejects_unexpected_artifact_type() -> None:
    try:
        build_websearch_live_search_canary_report(canary_artifact={"artifact_type": "wrong"})
    except ValueError as exc:
        assert "unsupported_websearch_live_search_canary_artifact" in str(exc)
    else:
        raise AssertionError("unexpected canary artifact type must fail")


def test_websearch_live_search_canary_report_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_live_search_canary_report import main

    canary_path = tmp_path / "canary.json"
    output = tmp_path / "report.json"
    write_json_artifact(canary_path, _canary_artifact())

    assert (
        main(
            [
                "--canary-artifact",
                str(canary_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    report = read_json_artifact(output)
    assert report["artifact_type"] == "accurate_intake_websearch_live_search_canary_report_v1"
    assert report["status"] == "trace_only_canary_clean"
    assert report["readiness_claimed"] is False


def test_websearch_live_search_canary_report_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_live_search_canary_report.py"),
        Path("scripts/build_accurate_intake_websearch_live_search_canary_report.py"),
    ]
    forbidden = [
        "Tavily",
        "BuilderSpaceAdapter",
        "requests.",
        "httpx.",
        "ManagerContextPacket",
        "NutritionEvidenceStorePort",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
