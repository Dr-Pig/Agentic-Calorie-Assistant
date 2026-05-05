from __future__ import annotations

from pathlib import Path

from app.nutrition.application.grokfast_fooddb_diagnostic_preflight import (
    build_grokfast_fooddb_diagnostic_preflight,
    is_grokfast_fooddb_preflight_clear,
)


def _retrieval_eval_wall(*, fail_count: int = 0) -> dict:
    return {
        "artifact_type": "accurate_intake_retrieval_eval_wall_v1",
        "classification": "deterministic_retrieval_eval_wall_only",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "case_count": 9,
            "pass_count": 9 - fail_count,
            "fail_count": fail_count,
            "websearch_runtime_truth_allowed_count": 0,
            "next_required_slice": (
                "inspect_retrieval_eval_wall_failures"
                if fail_count
                else "grokfast_fooddb_packet_live_diagnostic"
            ),
        },
    }


def _fooddb_status(
    *,
    next_required_slices: list[str] | None = None,
    handoff_status: str = "not_run",
    handoff_ready: bool = False,
) -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_evidence_status_packet_v1",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "runtime_common_serving_anchor_count": 51,
            "listed_component_anchor_count": 30,
            "manager_fooddb_packet_seam_gate_status": "pass",
            "manager_contract_handoff_status": handoff_status,
            "manager_contract_owner_handoff_ready": handoff_ready,
        },
        "next_required_slices": next_required_slices
        or ["grokfast_fooddb_packet_live_diagnostic"],
    }


def _manager_packet_smoke(
    *,
    leak: bool = False,
    readiness_claimed: bool = False,
    runtime_mutation_attempted: bool = False,
) -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_manager_packet_smoke",
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": runtime_mutation_attempted,
        "live_provider_used": False,
        "manager_context_changed": False,
        "runtime_packetizer_contract_changed": False,
        "packetizer_format_changed": False,
        "readiness_claimed": readiness_claimed,
        "summary": {
            "case_count": 5,
            "compact_packet_pass_count": 5,
            "raw_source_rows_included": leak,
            "candidate_only_records_included": False,
            "full_fooddb_included": False,
        },
    }


def test_grokfast_fooddb_diagnostic_preflight_clears_only_when_all_upstream_gates_pass() -> None:
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
    )

    assert artifact["artifact_type"] == "accurate_intake_grokfast_fooddb_diagnostic_preflight_v1"
    assert artifact["status"] == "clear_for_grokfast_fooddb_packet_live_diagnostic"
    assert artifact["clear_to_run_live_diagnostic"] is True
    assert artifact["live_provider_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["next_required_slice"] == "grokfast_fooddb_packet_live_diagnostic"
    assert is_grokfast_fooddb_preflight_clear(artifact) is True


def test_grokfast_fooddb_diagnostic_preflight_blocks_retrieval_eval_failures() -> None:
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(fail_count=1),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["clear_to_run_live_diagnostic"] is False
    assert "retrieval_eval_wall_has_failures" in artifact["blockers"]
    assert artifact["next_required_slice"] == "inspect_grokfast_fooddb_preflight_blockers"


def test_grokfast_fooddb_diagnostic_preflight_blocks_manager_contract_handoff_ready() -> None:
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(
            next_required_slices=["await_manager_contract_owner_repair"],
            handoff_status="ready_for_manager_contract_owner",
            handoff_ready=True,
        ),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
    )

    assert artifact["status"] == "blocked"
    assert "fooddb_status_not_ready_for_grokfast_diagnostic" in artifact["blockers"]
    assert "manager_contract_owner_handoff_ready" in artifact["blockers"]
    assert artifact["summary"]["manager_contract_handoff_status"] == "ready_for_manager_contract_owner"


def test_grokfast_fooddb_diagnostic_preflight_blocks_noncompact_packet_smoke() -> None:
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(leak=True),
    )

    assert artifact["status"] == "blocked"
    assert "manager_packet_smoke_not_compact" in artifact["blockers"]
    assert is_grokfast_fooddb_preflight_clear(artifact) is False


