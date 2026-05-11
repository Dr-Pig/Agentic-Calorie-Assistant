from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.shared.infra.json_artifacts import read_json_artifact


def test_weekly_insight_builds_lab_report_from_deterministic_metrics() -> None:
    from app.advanced_shadow_lab.product_lab_weekly_insight import (
        run_product_lab_weekly_insight,
    )
    from app.advanced_shadow_lab.product_lab_weekly_insight_fixture_inputs import (
        build_product_lab_weekly_insight_fixture_inputs,
    )

    artifact = run_product_lab_weekly_insight(
        fixture_inputs=build_product_lab_weekly_insight_fixture_inputs(),
        enabled=True,
    )

    assert artifact["artifact_type"] == "advanced_product_lab_weekly_insight_artifact"
    assert artifact["status"] == "pass"
    assert artifact["lab_enabled"] is True
    assert artifact["weekly_insight_report_generated"] is True
    assert artifact["weekly_insight_chat_candidate_allowed"] is True
    assert artifact["weekly_insight_report"]["report_id"] == "weekly:fixture-user:2026-W19"
    assert artifact["weekly_insight_report"]["deficit_achievement_rate"] == 0.71
    assert artifact["weekly_insight_report"]["logging_coverage"] == 1.0
    assert artifact["weekly_insight_report"]["overshoot_days"] == 2
    assert artifact["weekly_insight_report"]["narrative_summary"]
    assert artifact["lab_chat_copy"]
    assert artifact["llm_boundary"]["may_invent_metrics"] is False
    assert artifact["source_shadow_artifact"]["weekly_insight_report_written"] is False
    assert artifact["production_scheduler_delivery_allowed"] is False
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_weekly_insight_degrades_when_logging_coverage_is_too_low() -> None:
    from app.advanced_shadow_lab.product_lab_weekly_insight import (
        run_product_lab_weekly_insight,
    )
    from app.advanced_shadow_lab.product_lab_weekly_insight_fixture_inputs import (
        build_product_lab_weekly_insight_fixture_inputs,
    )

    artifact = run_product_lab_weekly_insight(
        fixture_inputs=build_product_lab_weekly_insight_fixture_inputs(
            mode="low_coverage"
        ),
        enabled=True,
    )

    assert artifact["status"] == "pass"
    assert artifact["weekly_insight_report"]["report_posture"] == (
        "degraded_insufficient_logging_coverage"
    )
    assert artifact["weekly_insight_chat_candidate_allowed"] is False
    assert artifact["lab_chat_delivery_allowed"] is False
    assert "weekly_insight.logging_coverage_below_threshold" in artifact["blockers"]
    assert artifact["scheduler_delivery_allowed"] is False


def test_product_lab_turn_surfaces_v_weekly_insight_chat_packet() -> None:
    from app.advanced_shadow_lab.product_lab_weekly_insight_fixture_inputs import (
        build_product_lab_weekly_insight_fixture_inputs,
    )

    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_weekly_turn("weekly-turn-1"),
        fixture_inputs=build_product_lab_weekly_insight_fixture_inputs(),
    )

    assert artifact["status"] == "pass"
    assert "weekly_insight" in artifact["product_capabilities_exercised"]
    weekly = artifact["product_lab_weekly_insight_artifact"]
    assert weekly["weekly_insight_chat_candidate_allowed"] is True
    proactive = artifact["product_lab_proactive_artifact"]
    assert "weekly_insight" in proactive["delivery_packet"]["candidate_ids"]
    assert proactive["pre_delivery_review"]["allowed_trigger_types"] == [
        "recommendation_prompt",
        "rescue_nudge",
        "weekly_insight",
    ]
    packet = _message(artifact, "weekly_insight:2")
    assert packet["workflow_family"] == "proactive"
    assert packet["trigger_type"] == "weekly_insight"
    assert packet["weekly_insight_report"]["report_id"] == "weekly:fixture-user:2026-W19"
    assert packet["weekly_insight_report"]["canonical_product_mutation_allowed"] is False
    assert [action["action"] for action in packet["actions"]] == [
        "dismiss",
        "snooze",
        "undo",
    ]
    assert artifact["lab_chat_response_packet"]["lab_runtime_capabilities"][
        "weekly_insight_served_to_lab"
    ] is True
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["production_scheduler_delivery_allowed"] is False
    assert artifact["durable_product_memory_written"] is False


