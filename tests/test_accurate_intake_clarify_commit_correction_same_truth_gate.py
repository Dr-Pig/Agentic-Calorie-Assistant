from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_clarify_commit_correction_same_truth_gate import (
    CLARIFY_COMMIT_CORRECTION_SAME_TRUTH_READY_STATUS,
    build_clarify_commit_correction_same_truth_gate_artifact,
)


def _product_pages_browser_smoke() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_product_pages_browser_smoke",
        "smoke_id": "accurate_intake_product_pages_browser_smoke_v1",
        "status": "pass",
        "browser_executed": True,
        "today_meal_list_rendered": True,
        "today_summary_rendered": True,
    }


def _short_term_context_smoke() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_product_pages_short_term_context_smoke",
        "smoke_id": "accurate_intake_product_pages_short_term_context_smoke_v1",
        "status": "pass",
        "browser_executed": True,
        "pending_followup_created": True,
        "pending_followup_reloaded": True,
        "chat_history_context_fields_reloaded": True,
        "assistant_followup_bubble_rendered": True,
        "assistant_commit_bubble_rendered": True,
        "today_no_meal_before_followup_answer": True,
        "today_consumed_zero_before_followup_answer": True,
        "today_same_day_meal_rendered": True,
        "today_summary_rendered": True,
        "product_pages_no_debug_trace": True,
    }


def _target_candidate_ui_smoke() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_product_pages_target_candidate_ui_smoke",
        "smoke_id": "accurate_intake_product_pages_target_candidate_ui_smoke_v1",
        "status": "pass",
        "browser_executed": True,
        "target_candidate_surface_checked": True,
        "target_candidate_count_rendered": 2,
        "target_candidate_names_rendered": ["luwei", "milk tea"],
        "target_candidate_list_read_only": True,
        "context_strip_read_only": True,
        "product_pages_no_debug_trace": True,
    }


def _fixture_full_product_loop_e2e() -> dict[str, object]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_fixture_full_product_loop_e2e",
        "status": "fixture_product_loop_e2e_diagnostic_pass",
        "browser_executed": True,
        "fixture_evidence_used": True,
        "completed_product_loop_steps": [
            "food_log",
            "listed_basket_commit",
            "correction",
            "removal",
            "reload_continuity",
            "browser_render_same_truth",
            "context_replay",
            "fake_provider_context_smoke",
        ],
    }


def _rt7_green_ledger() -> dict[str, object]:
    return {
        "gates": [
            {
                "gate_id": "rt7_clarify_commit_correction_closure",
                "status": "green",
                "pass_type": "runtime_backed",
                "title": "Clarify, commit, and correction closure",
            }
        ]
    }


def test_clarify_commit_correction_same_truth_gate_accepts_rt7_green_browser_truth() -> None:
    artifact = build_clarify_commit_correction_same_truth_gate_artifact(
        product_pages_browser_smoke=_product_pages_browser_smoke(),
        short_term_context_smoke=_short_term_context_smoke(),
        target_candidate_ui_smoke=_target_candidate_ui_smoke(),
        fixture_full_product_loop_e2e=_fixture_full_product_loop_e2e(),
        manager_runtime_gate_ledger=_rt7_green_ledger(),
    )

    assert artifact["artifact_type"] == "accurate_intake_clarify_commit_correction_same_truth_gate"
    assert artifact["status"] == CLARIFY_COMMIT_CORRECTION_SAME_TRUTH_READY_STATUS
    assert artifact["pass_type"] == "browser_executed"
    assert artifact["journeys"] == ["B", "C", "D", "K"]
    assert artifact["upstream_runtime_gate"] == "rt7_clarify_commit_correction_closure"
    assert artifact["blockers"] == []
    assert artifact["summary"]["upstream_gate_green"] is True
    assert artifact["summary"]["target_candidate_count_rendered"] == 2
    assert artifact["summary"]["completed_fixture_step_count"] == 8
    assert "product_readiness_claimed" not in artifact
    assert "private_self_use_approved" not in artifact


