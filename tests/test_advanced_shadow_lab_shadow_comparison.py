from __future__ import annotations

import json

from app.advanced_shadow_lab.shadow_comparison import (
    build_advanced_shadow_comparison_artifact,
)


def test_shadow_comparison_aggregates_fixture_dogfood_and_live_diagnostic() -> None:
    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert artifact["artifact_type"] == "advanced_shadow_comparison_artifact"
    assert artifact["status"] == "pass"
    assert artifact["source_statuses"] == {
        "fixture_chain": "pass",
        "dogfood_replay": "pass",
        "recommendation_copy_live_diagnostic": "pass",
    }
    assert artifact["surface_status_rows"] == [
        {
            "surface": "terminal_no_send_review_sink",
            "fixture_status": "pass",
            "dogfood_status": "pass",
            "live_status": "not_applicable",
            "finding": "no_drift",
        },
        {
            "surface": "recommendation_prompt_reason_copy",
            "fixture_status": "not_applicable",
            "dogfood_status": "not_applicable",
            "live_status": "pass",
            "finding": "live_diagnostic_passed",
        },
    ]
    assert artifact["activation_invariant_summary"]["observed_true_flags"] == []
    assert artifact["live_diagnostic_signal"] == {
        "live_invoked": True,
        "live_provider_used": True,
        "provider_mode": "builderspace_live_diagnostic",
        "output_guard_status": "pass",
    }
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["delivery_attempted"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert "private dogfood wording" not in serialized
    assert "Consider the FamilyMart" not in serialized


def test_shadow_comparison_blocks_activation_claim_drift() -> None:
    dogfood = _dogfood_replay()
    dogfood["delivery_attempted"] = True
    live = _live_diagnostic()
    live["recommendation_served"] = True

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=dogfood,
        recommendation_copy_live_diagnostic_artifact=live,
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "advanced_shadow_dogfood_replay_artifact.delivery_attempted",
        "advanced_shadow_recommendation_copy_live_diagnostic_artifact.recommendation_served",
    ]
    assert artifact["activation_invariant_summary"]["observed_true_flags"] == [
        {
            "source": "advanced_shadow_dogfood_replay_artifact",
            "flag": "delivery_attempted",
        },
        {
            "source": "advanced_shadow_recommendation_copy_live_diagnostic_artifact",
            "flag": "recommendation_served",
        },
    ]
    assert artifact["delivery_attempted"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["user_facing_behavior_changed"] is False


def test_shadow_comparison_treats_live_guard_block_as_quality_finding() -> None:
    live = _live_diagnostic(status="blocked", output_guard_status="blocked")

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=live,
    )

    assert artifact["status"] == "pass"
    assert artifact["source_statuses"]["recommendation_copy_live_diagnostic"] == "blocked"
    assert artifact["surface_status_rows"][1] == {
        "surface": "recommendation_prompt_reason_copy",
        "fixture_status": "not_applicable",
        "dogfood_status": "not_applicable",
        "live_status": "blocked",
        "finding": "live_diagnostic_model_output_blocked",
    }
    assert artifact["blockers"] == []


def test_shadow_comparison_blocks_unsupported_source_artifact_type() -> None:
    fixture = _fixture_chain()
    fixture["artifact_type"] = "legacy_fixture_report"

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=fixture,
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "fixture_chain.unsupported_artifact_type:legacy_fixture_report"
    ]
    assert artifact["source_statuses"]["fixture_chain"] == "unsupported"
    assert artifact["delivery_attempted"] is False
    assert artifact["user_facing_behavior_changed"] is False


def _fixture_chain() -> dict[str, object]:
    return {
        "artifact_type": "advanced_shadow_e2e_fixture_chain_artifact",
        "status": "pass",
        "terminal_review_sink": {"status": "pass", "record_count": 2},
        "mainline_runtime_connected": False,
        "delivery_attempted": False,
        "scheduler_enabled": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _dogfood_replay() -> dict[str, object]:
    return {
        "artifact_type": "advanced_shadow_dogfood_replay_artifact",
        "status": "pass",
        "advanced_fixture_chain_status": "pass",
        "terminal_review_sink_summary": {"status": "pass", "record_count": 2},
        "dogfood_case_summaries": [
            {"case_id": "dogfood-1", "raw_text": "private dogfood wording"}
        ],
        "mainline_runtime_connected": False,
        "delivery_attempted": False,
        "scheduler_enabled": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _live_diagnostic(
    *,
    status: str = "pass",
    output_guard_status: str = "pass",
) -> dict[str, object]:
    return {
        "artifact_type": "advanced_shadow_recommendation_copy_live_diagnostic_artifact",
        "status": status,
        "target_surface": "recommendation_prompt_reason_copy",
        "provider_mode": "builderspace_live_diagnostic",
        "live_invoked": True,
        "live_provider_used": True,
        "output_guard": {"status": output_guard_status},
        "model_output_summary": {
            "draft_prompt_present": True,
            "diagnostic_copy_preview": "Consider the FamilyMart option",
        },
        "mainline_runtime_connected": False,
        "delivery_attempted": False,
        "scheduler_enabled": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }
