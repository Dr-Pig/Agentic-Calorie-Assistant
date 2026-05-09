from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _synthetic_manager_trace() -> dict:
    return {
        "request_id": "rt-lab-001",
        "trace_meta": {
            "request_id": "rt-lab-001",
            "user_id": "user-a",
            "bundle": "intake_execution",
            "local_date": "2026-05-09",
        },
        "memory_lab_scope": {
            "workspace_id": "workspace-a",
            "project_id": "advanced-memory-runtime-lab",
            "surface": "manager_runtime_lab",
            "run_id": "run-001",
        },
        "request": {
            "user_id": "user-a",
            "local_date": "2026-05-09",
            "text": "Lunch: chicken salad. api_key=sk-test-secret should not persist.",
            "allow_search": False,
        },
        "manager_rounds": [
            {
                "round": 1,
                "decision": {
                    "intent": "log_meal",
                    "workflow_effect": "commit_meal_log",
                    "manager_action": "call_tools",
                },
            }
        ],
        "manager_final_decision": {
            "intent": "log_meal",
            "workflow_effect": "commit_meal_log",
            "final_action": "commit",
        },
        "tool_plan": ["estimate_nutrition", "persist_meal_log"],
        "tool_outputs": {
            "persistence_result": {
                "status": "ok",
                "persisted_log_id": "meal-log-123",
                "provider_token": "tok_live_secret",
            }
        },
        "state_delta": {"meal_log_id": "meal-log-123"},
        "trace_refs": {
            "request_id": "rt-lab-001",
            "request_trace_path": "artifacts/runtime/rt-lab-001.json",
            "stage_trace_path": "artifacts/runtime/rt-lab-001-stage.json",
        },
    }


def test_trace_ingress_converts_synthetic_manager_trace_without_memory_write() -> None:
    from app.memory.application.runtime_lab_trace_ingress import (
        build_memory_ingress_event_from_manager_trace,
    )

    event = build_memory_ingress_event_from_manager_trace(_synthetic_manager_trace())

    assert event["artifact_type"] == "memory_ingress_event"
    assert event["request_id"] == "rt-lab-001"
    assert event["scope_keys"] == {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-memory-runtime-lab",
        "surface": "manager_runtime_lab",
        "run_id": "run-001",
    }
    assert event["runtime_connected"] is True
    assert event["lab_isolated"] is True
    assert event["runtime_effect_allowed"] is False
    assert event["memory_store_written"] is False
    assert event["durable_product_memory_written"] is False
    assert event["manager_context_packet_changed"] is False
    assert event["canonical_mutation_changed"] is False
    assert event["manager_decision_summary"]["workflow_effect"] == "commit_meal_log"
    assert "persist_meal_log" in event["tool_call_names"]
    ref_ids = {ref["source_id"] for ref in event["canonical_source_refs"]}
    assert {"rt-lab-001", "meal-log-123"} <= ref_ids


def test_trace_ingress_rejects_missing_scope_before_observation() -> None:
    from app.memory.application.runtime_lab_trace_ingress import (
        build_memory_trace_ingress_diagnostic_artifact,
    )

    trace = _synthetic_manager_trace()
    trace["memory_lab_scope"].pop("project_id")

    artifact = build_memory_trace_ingress_diagnostic_artifact([trace])

    assert artifact["artifact_type"] == "runtime_lab_memory_trace_ingress_diagnostic"
    assert artifact["status"] == "blocked"
    assert artifact["event_count"] == 0
    assert artifact["rejected_trace_count"] == 1
    assert artifact["memory_store_written"] is False
    assert artifact["rejected_traces"][0]["reason"] == "missing_scope_keys:project_id"


def test_trace_ingress_redacts_secret_fields_and_raw_text() -> None:
    from app.memory.application.runtime_lab_trace_ingress import (
        build_memory_ingress_event_from_manager_trace,
    )

    event = build_memory_ingress_event_from_manager_trace(_synthetic_manager_trace())
    serialized = json.dumps(event, ensure_ascii=False)

    assert "sk-test-secret" not in serialized
    assert "tok_live_secret" not in serialized
    assert event["secret_redaction"]["raw_secret_values_stored"] is False
    assert "request.text" in event["secret_redaction"]["redacted_fields"]
    assert "tool_outputs.persistence_result.provider_token" in event["secret_redaction"][
        "redacted_fields"
    ]


def test_trace_ingress_runner_writes_non_live_diagnostic_artifact(
    tmp_path: Path,
) -> None:
    trace_path = tmp_path / "trace.json"
    output_path = tmp_path / "memory_ingress_diagnostic.json"
    trace_path.write_text(
        json.dumps(_synthetic_manager_trace(), ensure_ascii=False),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_runtime_lab_memory_trace_ingress_diagnostic.py"),
            "--trace-json",
            str(trace_path),
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
    assert artifact["status"] == "pass"
    assert artifact["runtime_connected"] is True
    assert artifact["lab_isolated"] is True
    assert artifact["live_invoked"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["canonical_mutation_changed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["shadow_memory_context_pack_used"] is False


def test_trace_ingress_stays_out_of_active_manager_imports() -> None:
    active_surfaces = [
        ROOT / "app" / "main.py",
        ROOT / "app" / "routes.py",
        ROOT / "app" / "schemas.py",
        ROOT / "app" / "composition" / "intake_routes.py",
        ROOT / "app" / "composition" / "intake_execution_orchestrator.py",
        ROOT / "app" / "composition" / "intake_turn_orchestrator.py",
        ROOT / "app" / "runtime" / "application" / "manager_service.py",
        ROOT / "app" / "runtime" / "agent" / "manager.py",
    ]
    forbidden_import = "app.memory.application.runtime_lab_trace_ingress"

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
