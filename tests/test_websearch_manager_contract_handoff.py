from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_manager_contract_handoff import (
    build_websearch_manager_contract_handoff,
)


def _live_report(*, seam_status: str = "provider_contract_blocked") -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_live_diagnostic_report",
        "seam_status": seam_status,
        "source_live_provider_used": True,
        "source_live_websearch_used": False,
        "next_recommended_slice": "narrow_grokfast_websearch_manager_contract_probe",
    }


def _probe(*, contract_failure_detected: bool = True) -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_manager_contract_probe",
        "status": "diagnostic_fail" if contract_failure_detected else "pass",
        "contract_failure_detected": contract_failure_detected,
        "summary": {
            "case_count": 2,
            "fail_count": 2 if contract_failure_detected else 0,
            "aggregate_missing_required_fields": {"intent": 2}
            if contract_failure_detected
            else {},
            "next_recommended_slice": "narrow_prompt_schema_intent_alias_probe",
        },
    }


def _repair_pack(
    *,
    next_recommended_slice: str = "tighten_websearch_manager_contract_prompt_or_transport",
) -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_manager_contract_repair_pack",
        "next_recommended_slice": next_recommended_slice,
        "summary": {
            "case_count": 2,
            "alias_hint_counts": {"intent": 2},
            "shape_pattern_counts": {"intent_type_present_intent_missing": 2},
        },
    }


def test_websearch_manager_contract_handoff_marks_owner_ready_for_provider_contract_failures() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(),
        contract_probe_artifact=_probe(),
        repair_pack_artifact=_repair_pack(),
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_manager_contract_handoff_v1"
    assert artifact["status"] == "ready_for_manager_contract_owner"
    assert artifact["selected_next_step"] == "tighten_websearch_manager_contract_prompt_or_transport"
    assert artifact["handoff_ready"] is True
    assert artifact["downstream_owner"] == "manager_runtime_contract"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["shared_contract_changed"] is False
    assert artifact["summary"]["alignment_blocker_count"] == 0


def test_websearch_manager_contract_handoff_blocks_alignment_gaps() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(),
        contract_probe_artifact=_probe(),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert artifact["selected_next_step"] == "repair_artifact_alignment_required"
    assert "repair_pack_empty_for_contract_failure" in artifact["alignment_blockers"]
    assert "probe_repair_case_count_mismatch" in artifact["alignment_blockers"]


def test_websearch_manager_contract_handoff_detects_live_probe_status_mismatch() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(),
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "live_report_probe_contract_status_mismatch" in artifact["alignment_blockers"]


def test_websearch_manager_contract_handoff_returns_to_websearch_on_candidate_boundary_block() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(seam_status="candidate_boundary_blocked"),
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
    )

    assert artifact["status"] == "return_to_websearch_packet_boundary"
    assert artifact["selected_next_step"] == "narrow_websearch_packet_boundary_or_prompt_probe"
    assert artifact["handoff_ready"] is False


def test_websearch_manager_contract_handoff_blocks_live_pass_when_probe_still_fails() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(seam_status="live_diagnostic_pass"),
        contract_probe_artifact=_probe(),
        repair_pack_artifact=_repair_pack(),
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "live_pass_with_contract_failure_detected" in artifact["alignment_blockers"]
    assert artifact["handoff_ready"] is False


def test_websearch_manager_contract_handoff_allows_passed_contract() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(seam_status="live_diagnostic_pass"),
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
    )

    assert artifact["status"] == "websearch_contract_unblocked"
    assert artifact["selected_next_step"] == "websearch_candidate_pipeline_narrow_expansion"
    assert artifact["handoff_ready"] is False


def test_websearch_manager_contract_handoff_sanitizes_against_raw_payload_leakage() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report={
            **_live_report(),
            "raw_response_excerpt": "forbidden",
            "parsed_object": {"food_name": "invented"},
        },
        contract_probe_artifact={
            **_probe(),
            "cases": [{"raw_content_excerpt": "forbidden"}],
        },
        repair_pack_artifact={
            **_repair_pack(),
            "cases": [{"present_top_level_fields": ["intent_type"], "food_name": "invented"}],
        },
    )

    serialized = str(artifact)
    assert "raw_response_excerpt" not in serialized
    assert "parsed_object" not in serialized
    assert "food_name" not in serialized
    assert "invented" not in serialized
    assert "forbidden" not in serialized