def test_session_replay_can_dismiss_weekly_insight_until_next_week_signal(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_weekly_insight_fixture_inputs import (
        build_product_lab_weekly_insight_fixture_inputs,
    )

    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="lab-session-weekly-1",
        fixture_inputs=build_product_lab_weekly_insight_fixture_inputs(),
        turns=[
            {
                "turn_id": "week1",
                "semantic_intent_fixture": "weekly_insight_proactive_lab",
                "weekly_insight_enabled": True,
                "lab_now_minute": 8 * 60,
                "post_turn_control_events": [
                    {
                        "event_id": "dismiss-weekly",
                        "action": "dismiss",
                        "target_candidate_id": "weekly_insight:2",
                        "trigger_type": "weekly_insight",
                        "scope": "candidate_instance",
                        "dismiss_reason": "not_relevant_now",
                        "next_signal_required": "new_weekly_insight_window",
                    }
                ],
            },
            {
                "turn_id": "same-week",
                "semantic_intent_fixture": "weekly_insight_proactive_lab",
                "weekly_insight_enabled": True,
                "lab_now_minute": 9 * 60,
            },
            {
                "turn_id": "next-week",
                "semantic_intent_fixture": "weekly_insight_proactive_lab",
                "weekly_insight_enabled": True,
                "lab_now_minute": 8 * 60,
                "observed_material_signals": ["new_weekly_insight_window"],
            },
        ],
    )

    assert artifact["status"] == "pass"
    visible_by_turn = {
        row["turn_id"]: row["visible_candidate_ids"]
        for row in artifact["turn_summaries"]
    }
    assert "weekly_insight:2" in visible_by_turn["week1"]
    assert "weekly_insight:2" not in visible_by_turn["same-week"]
    assert "weekly_insight:2" in visible_by_turn["next-week"]
    assert artifact["production_scheduler_delivery_allowed"] is False
    assert artifact["mainline_activation_enabled"] is False

    same_week = read_json_artifact(Path(artifact["turn_artifact_paths"][1]))
    proactive = same_week["turn_artifact"]["product_lab_proactive_artifact"]
    weekly_omissions = [
        row for row in proactive["omission_traces"] if row["trigger_type"] == "weekly_insight"
    ]
    assert weekly_omissions[0]["omission_reason"] == (
        "dismissed_until_material_signal"
    )


def _weekly_turn(turn_id: str) -> dict[str, object]:
    return {
        "session_id": "lab-session-weekly-1",
        "turn_id": turn_id,
        "surface": "chat",
        "user_utterance": "fixture text is not a semantic oracle",
        "semantic_intent_fixture": "weekly_insight_proactive_lab",
        "weekly_insight_enabled": True,
        "lab_now_minute": 8 * 60,
        "proactive_gate_context": {
            "local_time": "08:00",
            "max_recent_send_count": 2,
            "recent_send_count": 0,
            "delivery_surface_by_trigger": {
                "recommendation_prompt": "app_open",
                "weekly_insight": "app_open",
            },
            "explicit_consent_ready_by_trigger": {"rescue_nudge": True},
        },
    }


def _message(artifact: dict[str, object], candidate_id: str) -> dict[str, object]:
    surface = artifact["lab_chat_surface"]  # type: ignore[index]
    for message in surface["messages"]:  # type: ignore[index]
        if message["candidate_id"] == candidate_id:
            return message
    raise AssertionError(f"message not found: {candidate_id}")
