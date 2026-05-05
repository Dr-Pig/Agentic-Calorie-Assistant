from __future__ import annotations

from pathlib import Path

from app.nutrition.application.grokfast_fooddb_diagnostic_preflight import (
    build_grokfast_fooddb_diagnostic_preflight,
    is_grokfast_fooddb_preflight_clear,
)
from app.nutrition.application.fooddb_grokfast_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS as REQUIRED_FOODDB_GROKFAST_CASE_IDS,
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


def _case_matrix(
    *,
    status: str = "pass",
    plan_only: bool = True,
    live_provider_invoked: bool = False,
    websearch_invoked: bool = False,
    case_count: int = 5,
) -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_grokfast_packet_live_diagnostic_case_matrix",
        "status": status,
        "plan_only": plan_only,
        "live_llm_invoked": False,
        "live_provider_invoked": live_provider_invoked,
        "websearch_invoked": websearch_invoked,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_packet_changed": False,
        "shared_contract_changed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
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
            "case_count": case_count,
            "modifier_guard_cases": 2,
            "bare_basket_cases": 1,
            "listed_basket_cases": 1,
            "websearch_cases": 0,
            "exact_card_cases": 0,
        },
        "cases": [{"case_id": case_id} for case_id in REQUIRED_FOODDB_GROKFAST_CASE_IDS],
    }


def test_grokfast_fooddb_diagnostic_preflight_clears_only_when_all_upstream_gates_pass() -> None:
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
        case_matrix_artifact=_case_matrix(),
    )

    assert artifact["artifact_type"] == "accurate_intake_grokfast_fooddb_diagnostic_preflight_v1"
    assert artifact["status"] == "clear_for_grokfast_fooddb_packet_live_diagnostic"
    assert artifact["clear_to_run_live_diagnostic"] is True
    assert artifact["live_provider_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["next_required_slice"] == "grokfast_fooddb_packet_live_diagnostic"
    assert artifact["summary"]["case_matrix_status"] == "pass"
    assert artifact["summary"]["case_matrix_plan_only"] is True
    assert artifact["summary"]["case_matrix_case_count"] == 5
    assert artifact["summary"]["case_matrix_non_claim_count"] == 7
    assert is_grokfast_fooddb_preflight_clear(artifact) is True


def test_grokfast_fooddb_diagnostic_preflight_blocks_retrieval_eval_failures() -> None:
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(fail_count=1),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
        case_matrix_artifact=_case_matrix(),
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
        case_matrix_artifact=_case_matrix(),
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
        case_matrix_artifact=_case_matrix(),
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
        case_matrix_artifact=_case_matrix(),
    )

    assert artifact["status"] == "blocked"
    assert "manager_packet_smoke_claimed_readiness" in artifact["blockers"]
    assert "manager_packet_smoke_attempted_mutation" in artifact["blockers"]


def test_grokfast_fooddb_preflight_clear_helper_rejects_forged_summary() -> None:
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
        case_matrix_artifact=_case_matrix(),
    )
    forged = {
        **artifact,
        "summary": {
            **artifact["summary"],
            "retrieval_eval_fail_count": 1,
            "case_matrix_shared_contract_changed": True,
            "case_matrix_non_claim_count": 1,
        },
    }

    assert forged["status"] == "clear_for_grokfast_fooddb_packet_live_diagnostic"
    assert forged["clear_to_run_live_diagnostic"] is True
    assert forged["blockers"] == []
    assert is_grokfast_fooddb_preflight_clear(forged) is False


def test_grokfast_fooddb_diagnostic_preflight_requires_case_matrix() -> None:
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
        case_matrix_artifact={
            "artifact_type": "unexpected",
            "summary": {},
        },
    )

    assert artifact["status"] == "blocked"
    assert "unsupported_fooddb_grokfast_case_matrix_artifact" in artifact["blockers"]
    assert is_grokfast_fooddb_preflight_clear(artifact) is False


def test_grokfast_fooddb_diagnostic_preflight_blocks_ad_hoc_case_matrix() -> None:
    case_matrix = _case_matrix()
    case_matrix["cases"] = [{"case_id": "ad_hoc_easy_fooddb_live_case"}]
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
        case_matrix_artifact=case_matrix,
    )

    assert artifact["status"] == "blocked"
    assert "fooddb_grokfast_case_matrix_required_case_order_mismatch" in artifact["blockers"]
    assert is_grokfast_fooddb_preflight_clear(artifact) is False


def test_grokfast_fooddb_diagnostic_preflight_blocks_case_matrix_overclaims() -> None:
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
        case_matrix_artifact=_case_matrix(
            plan_only=False,
            live_provider_invoked=True,
            websearch_invoked=True,
        ),
    )

    assert artifact["status"] == "blocked"
    assert "fooddb_grokfast_case_matrix_not_plan_only" in artifact["blockers"]
    assert "fooddb_grokfast_case_matrix_invoked_live_provider" in artifact["blockers"]
    assert "fooddb_grokfast_case_matrix_invoked_websearch" in artifact["blockers"]
    assert is_grokfast_fooddb_preflight_clear(artifact) is False


def test_grokfast_fooddb_diagnostic_preflight_blocks_case_matrix_contract_changes() -> None:
    case_matrix = _case_matrix()
    case_matrix["shared_contract_changed"] = True
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
        case_matrix_artifact=case_matrix,
    )

    assert artifact["status"] == "blocked"
    assert "fooddb_grokfast_case_matrix_changed_shared_contract" in artifact["blockers"]
    assert is_grokfast_fooddb_preflight_clear(artifact) is False


def test_grokfast_fooddb_diagnostic_preflight_blocks_missing_case_matrix_non_claims() -> None:
    case_matrix = _case_matrix()
    case_matrix["non_claims"] = ["not_full_self_use_gate"]
    artifact = build_grokfast_fooddb_diagnostic_preflight(
        retrieval_eval_wall_artifact=_retrieval_eval_wall(),
        fooddb_status_packet=_fooddb_status(),
        manager_packet_smoke_artifact=_manager_packet_smoke(),
        case_matrix_artifact=case_matrix,
    )

    assert artifact["status"] == "blocked"
    assert (
        "fooddb_grokfast_case_matrix_missing_non_claim.not_websearch_exact_card_gate"
        in artifact["blockers"]
    )
    assert (
        "fooddb_grokfast_case_matrix_missing_non_claim.not_runtime_mutation_gate"
        in artifact["blockers"]
    )
    assert is_grokfast_fooddb_preflight_clear(artifact) is False


def test_grokfast_fooddb_diagnostic_preflight_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_grokfast_fooddb_diagnostic_preflight import main

    retrieval_path = tmp_path / "retrieval.json"
    fooddb_status_path = tmp_path / "fooddb_status.json"
    packet_path = tmp_path / "packet.json"
    case_matrix_path = tmp_path / "case_matrix.json"
    output = tmp_path / "preflight.json"
    write_json_artifact(retrieval_path, _retrieval_eval_wall())
    write_json_artifact(fooddb_status_path, _fooddb_status())
    write_json_artifact(packet_path, _manager_packet_smoke())
    write_json_artifact(case_matrix_path, _case_matrix())

    assert (
        main(
            [
                "--retrieval-eval-wall",
                str(retrieval_path),
                "--fooddb-status-packet",
                str(fooddb_status_path),
                "--manager-packet-smoke",
                str(packet_path),
                "--case-matrix",
                str(case_matrix_path),
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
        case_matrix_artifact=_case_matrix(),
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
