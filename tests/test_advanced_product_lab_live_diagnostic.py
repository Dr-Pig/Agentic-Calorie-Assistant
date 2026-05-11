from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
)
from app.advanced_shadow_lab.product_lab_live_diagnostic import (
    run_product_lab_live_diagnostic,
)
from app.shared.infra.json_artifacts import read_json_artifact


ROOT = Path(__file__).resolve().parents[1]


def test_product_lab_live_diagnostic_blocks_without_live_gate(
    tmp_path: Path,
) -> None:
    summary = _write_simulated_pack(tmp_path)
    output = tmp_path / "blocked_live.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_product_lab_live_diagnostic.py",
            "--summary",
            str(summary),
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
        env={key: value for key, value in os.environ.items() if key != _ALLOW_ENV},
    )

    assert result.returncode == 0, result.stderr
    stdout = json.loads(result.stdout)
    artifact = read_json_artifact(output)
    assert stdout["status"] == "blocked"
    assert artifact["artifact_type"] == "advanced_product_lab_live_diagnostic_artifact"
    assert artifact["status"] == "blocked"
    assert artifact["provider_mode"] == "not_invoked"
    assert artifact["live_invoked"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["blockers"] == ["live_gate_not_enabled"]
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["production_db_migration_allowed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_product_lab_live_diagnostic_rejects_kimi_profile_before_input_read(
    tmp_path: Path,
) -> None:
    output = tmp_path / "blocked_kimi.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_product_lab_live_diagnostic.py",
            "--summary",
            str(tmp_path / "missing_summary.json"),
            "--output",
            str(output),
            "--provider-mode",
            "live",
            "--allow-live-provider",
            "--provider-profile-id",
            ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, _ALLOW_ENV: "1"},
    )

    assert result.returncode == 0
    artifact = read_json_artifact(output)
    assert artifact["status"] == "blocked"
    assert artifact["provider_mode"] == "not_invoked"
    assert artifact["blockers"] == [
        "profile_not_live_diagnostic_allowed;kimi_live_calls_forbidden"
    ]
    assert "No such file" not in result.stderr


