from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from app.runtime.application.proactive_no_send_shadow_evaluator import (
    ProactiveNoSendShadowInput,
    build_proactive_no_send_simulation,
)
from app.runtime.application.proactive_recommendation_prompt_bridge import (
    NO_RECOMMENDATION_PROMPT_REVIEW,
)
from app.runtime.application.proactive_rescue_nudge_bridge import (
    NO_RESCUE_NUDGE_REVIEW,
)
from scripts.build_proactive_no_send_decision_pack import (
    build_proactive_no_send_decision_pack,
    write_proactive_no_send_decision_pack,
)


def _artifact_with_review_candidate() -> dict[str, object]:
    return build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="recommendation_prompt",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
                lower_frequency_ready=True,
                delivery_surface="app_open",
                recommendation_prompt_review={
                    **NO_RECOMMENDATION_PROMPT_REVIEW,
                    "source_report_used": True,
                    "status": "candidate_for_human_review",
                    "recommendation_pool_decision": "primary_plus_backup",
                    "prompt_posture": "invitation_only",
                },
            )
        ]
    )


def _artifact_with_copy_suppression() -> dict[str, object]:
    return build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="weekly_insight",
                wake_source="scheduled_check",
                user_relevant_reason="weekly_summary_expected_after_enough_data",
                candidate_copy="You must stop eating like this.",
                copy_posture="directive",
                copy_has_user_agency=False,
                copy_has_no_shame=False,
            )
        ]
    )


def _artifact_with_prompt_review(review: dict[str, object] | None) -> dict[str, object]:
    return build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="recommendation_prompt",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
                lower_frequency_ready=True,
                delivery_surface="app_open",
                recommendation_prompt_review=review,
            )
        ]
    )


def _artifact_with_rescue_review(review: dict[str, object] | None) -> dict[str, object]:
    return build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="rescue_nudge",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
                rescue_nudge_review=review,
            )
        ]
    )


def _prompt_review(
    status: str,
    *,
    suppression_reason: str | None = None,
    blocker: str | None = None,
) -> dict[str, object]:
    return {
        **NO_RECOMMENDATION_PROMPT_REVIEW,
        "source_report_used": True,
        "status": status,
        "recommendation_pool_decision": (
            "silent_no_qualified_candidate"
            if status == "suppressed"
            else "primary_plus_backup"
        ),
        "prompt_posture": "invitation_only" if status == "candidate_for_human_review" else "silent",
        "suppression_reasons": [suppression_reason] if suppression_reason else [],
        "blockers": [blocker] if blocker else [],
    }


def _rescue_review(
    status: str,
    *,
    suppression_reason: str | None = None,
    blocker: str | None = None,
) -> dict[str, object]:
    return {
        **NO_RESCUE_NUDGE_REVIEW,
        "source_projection_used": True,
        "status": status,
        "prompt_posture": "later_only_review_context" if status == "context_available" else "silent",
        "suppression_reasons": [suppression_reason] if suppression_reason else [],
        "blockers": [blocker] if blocker else [],
        "history_review_notes": ["private rescue note should not be in decision pack"],
    }


def test_decision_pack_keeps_single_no_send_run_out_of_live_promotion() -> None:
    pack = build_proactive_no_send_decision_pack([_artifact_with_review_candidate()])

    assert pack["artifact_type"] == "proactive_no_send_decision_pack"
    assert pack["shadow_mode"] is True
    assert pack["live_delivery_allowed"] is False
    assert pack["scheduler_activation_allowed"] is False
    assert pack["promotion_allowed"] is False
    assert pack["summary"]["run_count"] == 1
    assert pack["summary"]["candidate_for_human_review_trigger_types"] == ["recommendation_prompt"]
    assert pack["promotion_gate"] == {
        "minimum_clean_shadow_runs": 3,
        "human_review_required": True,
        "repeated_clean_shadow_evidence": False,
        "promotion_blockers": [
            "human_review_required_before_live_delivery",
            "live_scheduler_not_enabled",
            "minimum_clean_shadow_runs_not_met",
            "no_send_shadow_only",
        ],
    }


