from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_post_extract_lane_status_packet import (
    build_websearch_post_extract_lane_status_packet,
)


def _extract_report(*, status: str = "trace_only_extract_canary_clean") -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_live_extract_canary_report_v1",
        "status": status,
        "classification": "diagnostic_report_only",
        "claim_scope": "websearch_live_extract_canary_report_without_runtime_activation",
        "selected_option": (
            "trace_only_extract_canary_continues"
            if status == "trace_only_extract_canary_clean"
            else "no_live_extract_seam"
        ),
        "extract_port_used": status == "trace_only_extract_canary_clean",
        "live_extract_used": True,
        "live_websearch_used": False,
        "live_provider_used": False,
        "runtime_truth_changed": False,
        "websearch_runtime_truth_allowed": False,
        "runtime_mutation_allowed": False,
        "readiness_claimed": False,
        "runtime_web_activation_approved": False,
        "runtime_web_activation_recommended": False,
        "ready_for_runtime_truth": False,
        "ready_for_runtime_mutation": False,
        "requires_owner_decision": False,
        "input_integrity": {"passed": True, "blockers": []},
        "evidence_summary": {
            "canary_status": "pass",
            "case_count": 1 if status == "trace_only_extract_canary_clean" else 0,
            "pass_count": 1 if status == "trace_only_extract_canary_clean" else 0,
            "failure_count": 0,
            "summary_fail_count": 0,
            "input_blocker_count": 0,
            "blockers": [],
            "extract_port_used": status == "trace_only_extract_canary_clean",
            "live_extract_used": True,
            "live_websearch_used": False,
        },
        "decision_boundary": {
            "trace_extract_canary_is_runtime_activation_evidence": False,
            "accepted_extract_rows_are_exact_truth": False,
            "runtime_web_exact_lane_requires_new_slice": True,
            "mutation_allowed": False,
            "product_readiness_claim_allowed": False,
        },
        "next_required_slice": (
            "websearch_live_extract_observation_or_exact_lane_decision"
            if status == "trace_only_extract_canary_clean"
            else "inspect_websearch_live_extract_canary_blockers"
        ),
    }


def test_post_extract_lane_status_clears_for_exact_card_candidate_planning_only() -> None:
    packet = build_websearch_post_extract_lane_status_packet(
        extract_canary_report=_extract_report()
    )

    assert packet["artifact_type"] == "accurate_intake_websearch_post_extract_lane_status_packet_v1"
    assert packet["status"] == "clear_for_exact_card_candidate_planning"
    assert packet["classification"] == "deterministic_websearch_post_extract_status_only"
    assert packet["runtime_truth_changed"] is False
    assert packet["runtime_mutation_allowed"] is False
    assert packet["websearch_runtime_truth_allowed"] is False
    assert packet["runtime_web_activation_approved"] is False
    assert packet["runtime_web_activation_recommended"] is False
    assert packet["readiness_claimed"] is False
    assert packet["summary"]["extract_report_status"] == "trace_only_extract_canary_clean"
    assert packet["summary"]["live_extract_used"] is True
    assert packet["next_required_slices"] == [
        "websearch_exact_card_candidate_planning_after_live_extract"
    ]


def test_post_extract_lane_status_blocks_without_clean_extract_report() -> None:
    packet = build_websearch_post_extract_lane_status_packet(
        extract_canary_report=_extract_report(status="blocked")
    )

    assert packet["status"] == "blocked_on_live_extract_report"
    assert packet["next_required_slices"] == ["inspect_websearch_live_extract_canary_blockers"]
    assert "extract_report_not_clean:blocked" in packet["upstream_gate"]["blockers"]


def test_post_extract_lane_status_blocks_report_integrity_failures() -> None:
    report = _extract_report()
    report["input_integrity"]["passed"] = False
    report["input_integrity"]["blockers"] = ["row_websearch_runtime_truth_allowed"]

    packet = build_websearch_post_extract_lane_status_packet(extract_canary_report=report)

    assert packet["status"] == "blocked_on_live_extract_report"
    assert (
        "extract_report_input_integrity:row_websearch_runtime_truth_allowed"
        in packet["upstream_gate"]["blockers"]
    )
    assert packet["runtime_web_activation_approved"] is False


