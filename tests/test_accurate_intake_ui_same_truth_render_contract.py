from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_ui_same_truth_render_contract import (
    build_ui_same_truth_render_contract,
)
from scripts import build_accurate_intake_ui_same_truth_render_contract as module


def test_ui_same_truth_render_contract_accepts_current_local_shell() -> None:
    html = Path("static/accurate-intake-local-shell.html").read_text(encoding="utf-8")

    artifact = build_ui_same_truth_render_contract(html)

    assert artifact["artifact_type"] == "accurate_intake_ui_same_truth_render_contract"
    assert artifact["status"] == "pass"
    assert artifact["frontend_semantic_owner"] is False
    assert artifact["render_only_boundary_ok"] is True
    assert artifact["backend_truth_selectors_present"] is True
    assert artifact["required_render_functions_present"] is True
    assert artifact["forbidden_semantic_fragments_present"] == []
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["fooddb_truth_updated"] is False
    assert artifact["live_llm_invoked"] is False


def test_ui_same_truth_render_contract_lists_backend_truth_selectors_and_render_functions() -> None:
    html = Path("static/accurate-intake-local-shell.html").read_text(encoding="utf-8")

    artifact = build_ui_same_truth_render_contract(html)

    assert {"#budget-kcal", "#consumed-kcal", "#remaining-kcal"} <= set(
        artifact["backend_truth_selectors"]
    )
    assert {"renderBudget", "renderDebug", "renderChatHistory", "renderReviewPanel"} <= set(
        artifact["render_functions"]
    )
    assert "view.budget_kcal" in artifact["backend_truth_fields"]
    assert "thread.active_version?.total_kcal" in artifact["backend_truth_fields"]


def test_ui_same_truth_render_contract_rejects_frontend_semantic_or_kcal_inference() -> None:
    html = """
    <main data-frontend-semantic-owner="false" data-live-llm-required="false">
      <span id="budget-kcal"></span><span id="consumed-kcal"></span><span id="remaining-kcal"></span>
      <ul id="meal-thread-list"></ul><ul id="pending-followup-list"></ul>
      <ul id="runtime-status-list"></ul><ul id="failure-signal-list"></ul><ul id="same-truth-list"></ul>
      <script>
        function renderBudget() {}
        function renderDebug() {}
        function renderChatHistory() {}
        function renderReviewPanel() {}
        const remainingKcal = budget - consumed;
        if (text.includes("拿掉")) selectTarget();
      </script>
    </main>
    """

    artifact = build_ui_same_truth_render_contract(html)

    assert artifact["status"] == "fail"
    assert "budget - consumed" in artifact["forbidden_semantic_fragments_present"]
    assert "text.includes" in artifact["forbidden_semantic_fragments_present"]
    assert "selectTarget" in artifact["forbidden_semantic_fragments_present"]


def test_ui_same_truth_render_contract_cli_writes_artifact(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "ui-contract.json"

    exit_code = module.main(["--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "pass"


def test_ui_same_truth_render_contract_script_stays_out_of_fooddb_websearch_and_live_boundaries() -> None:
    source = Path("scripts/build_accurate_intake_ui_same_truth_render_contract.py").read_text(encoding="utf-8")

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "Tavily",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "kimi",
        "grok",
    ):
        assert fragment not in source
