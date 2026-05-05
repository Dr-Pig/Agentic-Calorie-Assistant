from __future__ import annotations

from pathlib import Path

from app.nutrition.application.fooddb_manager_contract_handoff import (
    build_fooddb_manager_contract_handoff,
)


def _live_report(*, seam_status: str = "provider_contract_blocked") -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_live_diagnostic_report",
        "seam_status": seam_status,
        "source_live_provider_used": True,
        "next_recommended_slice": "narrow_grokfast_fooddb_manager_contract_probe",
    }


def _probe(*, contract_failure_detected: bool = True) -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_manager_contract_probe",
        "contract_failure_detected": contract_failure_detected,
        "next_recommended_slice": "tighten_fooddb_manager_contract_prompt_or_transport",
        "summary": {
            "case_count": 5,
            "aggregate_missing_required_fields": {"intent": 5},
        },
    }


def _repair_pack(*, next_recommended_slice: str = "tighten_fooddb_manager_contract_prompt_or_transport") -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_manager_contract_repair_pack",
        "next_recommended_slice": next_recommended_slice,
        "summary": {
            "case_count": 5,
            "alias_hint_counts": {"intent": 5},
            "probe_match_status_counts": {"matched_probe_case": 5},
            "trace_status_counts": {"trace_present": 5},
        },
    }


def test_fooddb_manager_contract_handoff_marks_owner_ready_for_provider_contract_failures() -> None:
    artifact = build_fooddb_manager_contract_handoff(
        live_diagnostic_report=_live_report(),
        contract_probe_artifact=_probe(),
        repair_pack_artifact=_repair_pack(),
    )

    assert artifact["artifact_type"] == "accurate_intake_fooddb_manager_contract_handoff_v1"
    assert artifact["status"] == "ready_for_manager_contract_owner"
    assert artifact["selected_next_step"] == "tighten_fooddb_manager_contract_prompt_or_transport"
    assert artifact["handoff_ready"] is True
    assert artifact["downstream_owner"] == "manager_runtime_contract"
    assert artifact["summary"]["alignment_blocker_count"] == 0


def test_fooddb_manager_contract_handoff_blocks_alignment_gaps() -> None:
    artifact = build_fooddb_manager_contract_handoff(
        live_diagnostic_report=_live_report(),
        contract_probe_artifact=_probe(),
        repair_pack_artifact=_repair_pack(next_recommended_slice="repair_artifact_alignment_required"),
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert artifact["selected_next_step"] == "repair_artifact_alignment_required"
    assert artifact["handoff_ready"] is False
    assert "repair_pack_alignment_required" in artifact["alignment_blockers"]


def test_fooddb_manager_contract_handoff_detects_live_probe_status_mismatch() -> None:
    artifact = build_fooddb_manager_contract_handoff(
        live_diagnostic_report=_live_report(seam_status="provider_contract_blocked"),
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact=_repair_pack(),
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "live_report_probe_contract_status_mismatch" in artifact["alignment_blockers"]


def test_fooddb_manager_contract_handoff_returns_to_fooddb_on_packet_boundary_block() -> None:
    artifact = build_fooddb_manager_contract_handoff(
        live_diagnostic_report=_live_report(seam_status="packet_boundary_blocked"),
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact=_repair_pack(),
    )

    assert artifact["status"] == "return_to_fooddb_packet_boundary"
    assert artifact["selected_next_step"] == "narrow_fooddb_packet_boundary_or_prompt_probe"
    assert artifact["handoff_ready"] is False


def test_fooddb_manager_contract_handoff_blocks_live_pass_when_probe_still_fails() -> None:
    artifact = build_fooddb_manager_contract_handoff(
        live_diagnostic_report=_live_report(seam_status="live_diagnostic_pass"),
        contract_probe_artifact=_probe(contract_failure_detected=True),
        repair_pack_artifact=_repair_pack(),
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "live_pass_with_contract_failure_detected" in artifact["alignment_blockers"]
    assert artifact["handoff_ready"] is False


def test_fooddb_manager_contract_handoff_blocks_stale_repair_pack_counts() -> None:
    artifact = build_fooddb_manager_contract_handoff(
        live_diagnostic_report=_live_report(),
        contract_probe_artifact=_probe(),
        repair_pack_artifact={
            **_repair_pack(),
            "summary": {
                "case_count": 0,
                "alias_hint_counts": {},
                "probe_match_status_counts": {},
                "trace_status_counts": {},
            },
        },
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "repair_pack_empty_for_contract_failure" in artifact["alignment_blockers"]
    assert "probe_repair_case_count_mismatch" in artifact["alignment_blockers"]
    assert artifact["handoff_ready"] is False


def test_fooddb_manager_contract_handoff_sanitizes_against_raw_payload_leakage() -> None:
    artifact = build_fooddb_manager_contract_handoff(
        live_diagnostic_report={
            **_live_report(),
            "raw_response_excerpt": "forbidden",
            "parsed_object": {"food_name": "珍奶"},
        },
        contract_probe_artifact={
            **_probe(),
            "cases": [{"raw_content_excerpt": "forbidden"}],
        },
        repair_pack_artifact={
            **_repair_pack(),
            "cases": [{"present_top_level_fields": ["intent_type"], "food_name": "珍奶"}],
        },
    )

    assert not _contains_key(artifact, "raw_response_excerpt")
    assert not _contains_key(artifact, "parsed_object")
    assert not _contains_key(artifact, "food_name")
    assert "forbidden" not in _scalar_values(artifact)
    assert "珍奶" not in _scalar_values(artifact)


def test_fooddb_manager_contract_handoff_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_fooddb_manager_contract_handoff import main

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


def test_fooddb_manager_contract_handoff_rejects_unexpected_sources() -> None:
    try:
        build_fooddb_manager_contract_handoff(
            live_diagnostic_report={"artifact_type": "wrong"},
            contract_probe_artifact=_probe(),
            repair_pack_artifact=_repair_pack(),
        )
    except ValueError as exc:
        assert "unsupported_fooddb_manager_contract_handoff_live_report" in str(exc)
    else:
        raise AssertionError("unexpected live report type must fail")

    try:
        build_fooddb_manager_contract_handoff(
            live_diagnostic_report=_live_report(),
            contract_probe_artifact={"artifact_type": "wrong"},
            repair_pack_artifact=_repair_pack(),
        )
    except ValueError as exc:
        assert "unsupported_fooddb_manager_contract_handoff_contract_probe" in str(exc)
    else:
        raise AssertionError("unexpected contract probe type must fail")

    try:
        build_fooddb_manager_contract_handoff(
            live_diagnostic_report=_live_report(),
            contract_probe_artifact=_probe(),
            repair_pack_artifact={"artifact_type": "wrong"},
        )
    except ValueError as exc:
        assert "unsupported_fooddb_manager_contract_handoff_repair_pack" in str(exc)
    else:
        raise AssertionError("unexpected repair pack type must fail")


def test_fooddb_manager_contract_handoff_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/fooddb_manager_contract_handoff.py"),
        Path("scripts/build_accurate_intake_fooddb_manager_contract_handoff.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "requests.",
        "httpx.",
        "allow_live",
        "Tavily",
        "tavily",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source


def _contains_key(value: object, target_key: str) -> bool:
    if isinstance(value, dict):
        return target_key in value or any(_contains_key(child, target_key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, target_key) for item in value)
    return False


def _scalar_values(value: object) -> set[str]:
    if isinstance(value, dict):
        return {item for child in value.values() for item in _scalar_values(child)}
    if isinstance(value, list):
        return {item for child in value for item in _scalar_values(child)}
    return {str(value)}