def test_decision_pack_rejects_overclaiming_or_side_effectful_inputs() -> None:
    overclaiming = _artifact_with_review_candidate()
    overclaiming["product_readiness_claimed"] = True
    side_effectful = _artifact_with_review_candidate()
    side_effectful["proactive_sent"] = True

    pack = build_proactive_no_send_decision_pack([overclaiming, side_effectful])

    assert pack["input_integrity"]["passed"] is False
    assert "run_1_product_readiness_claimed" in pack["input_integrity"]["blockers"]
    assert "run_2_proactive_sent" in pack["input_integrity"]["blockers"]
    assert pack["promotion_allowed"] is False


def test_decision_pack_summarizes_recommendation_prompt_review_posture() -> None:
    suppressed = _prompt_review(
        "suppressed",
        suppression_reason="recommendation_pool_silent_no_qualified_candidate",
    )
    blocked = _prompt_review(
        "blocked",
        blocker="recommendation_quality_report.recommendation_served",
    )
    pack = build_proactive_no_send_decision_pack(
        [
            _artifact_with_prompt_review(_prompt_review("candidate_for_human_review")),
            _artifact_with_prompt_review(suppressed),
            _artifact_with_prompt_review(blocked),
            _artifact_with_prompt_review({**NO_RECOMMENDATION_PROMPT_REVIEW}),
            _artifact_with_prompt_review(None),
        ]
    )

    assert pack["artifact_type"] == "proactive_no_send_decision_pack"
    assert pack["summary"]["recommendation_prompt_review_status_counts"] == {
        "blocked": 1,
        "candidate_for_human_review": 1,
        "not_evaluated": 2,
        "suppressed": 1,
    }
    assert pack["summary"]["recommendation_prompt_suppression_reason_counts"] == {
        "recommendation_pool_silent_no_qualified_candidate": 1
    }
    assert pack["summary"]["recommendation_prompt_blocker_counts"] == {
        "recommendation_quality_report.recommendation_served": 1
    }
    assert pack["live_delivery_allowed"] is False
    assert pack["scheduler_activation_allowed"] is False
    assert pack["promotion_allowed"] is False


def test_decision_pack_does_not_leak_prompt_review_candidate_details() -> None:
    review = _prompt_review(
        "blocked",
        blocker="recommendation_quality_report.recommendation_served",
    )
    review["candidate_ids"] = ["hidden-candidate-123"]
    review["candidate_copy"] = "Hidden candidate copy should not be surfaced."

    pack = build_proactive_no_send_decision_pack([_artifact_with_prompt_review(review)])
    pack_text = json.dumps(pack, sort_keys=True)

    assert "hidden-candidate-123" not in pack_text
    assert "Hidden candidate copy" not in pack_text
    assert pack["summary"]["recommendation_prompt_blocker_counts"] == {
        "recommendation_quality_report.recommendation_served": 1
    }


def test_decision_pack_summarizes_rescue_nudge_review_posture() -> None:
    suppressed = _rescue_review(
        "suppressed",
        suppression_reason="rescue_context_not_actionable",
    )
    blocked = _rescue_review(
        "blocked",
        blocker="rescue_projection.day_budget_mutated",
    )
    pack = build_proactive_no_send_decision_pack(
        [
            _artifact_with_rescue_review(_rescue_review("context_available")),
            _artifact_with_rescue_review(suppressed),
            _artifact_with_rescue_review(blocked),
            _artifact_with_rescue_review(None),
        ]
    )
    pack_text = json.dumps(pack, sort_keys=True)

    assert pack["summary"]["rescue_nudge_review_status_counts"] == {
        "blocked": 1,
        "context_available": 1,
        "not_evaluated": 1,
        "suppressed": 1,
    }
    assert pack["summary"]["rescue_nudge_suppression_reason_counts"] == {
        "rescue_context_not_actionable": 1
    }
    assert pack["summary"]["rescue_nudge_blocker_counts"] == {
        "rescue_projection.day_budget_mutated": 1
    }
    assert "private rescue note should not be in decision pack" not in pack_text
    assert pack["live_delivery_allowed"] is False
    assert pack["scheduler_activation_allowed"] is False
    assert pack["promotion_allowed"] is False


