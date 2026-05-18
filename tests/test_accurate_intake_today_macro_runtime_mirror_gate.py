from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import yaml

from app.composition.accurate_intake_today_macro_mirror_gate import (
    build_today_macro_runtime_mirror_gate_artifact,
)
from app.shared.domain.canonical_models import CurrentBudgetView


def _manager_gate_ledger() -> dict[str, object]:
    return yaml.safe_load(Path("docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml").read_text(encoding="utf-8"))


def _current_budget_payload(*, show_macro: bool = True) -> dict[str, object]:
    view = CurrentBudgetView(
        user_id=1,
        local_date="2026-05-08",
        budget_kcal=1800,
        consumed_kcal=640,
        consumed_protein=31,
        consumed_carbs=44,
        consumed_fat=12,
        show_macro=show_macro,
        macro_guard_reason=None if show_macro else "Backend macro visibility policy withheld day-level macros.",
        remaining_kcal=1160,
        active_meal_count=2,
    )
    return view.model_dump(mode="json")


def test_today_macro_runtime_mirror_gate_requires_manager_gates_and_current_budget_payload() -> None:
    artifact = build_today_macro_runtime_mirror_gate_artifact(
        manager_gate_ledger_artifact=_manager_gate_ledger(),
        current_budget_payload=_current_budget_payload(show_macro=True),
    )

    assert artifact["artifact_type"] == "accurate_intake_today_macro_runtime_mirror_gate"
    assert artifact["status"] == "today_macro_runtime_mirror_gate_ready_for_browser"
    assert artifact["pass_type"] == "runtime_backed"
    assert artifact["blockers"] == []
    assert artifact["runtime_backed"] is True
    assert artifact["macro_visible_case_checked"] is True
    assert artifact["macro_guarded_case_checked"] is True
    assert artifact["backend_macro_fields_required"] is True
    assert artifact["show_macro_false_suppresses_macro"] is True
    assert artifact["frontend_semantic_owner"] is False
    assert artifact["frontend_calculates_macro_values"] is False
    assert artifact["truth_owner"] == "CurrentBudgetView.macro_visibility"
    assert artifact["upstream_manager_gates"] == {
        "rt11c_renderer_input_basis_evidence_pack": "green",
        "rt14_limited_live_ladder": "green",
    }
    assert artifact["current_budget_payload_fields_checked"] == [
        "consumed_protein",
        "consumed_carbs",
        "consumed_fat",
        "show_macro",
        "macro_guard_reason",
    ]
    assert artifact["runtime_case"]["macro_state"] == "visible"
    assert artifact["runtime_case"]["protein_text"] == "31"
    assert artifact["runtime_case"]["carbs_text"] == "44"
    assert artifact["runtime_case"]["fat_text"] == "12"


def test_today_macro_runtime_mirror_gate_preserves_backend_guarded_macro_state() -> None:
    artifact = build_today_macro_runtime_mirror_gate_artifact(
        manager_gate_ledger_artifact=_manager_gate_ledger(),
        current_budget_payload=_current_budget_payload(show_macro=False),
    )

    assert artifact["status"] == "today_macro_runtime_mirror_gate_ready_for_browser"
    assert artifact["runtime_case"]["macro_state"] == "guarded"
    assert artifact["runtime_case"]["macro_grid_hidden"] is True
    assert artifact["runtime_case"]["macro_guard_reason_hidden"] is False
    assert (
        artifact["runtime_case"]["macro_guard_reason_text"]
        == "Backend macro visibility policy withheld day-level macros."
    )
    assert artifact["runtime_case"]["protein_text"] == "--"
    assert artifact["runtime_case"]["carbs_text"] == "--"
    assert artifact["runtime_case"]["fat_text"] == "--"


def test_today_macro_runtime_mirror_gate_blocks_when_upstream_manager_gate_is_not_green() -> None:
    ledger = deepcopy(_manager_gate_ledger())
    for gate in ledger["gates"]:
        if gate["gate_id"] == "rt14_limited_live_ladder":
            gate["status"] = "pending"

    artifact = build_today_macro_runtime_mirror_gate_artifact(
        manager_gate_ledger_artifact=ledger,
        current_budget_payload=_current_budget_payload(show_macro=True),
    )

    assert artifact["status"] == "blocked"
    assert "manager_runtime_gate.rt14_limited_live_ladder_not_green:pending" in artifact["blockers"]


def test_today_macro_runtime_mirror_gate_blocks_missing_current_budget_payload_field() -> None:
    payload = _current_budget_payload(show_macro=True)
    payload.pop("show_macro")

    artifact = build_today_macro_runtime_mirror_gate_artifact(
        manager_gate_ledger_artifact=_manager_gate_ledger(),
        current_budget_payload=payload,
    )

    assert artifact["status"] == "blocked"
    assert "current_budget_payload.missing_field:show_macro" in artifact["blockers"]


def test_today_macro_runtime_mirror_gate_cli_writes_artifact_from_payload_json(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_today_macro_runtime_mirror_gate import main

    payload_path = tmp_path / "current-budget.json"
    output_path = tmp_path / "today-macro-runtime-mirror-gate.json"
    payload_path.write_text(json.dumps(_current_budget_payload(show_macro=True)), encoding="utf-8")

    exit_code = main(
        [
            "--current-budget-json",
            str(payload_path),
            "--renderer-source-map-json",
            str(tmp_path / "absent-renderer-source-map.json"),
            "--output",
            str(output_path),
        ]
    )
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "today_macro_runtime_mirror_gate_ready_for_browser"


def test_ci_runs_today_macro_runtime_mirror_gate() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "tests/test_accurate_intake_today_macro_runtime_mirror_gate.py" in workflow
