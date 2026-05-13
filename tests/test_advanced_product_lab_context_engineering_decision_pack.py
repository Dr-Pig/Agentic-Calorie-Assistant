from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "scripts/build_advanced_product_lab_context_engineering_decision_pack.py"


def test_context_engineering_decision_pack_passes_without_mainline_activation() -> None:
    from app.advanced_shadow_lab.context_engineering_decision_pack import (
        build_context_engineering_decision_pack,
    )

    pack = build_context_engineering_decision_pack(
        pr_train=_pr_train(),
        baseline_runtime_artifact=_baseline_runtime(),
        manager_runtime_artifact=_manager_runtime(),
        live_grokfast_artifact=_live_grokfast(),
    )

    assert pack["artifact_type"] == "advanced_product_lab_context_engineering_decision_pack"
    assert pack["status"] == "pass"
    assert pack["ready_for_recommendation_entry_contract"] is True
    assert pack["ready_for_mainline_activation"] is False
    assert pack["mainline_activation_enabled"] is False
    assert pack["comparison"]["baseline_runtime_passed"] is True
    assert pack["comparison"]["manager_runtime_passed"] is True
    assert pack["comparison"]["manager_tool_order"] == [
        "memory.search",
        "reusable_meal.search",
        "rescue.run",
    ]
    assert pack["live_grokfast_summary"]["live_grokfast_diagnostic_pass"] is True
    assert pack["blockers"] == []


def test_context_engineering_decision_pack_blocks_activation_or_missing_live() -> None:
    from app.advanced_shadow_lab.context_engineering_decision_pack import (
        build_context_engineering_decision_pack,
    )

    live = _live_grokfast()
    live["live_grokfast_diagnostic_pass"] = False
    manager = _manager_runtime()
    manager["canonical_product_mutation_allowed"] = True
    pack = build_context_engineering_decision_pack(
        pr_train=_pr_train(),
        baseline_runtime_artifact=_baseline_runtime(),
        manager_runtime_artifact=manager,
        live_grokfast_artifact=live,
    )

    assert pack["status"] == "blocked"
    assert "manager_runtime.canonical_product_mutation_allowed" in pack["blockers"]
    assert "live_grokfast.not_passed" in pack["blockers"]
    assert pack["ready_for_recommendation_entry_contract"] is False
    assert pack["ready_for_mainline_activation"] is False


def test_context_engineering_decision_pack_cli_roundtrip(tmp_path: Path) -> None:
    pr_train = tmp_path / "pr-train.json"
    baseline = tmp_path / "baseline.json"
    manager = tmp_path / "manager.json"
    live = tmp_path / "live.json"
    output = tmp_path / "decision-pack.json"
    write_json_artifact(pr_train, _pr_train())
    write_json_artifact(baseline, _baseline_runtime())
    write_json_artifact(manager, _manager_runtime())
    write_json_artifact(live, _live_grokfast())

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--pr-train-json",
            str(pr_train),
            "--baseline-runtime-json",
            str(baseline),
            "--manager-runtime-json",
            str(manager),
            "--live-grokfast-json",
            str(live),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout = json.loads(result.stdout)
    pack = read_json_artifact(output)
    assert stdout == pack
    assert pack["status"] == "pass"


def _pr_train() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_context_engineering_pr_train",
        "status": "active",
        "planned_pr_count": 29,
        "last_completed_pr_number": 27,
        "dynamic_remaining_pr_count": 2,
    }


def _baseline_runtime() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_turn_artifact",
        "status": "pass",
        "manager_tool_loop_enabled": False,
        "mainline_runtime_connected": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def _manager_runtime() -> dict[str, object]:
    return {
        **_baseline_runtime(),
        "manager_tool_loop_enabled": True,
        "manager_tool_loop_source_refs": [
            "manager_tool_call:memory-search-1:memory.search",
            "manager_tool_call:reusable-meal-search-1:reusable_meal.search",
            "manager_tool_call:rescue-1:rescue.run",
        ],
        "manager_selected_memory_context_adapter": {"status": "pass"},
        "manager_selected_reusable_meal_artifact": {"status": "pass"},
        "manager_selected_rescue_artifact": {"status": "pass"},
    }


def _live_grokfast() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_manager_turn_grokfast_diagnostic",
        "status": "pass",
        "diagnostic_evidence_class": "live_grokfast",
        "live_invoked": True,
        "provider_invoked": True,
        "live_provider_used": True,
        "live_grokfast_diagnostic_pass": True,
        "source_manager_tool_order": ["memory.search", "reusable_meal.search", "rescue.run"],
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "blockers": [],
    }
