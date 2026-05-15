from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_product_pages_renderer_source_map import (
    build_product_pages_renderer_source_map_artifact,
)
from app.composition.accurate_intake_today_macro_mirror_gate import (
    build_today_macro_mirror_gate_artifact,
)


TODAY_PAGE = Path("static/accurate-intake-today.html")


def test_today_macro_mirror_gate_accepts_current_renderer_contract_and_today_page_behavior() -> None:
    renderer_source_map = build_product_pages_renderer_source_map_artifact()

    artifact = build_today_macro_mirror_gate_artifact(
        renderer_source_map_artifact=renderer_source_map
    )

    assert artifact["artifact_type"] == "accurate_intake_today_macro_mirror_gate"
    assert artifact["status"] == "today_macro_mirror_gate_ready_for_human_review"
    assert artifact["pass_type"] == "contract"
    assert artifact["blockers"] == []
    assert artifact["summary"]["renderer_contract_fields_checked"] == 5
    assert artifact["summary"]["visible_case_checked"] is True
    assert artifact["summary"]["guarded_case_checked"] is True
    assert artifact["visible_case"]["macro_state"] == "visible"
    assert artifact["visible_case"]["macro_grid_hidden"] is False
    assert artifact["visible_case"]["macro_guard_reason_hidden"] is True
    assert artifact["visible_case"]["protein_text"] == "31"
    assert artifact["visible_case"]["carbs_text"] == "44"
    assert artifact["visible_case"]["fat_text"] == "12"
    assert artifact["guarded_case"]["macro_state"] == "guarded"
    assert artifact["guarded_case"]["macro_grid_hidden"] is True
    assert artifact["guarded_case"]["macro_guard_reason_hidden"] is False
    assert artifact["guarded_case"]["macro_guard_reason_text"] == "Backend says macros are insufficient today."
    assert artifact["frontend_semantic_owner"] is False
    assert artifact["frontend_calculates_macro_values"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False


def test_today_macro_mirror_gate_blocks_missing_renderer_contract_fields() -> None:
    renderer_source_map = build_product_pages_renderer_source_map_artifact()
    today = dict(renderer_source_map["source_map"]["today"])
    today["backend_fields"] = [
        field for field in list(today["backend_fields"]) if field != "payload.show_macro"
    ]
    renderer_source_map["source_map"]["today"] = today

    artifact = build_today_macro_mirror_gate_artifact(
        renderer_source_map_artifact=renderer_source_map
    )

    assert artifact["status"] == "blocked"
    assert (
        "renderer_source_map.today.missing_backend_field:payload.show_macro"
        in artifact["blockers"]
    )


def test_today_macro_mirror_gate_blocks_guarded_case_macro_leak() -> None:
    broken_today_html = TODAY_PAGE.read_text(encoding="utf-8").replace(
        'writeText("protein-g", showMacro ? payload.consumed_protein : null);',
        'writeText("protein-g", payload.consumed_protein);',
    )

    artifact = build_today_macro_mirror_gate_artifact(html_override=broken_today_html)

    assert artifact["status"] == "blocked"
    assert "today_macro_panel.guarded_case.protein_text_leaked" in artifact["blockers"]


def test_today_macro_mirror_gate_cli_writes_artifact_from_renderer_source_map_json(
    tmp_path: Path,
) -> None:
    from scripts.build_accurate_intake_today_macro_mirror_gate import main

    renderer_path = tmp_path / "renderer-source-map.json"
    output_path = tmp_path / "today-macro-mirror-gate.json"
    renderer_path.write_text(
        json.dumps(build_product_pages_renderer_source_map_artifact(), ensure_ascii=False),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--renderer-source-map-json",
            str(renderer_path),
            "--output",
            str(output_path),
        ]
    )
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "today_macro_mirror_gate_ready_for_human_review"


def test_today_macro_mirror_gate_source_stays_out_of_fooddb_websearch_and_live_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_today_macro_mirror_contract.py"),
        Path("app/composition/accurate_intake_today_macro_mirror_gate.py"),
        Path("app/composition/accurate_intake_today_macro_panel_probe.py"),
        Path("scripts/build_accurate_intake_today_macro_mirror_gate.py"),
    ]
    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "Tavily",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "live_llm_invoked = True",
        "web_tavily_used = True",
        "ready_for_live_diagnostic_decision = True",
        "ready_for_fdb_integration = True",
    ):
        assert fragment not in combined_source


def test_ci_runs_today_macro_panel_behavior_and_today_macro_mirror_gate() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "tests/test_accurate_intake_today_macro_panel_behavior.py" in workflow
    assert "tests/test_accurate_intake_today_macro_mirror_gate.py" in workflow