def test_clarify_commit_correction_same_truth_gate_blocks_when_rt7_not_green() -> None:
    artifact = build_clarify_commit_correction_same_truth_gate_artifact(
        product_pages_browser_smoke=_product_pages_browser_smoke(),
        short_term_context_smoke=_short_term_context_smoke(),
        target_candidate_ui_smoke=_target_candidate_ui_smoke(),
        fixture_full_product_loop_e2e=_fixture_full_product_loop_e2e(),
        manager_runtime_gate_ledger={
            "gates": [
                {
                    "gate_id": "rt7_clarify_commit_correction_closure",
                    "status": "pending",
                }
            ]
        },
    )

    assert artifact["status"] == "blocked"
    assert "upstream_gate.rt7_clarify_commit_correction_closure_not_green:pending" in artifact["blockers"]


def test_clarify_commit_correction_same_truth_gate_blocks_when_candidate_or_fixture_evidence_missing() -> None:
    target_candidate_ui_smoke = _target_candidate_ui_smoke()
    target_candidate_ui_smoke["target_candidate_surface_checked"] = False
    fixture_full_product_loop_e2e = _fixture_full_product_loop_e2e()
    fixture_full_product_loop_e2e["completed_product_loop_steps"] = [
        "food_log",
        "listed_basket_commit",
        "correction",
    ]

    artifact = build_clarify_commit_correction_same_truth_gate_artifact(
        product_pages_browser_smoke=_product_pages_browser_smoke(),
        short_term_context_smoke=_short_term_context_smoke(),
        target_candidate_ui_smoke=target_candidate_ui_smoke,
        fixture_full_product_loop_e2e=fixture_full_product_loop_e2e,
        manager_runtime_gate_ledger=_rt7_green_ledger(),
    )

    assert artifact["status"] == "blocked"
    assert "target_candidate_ui_smoke.target_candidate_surface_checked_not_true" in artifact["blockers"]
    assert "fixture_full_product_loop_e2e.completed_step_missing:removal" in artifact["blockers"]
    assert "fixture_full_product_loop_e2e.completed_step_missing:reload_continuity" in artifact["blockers"]


def test_clarify_commit_correction_same_truth_gate_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_clarify_commit_correction_same_truth_gate import main

    browser_smoke_path = tmp_path / "product-pages-browser-smoke.json"
    short_term_context_path = tmp_path / "product-pages-short-term-context-smoke.json"
    target_candidate_ui_path = tmp_path / "product-pages-target-candidate-ui-smoke.json"
    fixture_path = tmp_path / "fixture-full-product-loop-e2e.json"
    ledger_path = tmp_path / "manager-runtime-gate-ledger.json"
    output_path = tmp_path / "clarify-commit-correction-same-truth-gate.json"

    browser_smoke_path.write_text(
        json.dumps(_product_pages_browser_smoke(), ensure_ascii=False),
        encoding="utf-8",
    )
    short_term_context_path.write_text(
        json.dumps(_short_term_context_smoke(), ensure_ascii=False),
        encoding="utf-8",
    )
    target_candidate_ui_path.write_text(
        json.dumps(_target_candidate_ui_smoke(), ensure_ascii=False),
        encoding="utf-8",
    )
    fixture_path.write_text(
        json.dumps(_fixture_full_product_loop_e2e(), ensure_ascii=False),
        encoding="utf-8",
    )
    ledger_path.write_text(json.dumps(_rt7_green_ledger(), ensure_ascii=False), encoding="utf-8")

    exit_code = main(
        [
            "--product-pages-browser-smoke-json",
            str(browser_smoke_path),
            "--product-pages-short-term-context-smoke-json",
            str(short_term_context_path),
            "--product-pages-target-candidate-ui-smoke-json",
            str(target_candidate_ui_path),
            "--fixture-full-product-loop-e2e-json",
            str(fixture_path),
            "--manager-runtime-gate-ledger-json",
            str(ledger_path),
            "--output",
            str(output_path),
        ]
    )
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == CLARIFY_COMMIT_CORRECTION_SAME_TRUTH_READY_STATUS


def test_clarify_commit_correction_same_truth_gate_source_stays_out_of_fooddb_live_and_mutation_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_clarify_commit_correction_same_truth_gate.py"),
        Path("scripts/build_accurate_intake_clarify_commit_correction_same_truth_gate.py"),
    ]
    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "Tavily",
        "builderspace_adapter",
        "live_llm_invoked = True",
        "fooddb_evidence_used = True",
        "mutation_changed = True",
    ):
        assert fragment not in combined_source


def test_ci_runs_clarify_commit_correction_same_truth_gate() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "tests/test_accurate_intake_clarify_commit_correction_same_truth_gate.py" in workflow