def test_websearch_manager_contract_handoff_whitelists_upstream_summaries() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report={
            **_live_report(),
            "next_recommended_slice": "raw_response_excerpt forbidden",
            "source_live_provider_used": "raw_response_excerpt forbidden",
            "source_live_websearch_used": "raw_response_excerpt forbidden",
        },
        contract_probe_artifact={
            **_probe(),
            "summary": {
                "case_count": 2,
                "fail_count": 2,
                "aggregate_missing_required_fields": {
                    "intent": 2,
                    "raw_response_excerpt forbidden": 1,
                },
                "next_recommended_slice": "raw_response_excerpt forbidden",
            },
        },
        repair_pack_artifact={
            **_repair_pack(next_recommended_slice="raw_response_excerpt forbidden"),
            "summary": {
                "case_count": 2,
                "alias_hint_counts": {
                    "intent": 2,
                    "raw_response_excerpt forbidden": 1,
                },
                "shape_pattern_counts": {
                    "intent_type_present_intent_missing": 2,
                    "raw_response_excerpt forbidden": 1,
                },
            },
        },
    )

    serialized = str(artifact)
    assert "raw_response_excerpt" not in serialized
    assert "forbidden" not in serialized
    assert artifact["summary"]["aggregate_missing_required_fields"] == {"intent": 2}
    assert artifact["summary"]["alias_hint_counts"] == {"intent": 2}
    assert artifact["artifact_chain"]["live_diagnostic_report"]["next_recommended_slice"] is None
    assert artifact["artifact_chain"]["live_diagnostic_report"]["source_live_provider_used"] is False
    assert artifact["artifact_chain"]["live_diagnostic_report"]["source_live_websearch_used"] is False
    assert artifact["artifact_chain"]["contract_probe"]["next_recommended_slice"] is None


def test_websearch_manager_contract_handoff_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_manager_contract_handoff import main

    live_path = tmp_path / "live.json"
    probe_path = tmp_path / "probe.json"
    repair_path = tmp_path / "repair.json"
    output_path = tmp_path / "handoff.json"
    write_json_artifact(live_path, _live_report())
    write_json_artifact(probe_path, _probe())
    write_json_artifact(repair_path, _repair_pack())

    assert (
        main(
            [
                "--live-diagnostic-report",
                str(live_path),
                "--contract-probe-artifact",
                str(probe_path),
                "--repair-pack-artifact",
                str(repair_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output_path)
    assert artifact["status"] == "ready_for_manager_contract_owner"
    assert artifact["handoff_ready"] is True


def test_websearch_manager_contract_handoff_rejects_unexpected_sources() -> None:
    try:
        build_websearch_manager_contract_handoff(
            live_diagnostic_report={"artifact_type": "wrong"},
            contract_probe_artifact=_probe(),
            repair_pack_artifact=_repair_pack(),
        )
    except ValueError as exc:
        assert "unsupported_websearch_manager_contract_handoff_live_report" in str(exc)
    else:
        raise AssertionError("unexpected live report type must fail")

    try:
        build_websearch_manager_contract_handoff(
            live_diagnostic_report=_live_report(),
            contract_probe_artifact={"artifact_type": "wrong"},
            repair_pack_artifact=_repair_pack(),
        )
    except ValueError as exc:
        assert "unsupported_websearch_manager_contract_handoff_contract_probe" in str(exc)
    else:
        raise AssertionError("unexpected probe artifact type must fail")

    try:
        build_websearch_manager_contract_handoff(
            live_diagnostic_report=_live_report(),
            contract_probe_artifact=_probe(),
            repair_pack_artifact={"artifact_type": "wrong"},
        )
    except ValueError as exc:
        assert "unsupported_websearch_manager_contract_handoff_repair_pack" in str(exc)
    else:
        raise AssertionError("unexpected repair artifact type must fail")


def test_websearch_manager_contract_handoff_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_manager_contract_handoff.py"),
        Path("scripts/build_accurate_intake_websearch_manager_contract_handoff.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "Tavily",
        "tavily",
        "requests.",
        "httpx.",
        "allow_live",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
