from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.composition.accurate_intake_context_live_diagnostic_canary import (
    build_context_live_diagnostic_canary_report,
)
from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
)
from app.composition.accurate_intake_context_live_provider_input_preflight import (
    build_context_live_provider_input_preflight_artifact,
)


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _fixture_response(provider_input: dict[str, Any]) -> dict[str, Any]:
    expected = _dict(provider_input.get("expected_semantic_contract"))
    sidecar = _dict(provider_input.get("manager_context_sidecar"))
    prior_context = _dict(sidecar.get("prior_context"))
    candidates = prior_context.get("target_candidates") if isinstance(prior_context.get("target_candidates"), list) else []
    target_resolution = {"status": "not_applicable", "candidate_ids": []}
    clarification_question = None
    if sidecar.get("ambiguity_expected") is True:
        target_resolution = {"status": "ambiguous", "candidate_ids": candidates}
        clarification_question = "Which target should I use?"
    elif sidecar.get("target_candidates_expected") is True:
        target_resolution = {"status": "candidates_available", "candidate_ids": candidates}
    return {
        "case_id": provider_input.get("case_id"),
        "manager_intent": expected.get("manager_intent"),
        "workflow_effect": expected.get("workflow_effect"),
        "target_resolution": target_resolution,
        "mutation_request": {"requested": False, "reason": "stage_gate_fixture"},
        "clarification_question": clarification_question,
        "confidence_notes": "fixture response for staged live diagnostic validation",
    }


def _live_canary_for_case_count(count: int) -> dict[str, Any]:
    preflight = build_context_live_provider_input_preflight_artifact()
    inputs = list(preflight["provider_inputs"])[:count]
    narrowed = {**preflight, "provider_inputs": inputs}
    return build_context_live_diagnostic_canary_report(
        context_live_provider_input_preflight=narrowed,
        provider_outputs=[_fixture_response(row) for row in inputs],
        live_invoked=True,
    )