def test_decision_pack_surfaces_copy_review_suppression_risk() -> None:
    pack = build_proactive_no_send_decision_pack([_artifact_with_copy_suppression()])

    assert pack["summary"]["copy_suppressed_count"] == 1
    assert pack["summary"]["review_decision_counts"] == {"suppressed_copy_safety": 1}
    assert "weekly_insight" in pack["summary"]["suppressed_trigger_types"]
    assert "copy_review_issues_present" in pack["promotion_gate"]["promotion_blockers"]
    assert pack["promotion_allowed"] is False


def test_decision_pack_records_no_send_governance_and_silence_reasons() -> None:
    now = datetime(2026, 5, 9, 12, 0, tzinfo=timezone.utc)
    pack = build_proactive_no_send_decision_pack(
        [
            build_proactive_no_send_simulation(
                [
                    ProactiveNoSendShadowInput(
                        trigger_type="weekly_insight",
                        local_time="23:30",
                        quiet_hours_start="22:00",
                        quiet_hours_end="08:00",
                    ),
                    ProactiveNoSendShadowInput(
                        trigger_type="meal_reminder",
                        now=now,
                        cooldown_until=now + timedelta(hours=2),
                    ),
                    ProactiveNoSendShadowInput(
                        trigger_type="recommendation_nudge_nearby",
                        delivery_surface="background",
                    ),
                ]
            ),
            build_proactive_no_send_simulation(
                [
                    ProactiveNoSendShadowInput(
                        trigger_type="meal_reminder",
                        suppressed_trigger_types=["meal_reminder"],
                    ),
                    ProactiveNoSendShadowInput(
                        trigger_type="missing_log_reminder_with_cooldown",
                        ignored_count=2,
                    ),
                    ProactiveNoSendShadowInput(trigger_type="memory_driven_intervention"),
                ]
            ),
        ]
    )

    assert pack["artifact_governance"] == {
        "owner": "app/runtime",
        "consumer": "future_proactive_scheduler_activation_review",
        "retirement_trigger": "approved_proactive_scheduler_runtime_activation_plan",
    }
    assert pack["activation_guardrails"] == {
        "runtime_connected": False,
        "scheduler_connected": False,
        "push_or_line_delivery_connected": False,
        "manager_context_packet_connected": False,
        "mutation_path_connected": False,
        "live_llm_invoked": False,
    }
    assert pack["summary"]["suppression_reason_counts"] == {
        "cooldown_active": 1,
        "interaction_feedback_lower_frequency_required": 1,
        "later_only_trigger_not_live_eligible": 1,
        "permission_explicit_consent_required": 1,
        "permission_no_push_allowed": 1,
        "quiet_hours": 1,
        "suppressed_trigger_type": 1,
    }


def test_decision_pack_writer_creates_artifact(tmp_path: Path) -> None:
    source_path = tmp_path / "proactive_no_send_simulation.json"
    output_path = tmp_path / "proactive_no_send_decision_pack.json"
    source_path.write_text(
        __import__("json").dumps(_artifact_with_review_candidate(), ensure_ascii=False),
        encoding="utf-8",
    )

    written = write_proactive_no_send_decision_pack(
        no_send_artifact_paths=[source_path],
        output_path=output_path,
    )

    assert written == output_path
    payload = written.read_text(encoding="utf-8")
    assert '"artifact_type": "proactive_no_send_decision_pack"' in payload
    assert '"promotion_allowed": false' in payload
