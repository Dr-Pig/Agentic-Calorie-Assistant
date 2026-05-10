from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.proactive_copy_live_diagnostic import (
    run_proactive_copy_live_diagnostic,
)


class FakeProactiveCopyDiagnosticProvider:
    def __init__(self, response: Mapping[str, Any] | None = None) -> None:
        self.response = dict(response or _default_model_response())
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-proactive-copy", "configured": True}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        self.calls.append({"stage": kwargs.get("stage")})
        return dict(self.response), {
            "stage": "advanced_shadow_proactive_copy_live_diagnostic",
            "provider": "fake",
        }


def test_proactive_copy_live_diagnostic_records_fake_provider_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "proactive_copy_live_diagnostic.json"

    artifact = run_proactive_copy_live_diagnostic(
        no_send_review_sink=_review_sink(),
        output_path=output_path,
        provider=FakeProactiveCopyDiagnosticProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert json.loads(output_path.read_text(encoding="utf-8")) == artifact
    assert artifact["artifact_type"] == "advanced_shadow_proactive_copy_live_diagnostic_artifact"
    assert artifact["status"] == "pass"
    assert artifact["target_surface"] == "proactive_chat_copy_posture"
    assert artifact["provider_mode"] == "fake_provider_contract_test"
    assert artifact["live_invoked"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["provider_invoked"] is True
    assert artifact["source_record_count"] == 2
    assert artifact["control_path_summary"]["configured_paths"] == {
        "dismiss": True,
        "snooze": True,
        "undo": True,
    }
    assert artifact["model_output_summary"]["draft_chat_message_present"] is True
    assert artifact["model_output_summary"]["false_positive_silence_case_present"] is True
    assert artifact["model_output_summary"]["next_signal_present"] is True
    assert artifact["output_guard"]["status"] == "pass"
    assert artifact["proactive_sent"] is False
    assert artifact["scheduler_enabled"] is False
    assert artifact["scheduler_enqueued"] is False
    assert artifact["durable_snooze_written"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert "private proactive wording" not in serialized


def test_proactive_copy_live_diagnostic_blocks_send_schedule_and_mutation_language() -> None:
    provider = FakeProactiveCopyDiagnosticProvider(
        response={
            "draft_chat_message": "I sent and scheduled this prompt.",
            "reason_summary": "Saved it and updated your budget.",
            "false_positive_silence_case": "",
            "next_signal": "",
            "claim_scope": "user_facing",
            "action_request": True,
            "delivery_request": True,
            "mutation_request": True,
            "scheduler_request": True,
            "notification_request": True,
            "reason_codes": ["unsafe_action"],
        }
    )

    artifact = run_proactive_copy_live_diagnostic(
        no_send_review_sink=_review_sink(),
        provider=provider,
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "blocked"
    assert artifact["output_guard"]["status"] == "blocked"
    assert artifact["blockers"] == [
        "model_output.claim_scope_not_diagnostic",
        "model_output.action_request_not_allowed",
        "model_output.delivery_request_not_allowed",
        "model_output.mutation_request_not_allowed",
        "model_output.scheduler_request_not_allowed",
        "model_output.notification_request_not_allowed",
        "model_output.false_positive_silence_case_missing",
        "model_output.next_signal_missing",
        "model_output.delivery_language_present",
        "model_output.scheduler_language_present",
        "model_output.mutation_language_present",
    ]
    assert artifact["proactive_sent"] is False
    assert artifact["scheduler_enqueued"] is False
    assert artifact["mutation_changed"] is False


def test_proactive_copy_live_diagnostic_blocks_input_claim_drift() -> None:
    provider = FakeProactiveCopyDiagnosticProvider()
    sink = _review_sink()
    sink["proactive_sent"] = True
    sink["durable_snooze_written"] = True

    artifact = run_proactive_copy_live_diagnostic(
        no_send_review_sink=sink,
        provider=provider,
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert provider.calls == []
    assert artifact["status"] == "blocked"
    assert artifact["provider_invoked"] is False
    assert artifact["blockers"] == [
        "no_send_review_sink.proactive_sent",
        "no_send_review_sink.durable_snooze_written",
    ]
    assert artifact["live_provider_used"] is False
    assert artifact["proactive_sent"] is False


def test_proactive_copy_live_diagnostic_requires_no_send_control_paths() -> None:
    sink = _review_sink()
    sink["control_path_evidence"] = {"status": "pass", "configured_paths": {"dismiss": True}}

    artifact = run_proactive_copy_live_diagnostic(
        no_send_review_sink=sink,
        provider=FakeProactiveCopyDiagnosticProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert artifact["status"] == "blocked"
    assert artifact["provider_invoked"] is False
    assert artifact["blockers"] == [
        "control_path_evidence.snooze_not_configured",
        "control_path_evidence.undo_not_configured",
        "control_path_evidence.next_signal_missing",
    ]


def _review_sink() -> dict[str, object]:
    return {
        "artifact_type": "proactive_no_send_review_sink_artifact",
        "status": "pass",
        "record_count": 2,
        "records": [
            {
                "trigger_type": "recommendation_prompt",
                "candidate_kind": "recommendation_prompt_review",
                "interaction_action": "dismiss",
                "next_signal_required": "new_app_open_with_qualified_pool",
                "dismiss_reason_choices_present": True,
                "snooze_window_present": True,
                "undo_scope": "current_no_send_candidate_only",
                "private_note": "private proactive wording",
            },
            {
                "trigger_type": "rescue_nudge",
                "candidate_kind": "rescue_nudge_review",
                "interaction_action": "snooze",
                "next_signal_required": "material_budget_change_or_user_reopens_rescue",
                "dismiss_reason_choices_present": True,
                "snooze_window_present": True,
                "undo_scope": "current_no_send_candidate_only",
            },
        ],
        "control_path_evidence": {
            "status": "pass",
            "configured_paths": {"dismiss": True, "snooze": True, "undo": True},
            "interaction_actions_observed": ["dismiss", "snooze"],
            "next_signal_required_present": True,
        },
        "proactive_sent": False,
        "scheduler_enabled": False,
        "scheduler_enqueued": False,
        "durable_snooze_written": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _default_model_response() -> dict[str, object]:
    return {
        "draft_chat_message": "A review-only prompt could be useful later.",
        "reason_summary": "It has no-send controls and a clear next signal.",
        "false_positive_silence_case": "Stay silent if the user already handled it.",
        "next_signal": "Wait for a new app-open or material budget signal.",
        "claim_scope": "diagnostic_copy_only",
        "action_request": False,
        "delivery_request": False,
        "mutation_request": False,
        "scheduler_request": False,
        "notification_request": False,
        "reason_codes": ["chat_first", "review_only"],
    }
