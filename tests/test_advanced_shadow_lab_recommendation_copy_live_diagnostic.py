from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.recommendation_copy_live_diagnostic import (
    run_recommendation_copy_live_diagnostic,
)


class FakeRecommendationCopyDiagnosticProvider:
    def __init__(self, response: Mapping[str, Any] | None = None) -> None:
        self.response = dict(response or _default_model_response())
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-recommendation-copy", "configured": True}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        self.calls.append({"stage": kwargs.get("stage")})
        return dict(self.response), {"stage": "advanced_shadow_recommendation_copy_live_diagnostic", "provider": "fake"}


def test_recommendation_copy_live_diagnostic_records_fake_provider_artifact(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "recommendation_copy_live_diagnostic.json"

    artifact = run_recommendation_copy_live_diagnostic(
        recommendation_summary_report=_summary_report(),
        output_path=output_path,
        provider=FakeRecommendationCopyDiagnosticProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert json.loads(output_path.read_text(encoding="utf-8")) == artifact
    assert artifact["artifact_type"] == (
        "advanced_shadow_recommendation_copy_live_diagnostic_artifact"
    )
    assert artifact["status"] == "pass"
    assert artifact["target_surface"] == "recommendation_prompt_reason_copy"
    assert artifact["provider_mode"] == "fake_provider_contract_test"
    assert artifact["live_invoked"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["provider_invoked"] is True
    assert artifact["output_guard"]["status"] == "pass"
    assert artifact["model_output_summary"]["candidate_id"] == "golden-1"
    assert artifact["model_output_summary"]["draft_prompt_present"] is True
    assert artifact["source_candidate_count"] == 1
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["scheduler_enabled"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert "private dogfood wording" not in serialized
    assert "raw_menu_blob" not in serialized


def test_recommendation_copy_live_diagnostic_blocks_model_action_language() -> None:
    provider = FakeRecommendationCopyDiagnosticProvider(
        response={
            "candidate_id": "golden-1",
            "draft_prompt": "I sent this FamilyMart option to the user.",
            "reason_summary": "This should be delivered now.",
            "claim_scope": "user_facing",
            "action_request": False,
            "delivery_request": True,
            "mutation_request": False,
            "reason_codes": ["matches_preference"],
        }
    )

    artifact = run_recommendation_copy_live_diagnostic(
        recommendation_summary_report=_summary_report(),
        provider=provider,
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "blocked"
    assert artifact["output_guard"]["status"] == "blocked"
    assert artifact["blockers"] == [
        "model_output.claim_scope_not_diagnostic",
        "model_output.delivery_request_not_allowed",
        "model_output.delivery_language_present",
    ]
    assert artifact["recommendation_served"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["user_facing_behavior_changed"] is False


def test_recommendation_copy_live_diagnostic_blocks_input_claim_drift() -> None:
    provider = FakeRecommendationCopyDiagnosticProvider()
    report = _summary_report()
    report["recommendation_served"] = True
    report["manager_context_packet_changed"] = True

    artifact = run_recommendation_copy_live_diagnostic(
        recommendation_summary_report=report,
        provider=provider,
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert provider.calls == []
    assert artifact["status"] == "blocked"
    assert artifact["provider_invoked"] is False
    assert artifact["blockers"] == [
        "recommendation_summary.recommendation_served",
        "recommendation_summary.manager_context_packet_changed",
    ]
    assert artifact["live_provider_used"] is False
    assert artifact["recommendation_served"] is False


def test_recommendation_copy_live_diagnostic_runner_is_manual_env_gated() -> None:
    source = Path(
        "scripts/run_advanced_shadow_lab_recommendation_copy_live_diagnostic.py"
    ).read_text(encoding="utf-8")

    assert "ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC" in source
    assert "--allow-live-provider" in source
    assert "app.runtime.interface.provider_runtime" not in source
    assert "app.routes" not in source
    assert "scheduler" not in source.lower()
    assert "recommendation_served=True" not in source
    assert "user_facing_behavior_changed=True" not in source


def _summary_report() -> dict[str, object]:
    return {
        "artifact_type": "recommendation_shadow_summary_consumer_quality_report",
        "status": "pass",
        "candidate_count": 1,
        "primary_candidate_id": "golden-1",
        "candidate_evaluations": [
            {
                "candidate_id": "golden-1",
                "title": "Chicken salad",
                "store_name": "FamilyMart",
                "estimated_kcal": 520,
                "quality_gate_passed": True,
                "quality_tier": "high",
                "proactive_intensity": "offer",
                "presentation_posture": "shadow_activation_candidate",
                "quality_signals": [
                    "memory_positive_summary_match",
                    "memory_golden_order_projection_match",
                ],
                "source_refs": [
                    "memory_candidate:pref-1",
                    "memory_candidate:golden-1",
                ],
                "store_metadata": {
                    "chain": "familymart",
                    "raw_menu_blob": "hidden",
                },
                "private_note": "private dogfood wording",
                "recommendation_served": False,
                "intake_handoff_created": False,
            }
        ],
        "pool_decision": "offer",
        "recommendation_served": False,
        "proactive_sent": False,
        "manager_context_packet_changed": False,
        "durable_memory_written": False,
        "mutation_changed": False,
    }


def _default_model_response() -> dict[str, object]:
    return {
        "candidate_id": "golden-1",
        "draft_prompt": "Consider the FamilyMart chicken salad as a low-friction option.",
        "reason_summary": "It matches preference and budget, and stays review-only.",
        "claim_scope": "diagnostic_copy_only",
        "action_request": False,
        "delivery_request": False,
        "mutation_request": False,
        "reason_codes": ["matches_preference", "within_budget", "review_only"],
    }
