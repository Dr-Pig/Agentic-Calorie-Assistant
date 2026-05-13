from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.shared.infra.json_artifacts import read_json_artifact


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "scripts/run_advanced_product_lab_manager_turn_grokfast_diagnostic.py"
ALLOW_ENV = "ADVANCED_PRODUCT_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"


def test_manager_turn_grokfast_fake_provider_contract() -> None:
    from app.advanced_shadow_lab.product_lab_manager_turn_grokfast_diagnostic import (
        run_manager_turn_grokfast_diagnostic,
    )

    artifact = run_manager_turn_grokfast_diagnostic(
        runtime_artifact=_runtime_artifact(),
        provider=_FakeManagerTurnProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    assert artifact["artifact_type"] == (
        "advanced_product_lab_manager_turn_grokfast_diagnostic"
    )
    assert artifact["status"] == "pass"
    assert artifact["diagnostic_evidence_class"] == "fake_contract"
    assert artifact["live_grokfast_diagnostic_pass"] is False
    assert artifact["provider_invoked"] is True
    assert artifact["source_manager_tool_order"] == [
        "memory.search",
        "reusable_meal.search",
        "rescue.run",
    ]
    assert artifact["model_output_summary"]["claim_scope"] == "diagnostic_only"
    assert artifact["output_guard"] == {"status": "pass", "blockers": []}
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_manager_turn_grokfast_payload_is_bounded_runtime_summary() -> None:
    from app.advanced_shadow_lab.product_lab_manager_turn_live_payload import (
        manager_turn_live_provider_payload,
    )

    payload = manager_turn_live_provider_payload(
        _runtime_artifact(),
        constraints={"claim_scope_required": "diagnostic_only"},
    )
    serialized = json.dumps(payload, ensure_ascii=False)

    assert payload["runtime_summary"]["manager_tool_order"] == [
        "memory.search",
        "reusable_meal.search",
        "rescue.run",
    ]
    assert "same as before plus help me recover today" not in serialized
    assert "raw_transcript" not in serialized
    assert payload["constraints"]["claim_scope_required"] == "diagnostic_only"


def test_manager_turn_grokfast_cli_blocks_live_without_gate(tmp_path: Path) -> None:
    output = tmp_path / "blocked-live-manager-turn.json"

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--output",
            str(output),
            "--provider-mode",
            "live",
            "--allow-live-provider",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={key: value for key, value in os.environ.items() if key != ALLOW_ENV},
    )

    assert result.returncode == 0, result.stderr
    artifact = read_json_artifact(output)
    assert artifact["status"] == "blocked"
    assert artifact["provider_mode"] == "not_invoked"
    assert artifact["provider_invoked"] is False
    assert artifact["blockers"] == ["live_gate_not_enabled"]
    assert artifact["live_grokfast_diagnostic_pass"] is False


def test_manager_turn_grokfast_cli_fake_mode_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "fake-manager-turn.json"

    result = subprocess.run(
        [
            sys.executable,
            SCRIPT,
            "--output",
            str(output),
            "--provider-mode",
            "fake",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout = json.loads(result.stdout)
    artifact = read_json_artifact(output)
    assert stdout["status"] == "pass"
    assert artifact["status"] == "pass"
    assert artifact["provider_profile_id"] == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
    assert artifact["source_manager_tool_order"] == [
        "memory.search",
        "reusable_meal.search",
        "rescue.run",
    ]


class _FakeManagerTurnProvider:
    def readiness(self) -> dict[str, object]:
        return {"provider": "fake-manager-turn-grokfast", "configured": True}

    async def complete_with_trace(self, **_: object) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "claim_scope": "diagnostic_only",
            "selected_capabilities": ["memory", "reusable_meal", "rescue"],
            "tool_call_order": ["memory.search", "reusable_meal.search", "rescue.run"],
            "manager_turn_summary": "Memory, reusable meal, and rescue returned to Manager.",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "risk_notes": "Diagnostic evidence only.",
        }, {"stage": "advanced_product_lab_manager_turn_diagnostic", "provider": "fake"}


def _runtime_artifact() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_turn_artifact",
        "status": "pass",
        "semantic_intent_fixture": "repeat_meal_rescue_shadow",
        "manager_tool_loop_source_refs": [
            "manager_tool_call:memory-search-1:memory.search",
            "manager_tool_call:reusable-meal-search-1:reusable_meal.search",
            "manager_tool_call:rescue-1:rescue.run",
        ],
        "compiled_default_manager_script": {
            "requested_capabilities": ["memory", "reusable_meal", "rescue"],
        },
        "manager_selected_memory_context_adapter": {
            "memory_record_summary": {"selected_record_ids": ["reusable-meal-hint-1"]},
        },
        "manager_selected_reusable_meal_artifact": {
            "reusable_meal_candidates": [
                {
                    "entity_id": "ufe-fried-rice",
                    "estimate_posture_decision": "reuse_exact",
                }
            ],
        },
        "manager_selected_rescue_artifact": {
            "proposal_presented_to_lab": True,
            "primary_actions": ["accept_rescue_plan", "dismiss_rescue_plan"],
        },
        "mainline_runtime_connected": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }
