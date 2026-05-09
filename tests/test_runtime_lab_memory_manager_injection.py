from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _trace() -> dict:
    return {
        "request_id": "rt-lab-injection-001",
        "trace_meta": {
            "request_id": "rt-lab-injection-001",
            "user_id": "user-a",
            "bundle": "intake_execution",
            "local_date": "2026-05-09",
        },
        "memory_lab_scope": {
            "workspace_id": "workspace-a",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "manager_runtime_lab",
            "run_id": "injection-run-001",
        },
        "request": {"user_id": "user-a", "text": "structured injection replay"},
        "renderer_output": {"assistant_message": "Logged lunch."},
        "tool_plan": ["estimate_nutrition", "persist_meal_log"],
        "state_delta": {"meal_log_id": "meal-1"},
        "latency_tracking": {"total_ms": 120},
        "manager_final_decision": {"workflow_effect": "commit_meal_log"},
        "memory_lab_candidate_signal": {
            "candidate_type": "preference",
            "manager_decision_field": "memory_candidate_requested",
            "source_refs": ["message:dogfood-injection-001"],
            "review_status": "pending",
            "promotion_allowed_now": False,
            "human_review_required": True,
            "reason_codes": ["explicit_user_preference"],
            "summary": "prefers lighter lunch suggestions",
        },
    }


def _pack() -> dict:
    return {
        "artifact_type": "shadow_memory_context_pack",
        "entries": [
            {
                "candidate_id": "pref-1",
                "candidate_type": "preference",
                "summary": "preference: prefers lighter lunch suggestions",
                "source_object_refs": ["message:dogfood-injection-001"],
            }
        ],
        "selected_candidate_ids": ["pref-1"],
        "omission_trace": [],
        "token_estimate": 5,
        "manager_context_packet_changed": False,
    }


def test_lab_injection_flag_off_by_default_uses_baseline_only() -> None:
    from app.memory.application.runtime_lab_manager_injection import (
        build_manager_memory_injection_comparison,
    )

    artifact = build_manager_memory_injection_comparison(
        _trace(),
        _pack(),
        enable_lab_injection=False,
    )

    assert artifact["artifact_type"] == "runtime_lab_manager_memory_injection_comparison"
    assert artifact["injection_enabled"] is False
    assert artifact["shadow_memory_context_pack_used"] is False
    assert artifact["final_response_changed"] is False
    assert artifact["baseline_run"]["final_response"] == "Logged lunch."
    assert artifact["memory_context_run"]["final_response"] == "Logged lunch."
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["manager_context_injected"] is False


def test_lab_injection_enabled_uses_shadow_pack_but_blocks_tools_and_mutation() -> None:
    from app.memory.application.runtime_lab_manager_injection import (
        build_manager_memory_injection_comparison,
    )

    artifact = build_manager_memory_injection_comparison(
        _trace(),
        _pack(),
        enable_lab_injection=True,
    )

    assert artifact["injection_enabled"] is True
    assert artifact["shadow_memory_context_pack_used"] is True
    assert artifact["final_response_changed"] is True
    assert artifact["tool_calls_blocked"] is True
    assert artifact["mutation_attempts_blocked"] is True
    assert artifact["memory_context_run"]["tool_calls"] == []
    assert artifact["memory_context_run"]["mutation_attempts"] == []
    assert artifact["latency_comparison"]["memory_context_ms"] >= 120
    assert artifact["durable_product_memory_written"] is False
    assert artifact["canonical_mutation_changed"] is False
    assert artifact["user_facing_behavior_changed"] is False


def test_manager_injection_runner_default_keeps_flag_off(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.json"
    output_path = tmp_path / "injection.json"
    store_root = tmp_path / "runtime_lab_store"
    trace_path.write_text(json.dumps(_trace()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_runtime_lab_memory_manager_injection.py"),
            "--trace-json",
            str(trace_path),
            "--store-root",
            str(store_root),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["injection_enabled"] is False
    assert artifact["shadow_memory_context_pack_used"] is False
    assert artifact["manager_context_packet_changed"] is False


def test_manager_injection_runner_with_explicit_flag_builds_paired_artifact(
    tmp_path: Path,
) -> None:
    trace_path = tmp_path / "trace.json"
    output_path = tmp_path / "injection.json"
    store_root = tmp_path / "runtime_lab_store"
    trace_path.write_text(json.dumps(_trace()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_runtime_lab_memory_manager_injection.py"),
            "--trace-json",
            str(trace_path),
            "--store-root",
            str(store_root),
            "--output",
            str(output_path),
            "--enable-lab-injection",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["injection_enabled"] is True
    assert artifact["runtime_connected"] is True
    assert artifact["shadow_memory_context_pack_used"] is True
    assert artifact["tool_call_delta"]["blocked_from_memory_context_run"]
    assert artifact["omission_trace"] == []


def test_lab_injection_module_stays_out_of_active_manager_imports() -> None:
    active_surfaces = [
        ROOT / "app" / "main.py",
        ROOT / "app" / "routes.py",
        ROOT / "app" / "composition" / "intake_routes.py",
        ROOT / "app" / "composition" / "intake_execution_orchestrator.py",
        ROOT / "app" / "composition" / "intake_turn_orchestrator.py",
        ROOT / "app" / "runtime" / "application" / "manager_service.py",
        ROOT / "app" / "runtime" / "agent" / "manager.py",
    ]
    forbidden_import = "app.memory.application.runtime_lab_manager_injection"
    violations: list[str] = []
    for path in active_surfaces:
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            else:
                imported = []
            if any(value.startswith(forbidden_import) for value in imported):
                violations.append(str(path.relative_to(ROOT)))

    assert violations == []
