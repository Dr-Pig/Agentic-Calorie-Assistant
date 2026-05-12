from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.shared.infra.json_artifacts import read_json_artifact


ROOT = Path(__file__).resolve().parents[1]
ALLOW_ENV = "ADVANCED_PRODUCT_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
SCRIPT = "scripts/run_advanced_product_lab_integrated_live_e2e.py"


def test_integrated_live_e2e_fake_diagnostic_closes_memory_product_loop() -> None:
    from app.advanced_shadow_lab.product_lab_integrated_live_e2e import (
        FakeIntegratedLiveE2EProvider,
        run_integrated_live_e2e,
    )

    artifact = run_integrated_live_e2e(
        provider=FakeIntegratedLiveE2EProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    assert artifact["status"] == "pass"
    assert artifact["integrated_loop_closed"] is True
    assert artifact["component_statuses"] == {
        "memory_tool_lookup": "pass",
        "recommendation_blocker": "pass",
        "rescue_memory_context": "pass",
        "proactive_feedback": "pass",
        "product_lab_turn": "pass",
    }
    assert artifact["product_lab_turn_summary"]["lab_user_facing_behavior_changed"] is True
    assert artifact["provider_review_summary"]["integrated_loop_closed"] is True
    assert artifact["provider_review_summary"]["canonical_mutation_allowed"] is False
    assert artifact["lab_enabled"] is True
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["diagnostic_evidence_class"] == "fake_contract"


def test_integrated_live_e2e_blocks_provider_review_that_activates_mainline() -> None:
    from app.advanced_shadow_lab.product_lab_integrated_live_e2e import (
        FakeIntegratedLiveE2EProvider,
        run_integrated_live_e2e,
    )

    artifact = run_integrated_live_e2e(
        provider=FakeIntegratedLiveE2EProvider(corrupt_review=True),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    assert artifact["status"] == "blocked"
    assert "provider_review.mainline_activation_enabled" in artifact["blockers"]
    assert "provider_review.canonical_mutation_allowed" in artifact["blockers"]


def test_integrated_live_e2e_payload_separates_lab_memory_from_durable_memory() -> None:
    from app.advanced_shadow_lab.product_lab_integrated_live_e2e import (
        run_integrated_live_e2e,
    )

    provider = _CapturingIntegratedProvider()

    artifact = run_integrated_live_e2e(
        provider=provider,
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )

    assert artifact["status"] == "pass"
    assert provider.user_payload["activation_boundary"] == {
        "lab_memory_context_injected": True,
        "lab_user_facing_behavior_changed": True,
        "mainline_activation_enabled": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "scheduler_delivery_allowed": False,
    }


def test_integrated_live_e2e_cli_fake_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "integrated-live-e2e-fake.json"

    result = subprocess.run(
        [sys.executable, SCRIPT, "--output", str(output), "--provider-mode", "fake"],
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
    assert artifact["live_integrated_e2e_pass"] is False
    assert artifact["live_edd_preflight"]["reviewed_preflight_status"] == (
        "fake_contract_preflight_passed_non_live"
    )


def test_integrated_live_e2e_cli_blocks_live_without_gate(tmp_path: Path) -> None:
    output = tmp_path / "integrated-live-e2e-blocked-live.json"

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
    assert artifact["blockers"] == ["live_gate_not_enabled"]
    assert artifact["diagnostic_evidence_class"] == "blocked_not_invoked"


class _CapturingIntegratedProvider:
    def __init__(self) -> None:
        self.user_payload: dict[str, object] = {}

    def readiness(self) -> dict[str, object]:
        return {"provider": "capturing-integrated", "configured": True}

    async def complete_with_trace(
        self,
        **kwargs: object,
    ) -> tuple[dict[str, object], dict[str, object]]:
        self.user_payload = dict(kwargs["user_payload"])  # type: ignore[index]
        return {
            "integrated_loop_closed": True,
            "mainline_activation_enabled": False,
            "canonical_mutation_allowed": False,
            "durable_product_memory_written": False,
            "scheduler_delivery_allowed": False,
            "answer_summary": "Integrated lab loop stays inside the lab.",
            "risk_notes": "No durable product memory write.",
            "claim_scope": "diagnostic_only",
        }, {"stage": "advanced_product_lab_integrated_live_e2e", "provider": "capturing"}