def test_post_extract_lane_status_blocks_runtime_truth_or_activation_overclaims() -> None:
    expected = {
        "live_websearch_used": "extract_report_used_live_websearch",
        "source_live_websearch_used": "extract_report_used_source_live_websearch",
        "live_provider_used": "extract_report_used_live_provider",
        "runtime_truth_changed": "extract_report_changed_runtime_truth",
        "mutation_changed": "extract_report_changed_mutation",
        "websearch_runtime_truth_allowed": "extract_report_allowed_websearch_runtime_truth",
        "runtime_mutation_allowed": "extract_report_allowed_runtime_mutation",
        "runtime_web_activation_approved": "extract_report_approved_runtime_web_activation",
        "runtime_web_activation_recommended": (
            "extract_report_recommended_runtime_web_activation"
        ),
        "ready_for_runtime_truth": "extract_report_claimed_ready_for_runtime_truth",
        "ready_for_runtime_mutation": "extract_report_claimed_ready_for_runtime_mutation",
        "readiness_claimed": "extract_report_claimed_readiness",
        "shared_contract_changed": "extract_report_changed_shared_contract",
        "nutrition_evidence_store_port_changed": (
            "extract_report_changed_nutrition_evidence_store_port"
        ),
        "manager_context_changed": "extract_report_changed_manager_context",
        "packetizer_format_changed": "extract_report_changed_packetizer_format",
        "basket_semantics_changed": "extract_report_changed_basket_semantics",
    }
    for key, blocker in expected.items():
        report = _extract_report()
        report[key] = True
        packet = build_websearch_post_extract_lane_status_packet(
            extract_canary_report=report
        )
        assert packet["status"] == "blocked_on_live_extract_report"
        assert blocker in packet["upstream_gate"]["blockers"]


def test_post_extract_lane_status_blocks_boundary_drift() -> None:
    for key, blocker in (
        (
            "trace_extract_canary_is_runtime_activation_evidence",
            "decision_boundary_claimed_trace_as_runtime_activation",
        ),
        (
            "accepted_extract_rows_are_exact_truth",
            "decision_boundary_claimed_extract_rows_as_exact_truth",
        ),
        ("mutation_allowed", "decision_boundary_allowed_mutation"),
        ("product_readiness_claim_allowed", "decision_boundary_allowed_readiness_claim"),
    ):
        report = _extract_report()
        report["decision_boundary"][key] = True
        packet = build_websearch_post_extract_lane_status_packet(
            extract_canary_report=report
        )
        assert packet["status"] == "blocked_on_live_extract_report"
        assert blocker in packet["upstream_gate"]["blockers"]


def test_post_extract_lane_status_rejects_unexpected_artifact_type() -> None:
    try:
        build_websearch_post_extract_lane_status_packet(
            extract_canary_report={"artifact_type": "wrong"}
        )
    except ValueError as exc:
        assert "unsupported_post_extract_status_report" in str(exc)
    else:
        raise AssertionError("unexpected extract report type must fail")


def test_post_extract_lane_status_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_post_extract_lane_status_packet import (
        main,
    )

    report_path = tmp_path / "extract_report.json"
    output = tmp_path / "post_extract_status.json"
    write_json_artifact(report_path, _extract_report())

    assert main(["--extract-canary-report", str(report_path), "--output", str(output)]) == 0

    packet = read_json_artifact(output)
    assert (
        packet["artifact_type"]
        == "accurate_intake_websearch_post_extract_lane_status_packet_v1"
    )
    assert packet["status"] == "clear_for_exact_card_candidate_planning"


def test_post_extract_lane_status_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_post_extract_lane_status_packet.py"),
        Path("scripts/build_accurate_intake_websearch_post_extract_lane_status_packet.py"),
    ]
    forbidden = [
        "Tavily",
        "tavily",
        "OpenAI",
        "openai",
        "BuilderSpaceAdapter",
        "requests.",
        "httpx.",
        "ManagerContextPacket",
        "NutritionEvidenceStorePort",
        "PacketReadyAnchor",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