def test_grokfast_fooddb_diagnostic_preflight_blocks_packet_overclaims() -> None:
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(
            readiness_claimed=True,
            runtime_mutation_attempted=True,
        ),
    )

    assert artifact["status"] == "blocked"
    assert "manager_packet_smoke_claimed_readiness" in artifact["blockers"]
    assert "manager_packet_smoke_attempted_mutation" in artifact["blockers"]


def test_grokfast_fooddb_preflight_clear_helper_rejects_forged_summary() -> None:
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
    )
    forged = {
        **artifact,
        "summary": {
            **artifact["summary"],
            "retrieval_eval_fail_count": 1,
        },
    }

    assert forged["status"] == "clear_for_grokfast_fooddb_packet_live_diagnostic"
    assert forged["clear_to_run_live_diagnostic"] is True
    assert forged["blockers"] == []
    assert is_grokfast_fooddb_preflight_clear(forged) is False


def test_grokfast_fooddb_diagnostic_preflight_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_grokfast_fooddb_diagnostic_preflight import main

    retrieval_path = tmp_path / "retrieval.json"
    fooddb_status_path = tmp_path / "fooddb_status.json"
    packet_path = tmp_path / "packet.json"
    output = tmp_path / "preflight.json"
    write_json_artifact(retrieval_path, _retrieval_eval_wall())
    write_json_artifact(fooddb_status_path, _fooddb_status())
    write_json_artifact(packet_path, _manager_packet_smoke())

    assert (
        main(
            [
                "--retrieval-eval-wall",
                str(retrieval_path),
                "--fooddb-status-packet",
                str(fooddb_status_path),
                "--manager-packet-smoke",
                str(packet_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert is_grokfast_fooddb_preflight_clear(artifact) is True


def test_grokfast_fooddb_packet_live_script_requires_clear_preflight(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_fooddb_packet_smoke import main

    packet_path = tmp_path / "packet.json"
    missing_preflight = tmp_path / "missing_preflight.json"
    output = tmp_path / "blocked_live.json"
    write_json_artifact(
        packet_path,
        {
            "artifact_type": "accurate_intake_fooddb_manager_packet_smoke",
            "cases": [],
        },
    )

    assert (
        main(
            [
                "--mode",
                "live",
                "--allow-live",
                "--packet-smoke",
                str(packet_path),
                "--preflight-artifact",
                str(missing_preflight),
                "--output",
                str(output),
            ]
        )
        == 2
    )
    artifact = read_json_artifact(output)
    assert artifact["status"] == "blocked"
    assert artifact["failure_family"] == "missing_clear_grokfast_fooddb_preflight"


def test_grokfast_fooddb_packet_live_script_rejects_forged_clear_preflight(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_fooddb_packet_smoke import main

    packet_path = tmp_path / "packet.json"
    preflight_path = tmp_path / "forged_preflight.json"
    output = tmp_path / "blocked_live.json"
    write_json_artifact(
        packet_path,
        {
            "artifact_type": "accurate_intake_fooddb_manager_packet_smoke",
            "cases": [],
        },
    )
    clear_artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
    )
    write_json_artifact(
        preflight_path,
        {
            **clear_artifact,
            "summary": {
                **clear_artifact["summary"],
                "manager_contract_owner_handoff_ready": True,
            },
        },
    )

    assert (
        main(
            [
                "--mode",
                "live",
                "--allow-live",
                "--packet-smoke",
                str(packet_path),
                "--preflight-artifact",
                str(preflight_path),
                "--output",
                str(output),
            ]
        )
        == 2
    )
    artifact = read_json_artifact(output)
    assert artifact["status"] == "blocked"
    assert artifact["failure_family"] == "grokfast_fooddb_preflight_not_clear"


def test_grokfast_fooddb_diagnostic_preflight_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/grokfast_fooddb_diagnostic_preflight.py"),
        Path("scripts/build_accurate_intake_grokfast_fooddb_diagnostic_preflight.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "requests.",
        "httpx.",
        "Tavily",
        "tavily",
        "allow_live",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