def test_stage_gate_accepts_one_fixed_case_live_probe_only() -> None:
    from app.composition.accurate_intake_context_live_diagnostic_stage_gate import (
        build_context_live_diagnostic_stage_gate_artifact,
    )

    artifact = build_context_live_diagnostic_stage_gate_artifact(
        live_stage="single-case",
        context_live_diagnostic_canary=_live_canary_for_case_count(1),
    )

    assert artifact["artifact_type"] == "accurate_intake_context_live_diagnostic_stage_gate"
    assert artifact["status"] == "context_live_single_case_probe_pass"
    assert artifact["live_stage"] == "single-case"
    assert artifact["single_case_live_probe_required"] is True
    assert artifact["full_matrix_live_probe_allowed"] is False
    assert artifact["live_provider_invoked"] is True
    assert artifact["fooddb_used"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert "product_readiness_claimed" not in artifact
    assert artifact["summary"]["provider_output_count"] == 1
    assert artifact["summary"]["case_ids"] == [REQUIRED_CASE_IDS[0]]


def test_stage_gate_rejects_single_case_stage_with_full_matrix_output() -> None:
    from app.composition.accurate_intake_context_live_diagnostic_stage_gate import (
        build_context_live_diagnostic_stage_gate_artifact,
    )

    artifact = build_context_live_diagnostic_stage_gate_artifact(
        live_stage="single-case",
        context_live_diagnostic_canary=_live_canary_for_case_count(len(REQUIRED_CASE_IDS)),
    )

    assert artifact["status"] == "blocked"
    assert "single_case_live_probe_expected_one_provider_output" in artifact["blockers"]


def test_stage_gate_requires_single_case_pass_before_full_matrix_live_probe() -> None:
    from app.composition.accurate_intake_context_live_diagnostic_stage_gate import (
        build_context_live_diagnostic_stage_gate_artifact,
    )

    artifact = build_context_live_diagnostic_stage_gate_artifact(
        live_stage="full-matrix",
        context_live_diagnostic_canary=_live_canary_for_case_count(len(REQUIRED_CASE_IDS)),
    )

    assert artifact["status"] == "blocked"
    assert "single_case_stage_gate_required_before_full_matrix" in artifact["blockers"]

    single_case = build_context_live_diagnostic_stage_gate_artifact(
        live_stage="single-case",
        context_live_diagnostic_canary=_live_canary_for_case_count(1),
    )
    full_matrix = build_context_live_diagnostic_stage_gate_artifact(
        live_stage="full-matrix",
        context_live_diagnostic_canary=_live_canary_for_case_count(len(REQUIRED_CASE_IDS)),
        prior_single_case_stage_gate=single_case,
    )

    assert full_matrix["status"] == "context_live_full_matrix_probe_pass"
    assert full_matrix["full_matrix_live_probe_allowed"] is True
    assert full_matrix["summary"]["provider_output_count"] == len(REQUIRED_CASE_IDS)


def test_stage_gate_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_context_live_diagnostic_stage_gate import main

    canary = _live_canary_for_case_count(1)
    canary_path = tmp_path / "canary.json"
    output_path = tmp_path / "stage-gate.json"
    canary_path.write_text(json.dumps(canary), encoding="utf-8")

    assert main(["--live-stage", "single-case", "--canary-json", str(canary_path), "--output", str(output_path)]) == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["status"] == "context_live_single_case_probe_pass"


def test_context_live_diagnostic_gate_live_stage_blocks_full_matrix_without_single_case(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    import scripts.run_accurate_intake_context_live_diagnostic_gate as gate

    async def fake_live_canary(**_: Any) -> dict[str, Any]:
        return _live_canary_for_case_count(len(REQUIRED_CASE_IDS))

    monkeypatch.setenv("AI_BUILDER_TOKEN", "fake-token")
    monkeypatch.setattr(gate, "_live_canary", fake_live_canary)
    output_path = tmp_path / "context-live-gate.json"

    exit_code = gate.main(
        [
            "--artifact-dir",
            str(tmp_path / "artifacts"),
            "--output",
            str(output_path),
            "--allow-live-provider",
            "--live-stage",
            "full-matrix",
        ]
    )
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert artifact["status"] == "blocked"
    assert artifact["live_stage"] == "full-matrix"
    assert artifact["stage_gate_status"] == "blocked"
    assert "context_live_diagnostic_stage_gate" in artifact["artifact_paths"]
    assert "context_live_diagnostic_stage_gate.single_case_stage_gate_required_before_full_matrix" in artifact["blockers"]


def test_manifest_checks_accept_single_case_live_stage_gate() -> None:
    from app.composition.accurate_intake_pl_ce_context_live_manifest_checks import (
        context_live_optional_group_blockers,
        context_live_gate_state,
    )

    payload = {
        "artifact_type": "accurate_intake_context_live_diagnostic_gate",
        "status": "context_live_diagnostic_gate_ready_with_live_canary",
        "diagnostic_only": True,
        "local_only": True,
        "fixed_case_matrix_used": True,
        "full_matrix_live_probe_required": True,
        "ad_hoc_live_case_selection_allowed": False,
        "anti_overfit_guard_required": True,
        "holdout_plan_required": True,
        "response_contract_dry_run_required": True,
        "review_pack_status": "context_live_diagnostic_review_ready_with_live_canary",
        "canary_status": "live_diagnostic_pass",
        "live_llm_invoked": True,
        "live_provider_invoked": True,
        "live_stage": "single-case",
        "stage_gate_status": "context_live_single_case_probe_pass",
        "artifact_paths": {
            "context_live_diagnostic_case_matrix": "artifacts/matrix.json",
            "context_live_diagnostic_anti_overfit_guard": "artifacts/anti.json",
            "context_live_diagnostic_holdout_plan": "artifacts/holdout.json",
            "context_live_provider_input_preflight": "artifacts/preflight.json",
            "context_live_response_contract_dry_run": "artifacts/dry.json",
            "context_live_diagnostic_canary": "artifacts/canary.json",
            "context_live_diagnostic_review_pack": "artifacts/review.json",
            "context_live_diagnostic_stage_gate": "artifacts/stage.json",
        },
        "summary": {
            "fixed_case_count": len(REQUIRED_CASE_IDS),
            "dry_run_validated_response_count": len(REQUIRED_CASE_IDS),
            "live_provider_output_count": 1,
            "live_blocked_response_count": 0,
        },
    }

    assert context_live_optional_group_blockers("context_live_diagnostic_gate", payload) == []
    assert context_live_gate_state(payload) == (
        "gate_live_canary_passed",
        "context_only_live_diagnostic_gate_passed_not_full_e2e",
        True,
    )