def test_product_lab_live_diagnostic_fake_provider_contract(
    tmp_path: Path,
) -> None:
    summary = _write_simulated_pack(tmp_path)
    output = tmp_path / "fake_live_contract.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_product_lab_live_diagnostic.py",
            "--summary",
            str(summary),
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
    artifact = read_json_artifact(output)
    assert artifact["status"] == "pass"
    assert artifact["provider_mode"] == "fake_provider_contract_test"
    assert artifact["live_invoked"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["provider_invoked"] is True
    assert artifact["source_summary_artifact_type"] == (
        "advanced_product_lab_simulated_dogfood_summary"
    )
    assert artifact["lab_user_facing_behavior_changed"] is True
    assert artifact["lab_memory_store_written"] is True
    assert artifact["memory_context_injected"] is True
    assert artifact["model_input_policy"] == {
        "claim_scope_required": "diagnostic_only",
        "lab_user_facing_output_allowed": True,
        "outside_lab_delivery_allowed": False,
        "mutation_or_commit_allowed": False,
    }
    assert artifact["model_output_summary"] == {
        "diagnostic_notes_present": True,
        "risk_notes_present": True,
        "claim_scope": "diagnostic_only",
    }
    assert artifact["output_guard"] == {"status": "pass", "blockers": []}
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_product_lab_live_diagnostic_payload_includes_product_runtime_summary(
    tmp_path: Path,
) -> None:
    summary = read_json_artifact(_write_simulated_pack(tmp_path))
    provider = _CapturingProvider()

    artifact = run_product_lab_live_diagnostic(
        summary_artifact=summary,
        provider=provider,
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "pass"
    assert provider.user_payload["product_runtime_summary"] == {
        "capabilities_exercised": [
            "long_term_memory",
            "recommendation",
            "rescue",
            "proactive",
            "chat_surface",
        ],
        "recommendation_selected_candidate_ids": [
            "golden-1",
            "golden-breakfast-oatmeal",
            "golden-breakfast-oatmeal",
            "golden-breakfast-oatmeal",
        ],
        "proactive_candidate_counts": [2, 3, 2, 2],
        "outputs_applied_to_chat_surface": True,
        "recommendation_intake_handoff_created": True,
        "rescue_commit_handoff_created": True,
        "proactive_delivery_packet_ready": True,
    }
    assert provider.user_payload["chat_action_summary"] == {
        "action_outcome_count": 5,
        "action_outcome_types": [
            "recommendation_intake_draft",
            "rescue_shorter_plan_requested",
            "rescue_explanation_requested",
            "pending_intake_confirmed_lab",
            "rescue_commit_confirmation",
        ],
        "rescue_action_decision_kinds": [
            "request_shorter_variant",
            "request_explanation",
            "pending_rescue_commit_confirmation",
        ],
        "canonical_mutation_allowed": False,
        "blockers": [],
    }
    assert provider.user_payload["product_loop_closure"] == {
        "closed": True,
        "missing": [],
        "criteria": {
            "session_passed": True,
            "memory_store_written": True,
            "memory_context_injected": True,
            "recommendation_selected": True,
            "recommendation_intake_action_replayed": True,
            "pending_intake_terminal_replayed": True,
            "rescue_commit_action_replayed": True,
            "rescue_negotiation_posture_replayed": True,
            "proactive_chat_delivery_ready": True,
            "chat_surface_outputs_applied": True,
            "activation_wall_intact": True,
            "no_chat_action_blockers": True,
        },
    }
    assert artifact["source_product_loop_closed"] is True
    policy = artifact["model_profile_policy"]
    assert policy["diagnostic_live_model"] == "grok-4-fast"
    assert policy["target_reasoning_model"] == "kimi-k2.5"
    assert policy["provider_dependency_inversion_required"] is True
    assert policy["kimi_live_calls_allowed"] is False


def test_product_lab_live_diagnostic_blocks_unclosed_product_loop(
    tmp_path: Path,
) -> None:
    summary = read_json_artifact(_write_simulated_pack(tmp_path))
    summary["advanced_product_lab_product_loop_closed"] = False
    summary["advanced_product_lab_closure_missing"] = [
        "rescue_commit_action_replayed"
    ]
    provider = _CapturingProvider()

    artifact = run_product_lab_live_diagnostic(
        summary_artifact=summary,
        provider=provider,
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "blocked"
    assert artifact["provider_invoked"] is False
    assert artifact["blockers"] == [
        "summary.product_loop_not_closed:rescue_commit_action_replayed"
    ]
    assert provider.user_payload == {}


def test_product_lab_live_diagnostic_output_guard_allows_negated_claim_words(
    tmp_path: Path,
) -> None:
    summary = read_json_artifact(_write_simulated_pack(tmp_path))

    artifact = run_product_lab_live_diagnostic(
        summary_artifact=summary,
        provider=_StaticProvider(
            diagnostic_notes="Lab chat output was reviewed, not sent.",
            risk_notes="No mutation was committed or saved to product state.",
        ),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "pass"
    assert artifact["output_guard"] == {"status": "pass", "blockers": []}


def test_product_lab_live_diagnostic_output_guard_blocks_affirmative_claim_words(
    tmp_path: Path,
) -> None:
    summary = read_json_artifact(_write_simulated_pack(tmp_path))

    artifact = run_product_lab_live_diagnostic(
        summary_artifact=summary,
        provider=_StaticProvider(
            diagnostic_notes="The nudge was delivered to the user.",
            risk_notes="The rescue plan was saved to product state.",
        ),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "blocked"
    assert artifact["output_guard"]["blockers"] == [
        "model_output.delivery_language_present",
        "model_output.mutation_language_present",
    ]


def test_product_lab_live_diagnostic_writes_provider_error_artifact(
    tmp_path: Path,
) -> None:
    summary = read_json_artifact(_write_simulated_pack(tmp_path))
    output = tmp_path / "provider_error.json"

    artifact = run_product_lab_live_diagnostic(
        summary_artifact=summary,
        provider=_FailingProvider(),
        provider_mode="builderspace-grok-4-fast-advanced-shadow-lab-live-diagnostic",
        live_invoked=True,
        output_path=output,
    )

    assert artifact["status"] == "provider_error"
    assert artifact["provider_invoked"] is True
    assert artifact["live_provider_used"] is True
    assert artifact["provider_error"]["type"] == "RuntimeError"
    assert artifact["output_guard"] == {"status": "not_run", "blockers": []}
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert read_json_artifact(output)["status"] == "provider_error"


def _write_simulated_pack(tmp_path: Path) -> Path:
    output_root = tmp_path / "operator-pack"
    summary = tmp_path / "summary.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_advanced_product_lab_simulated_dogfood.py",
            "--output-root",
            str(output_root),
            "--summary-output",
            str(summary),
            "--session-id",
            "live-diag-session",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return summary


class _FailingProvider:
    def readiness(self) -> dict[str, object]:
        return {"provider": "failing", "configured": True}

    async def complete_with_trace(self, **_: object) -> tuple[dict[str, object], dict[str, object]]:
        raise RuntimeError("provider boom")


class _CapturingProvider:
    def __init__(self) -> None:
        self.user_payload: dict[str, object] = {}

    def readiness(self) -> dict[str, object]:
        return {"provider": "capturing", "configured": True}

    async def complete_with_trace(
        self,
        **kwargs: object,
    ) -> tuple[dict[str, object], dict[str, object]]:
        self.user_payload = dict(kwargs["user_payload"])  # type: ignore[index]
        return {
            "diagnostic_notes": "The isolated product lab surface used product outputs.",
            "risk_notes": "Review only.",
            "claim_scope": "diagnostic_only",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "reason_codes": ["review_only"],
        }, {"stage": "advanced_product_lab_live_diagnostic", "provider": "capturing"}


class _StaticProvider:
    def __init__(self, *, diagnostic_notes: str, risk_notes: str) -> None:
        self.diagnostic_notes = diagnostic_notes
        self.risk_notes = risk_notes

    def readiness(self) -> dict[str, object]:
        return {"provider": "static", "configured": True}

    async def complete_with_trace(
        self,
        **_: object,
    ) -> tuple[dict[str, object], dict[str, object]]:
        return {
            "diagnostic_notes": self.diagnostic_notes,
            "risk_notes": self.risk_notes,
            "claim_scope": "diagnostic_only",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "reason_codes": ["review_only"],
        }, {"stage": "advanced_product_lab_live_diagnostic", "provider": "static"}


_ALLOW_ENV = "ADVANCED_PRODUCT_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
