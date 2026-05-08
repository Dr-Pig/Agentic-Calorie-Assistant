from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import yaml

from app.composition.accurate_intake_product_pages_renderer_source_map import (
    build_product_pages_renderer_source_closure_artifact,
)


def _manager_gate_ledger() -> dict[str, object]:
    return yaml.safe_load(Path("docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml").read_text(encoding="utf-8"))


def test_renderer_source_closure_gate_ties_chat_today_body_to_routes_and_manager_gates() -> None:
    artifact = build_product_pages_renderer_source_closure_artifact(
        manager_gate_ledger_artifact=_manager_gate_ledger()
    )

    assert artifact["artifact_type"] == "accurate_intake_product_pages_renderer_source_closure_gate"
    assert artifact["status"] == "product_pages_renderer_source_closure_ready_for_browser"
    assert artifact["pass_type"] == "contract"
    assert artifact["blockers"] == []
    assert artifact["pages"] == ["chat", "today", "body"]
    assert artifact["source_map_status"] == "product_pages_renderer_source_map_ready_for_human_review"
    assert artifact["route_table_checked"] is True
    assert artifact["endpoint_method_contract"] == {
        "/estimate": ["POST"],
        "/accurate-intake/chat-history": ["GET"],
        "/today/current-budget": ["GET"],
        "/body-plan/active": ["GET"],
        "/weight/observations": ["GET"],
        "/weight/observation": ["POST"],
        "/onboarding/bootstrap": ["POST"],
        "/body-plan/manual-daily-target": ["POST"],
        "/today/deficit-summary": ["GET"],
        "/today/effective-budget": ["GET"],
        "/today/weekly-progress": ["GET"],
    }
    assert artifact["upstream_manager_gates"] == {
        "rt6_bootstrap_no_plan_body_closure": "green",
        "rt7_clarify_commit_correction_closure": "green",
        "rt8_overshoot_runtime_truth": "green",
        "rt11c_renderer_input_basis_evidence_pack": "green",
        "rt14_limited_live_ladder": "green",
    }
    assert artifact["frontend_semantic_owner"] is False
    assert artifact["frontend_selects_target"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["product_readiness_claimed"] is False


def test_renderer_source_closure_gate_blocks_missing_runtime_route() -> None:
    route_table = {
        "/estimate": ["POST"],
        "/today/current-budget": ["GET"],
    }

    artifact = build_product_pages_renderer_source_closure_artifact(
        manager_gate_ledger_artifact=_manager_gate_ledger(),
        route_table_override=route_table,
    )

    assert artifact["status"] == "blocked"
    assert "route_table.missing_endpoint:/accurate-intake/chat-history" in artifact["blockers"]
    assert "route_table.missing_endpoint:/body-plan/active" in artifact["blockers"]


def test_renderer_source_closure_gate_blocks_wrong_runtime_route_method() -> None:
    artifact = build_product_pages_renderer_source_closure_artifact(
        manager_gate_ledger_artifact=_manager_gate_ledger(),
        route_table_override={
            "/estimate": ["GET"],
            "/accurate-intake/chat-history": ["GET"],
            "/today/current-budget": ["GET"],
            "/body-plan/active": ["GET"],
            "/weight/observations": ["GET"],
            "/weight/observation": ["POST"],
            "/onboarding/bootstrap": ["POST"],
            "/body-plan/manual-daily-target": ["POST"],
            "/today/deficit-summary": ["GET"],
            "/today/effective-budget": ["GET"],
            "/today/weekly-progress": ["GET"],
        },
    )

    assert artifact["status"] == "blocked"
    assert "route_table.endpoint_method_missing:/estimate:POST" in artifact["blockers"]


def test_renderer_source_closure_gate_blocks_when_manager_upstream_gate_not_green() -> None:
    ledger = deepcopy(_manager_gate_ledger())
    for gate in ledger["gates"]:
        if gate["gate_id"] == "rt11c_renderer_input_basis_evidence_pack":
            gate["status"] = "pending"

    artifact = build_product_pages_renderer_source_closure_artifact(
        manager_gate_ledger_artifact=ledger
    )

    assert artifact["status"] == "blocked"
    assert (
        "manager_runtime_gate.rt11c_renderer_input_basis_evidence_pack_not_green:pending"
        in artifact["blockers"]
    )


def test_renderer_source_closure_gate_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_product_pages_renderer_source_closure_gate import main

    output_path = tmp_path / "renderer-source-closure.json"
    exit_code = main(["--output", str(output_path)])
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "product_pages_renderer_source_closure_ready_for_browser"


def test_ci_runs_renderer_source_closure_gate() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "tests/test_accurate_intake_product_pages_renderer_source_closure_gate.py" in workflow
    assert "build_accurate_intake_product_pages_renderer_source_closure_gate.py" in workflow
