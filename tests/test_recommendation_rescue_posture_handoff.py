from __future__ import annotations


def _commit_effect(**overrides: object) -> dict:
    artifact = {
        "artifact_type": "isolated_lab_rescue_commit_effect",
        "status": "pass",
        "refreshed_current_budget_view": {
            "user_id": "user-1",
            "local_date": "2026-05-13",
            "budget_kcal": 1800,
            "consumed_kcal": 600,
            "adjustment_kcal": 425,
            "remaining_kcal": 775,
        },
        "rescue_commit_effect": {
            "proposal_id": "rescue-proposal-1",
            "recommended_days": 2,
            "daily_kcal_adjustment": -225,
            "effective_from": "2026-05-13Tafter_lunch",
            "effective_to": "2026-05-14",
        },
    }
    artifact.update(overrides)
    return artifact


def _recommendation_payload(**overrides: object) -> dict:
    payload = {
        "current_budget_view": {"remaining_kcal": 1000},
        "negative_preference_summary": {"items": []},
        "open_rescue_context": {"accepted_conflict_patterns": []},
        "candidate_source_fixture": [
            {
                "candidate_id": "under",
                "title": "grilled chicken rice",
                "estimated_kcal_range": {"max": 700},
                "item_patterns": ["grilled_chicken"],
            },
            {
                "candidate_id": "over",
                "title": "large ramen",
                "estimated_kcal_range": {"max": 850},
                "item_patterns": ["ramen"],
            },
        ],
    }
    payload.update(overrides)
    return payload


def _handoff(commit_effect: dict | None = None, payload: dict | None = None) -> dict:
    from app.recommendation.application.rescue_posture_handoff import (
        build_recommendation_rescue_posture_handoff,
    )

    return build_recommendation_rescue_posture_handoff(
        isolated_lab_rescue_commit_effect=commit_effect or _commit_effect(),
        recommendation_payload=payload or _recommendation_payload(),
    )


def test_handoff_patches_recommendation_budget_posture_from_accepted_rescue_overlay() -> None:
    artifact = _handoff()

    assert artifact["artifact_type"] == "recommendation_rescue_posture_handoff"
    assert artifact["status"] == "pass"
    assert artifact["handoff_scope"] == "short_term_caloric_posture_only"
    patched = artifact["recommendation_runtime_patch"]
    assert patched["current_budget_view"]["remaining_kcal"] == 775
    assert patched["open_rescue_context"]["accepted_rescue_overlay_active"] is True
    assert patched["open_rescue_context"]["daily_kcal_adjustment"] == -225

    preview = artifact["candidate_guard_preview"]
    assert preview["allowed_candidate_ids"] == ["under"]
    assert preview["filtered_candidates"] == [
        {"candidate_id": "over", "reason_codes": ["over_budget"]}
    ]


def test_handoff_preserves_existing_rescue_conflict_patterns_for_candidate_guard() -> None:
    payload = _recommendation_payload(
        open_rescue_context={"accepted_conflict_patterns": ["fried_chicken"]},
        candidate_source_fixture=[
            {
                "candidate_id": "conflict",
                "title": "fried chicken bento",
                "estimated_kcal_range": {"max": 650},
                "item_patterns": ["fried_chicken"],
            }
        ],
    )

    artifact = _handoff(payload=payload)

    assert artifact["status"] == "pass"
    assert artifact["candidate_guard_preview"]["filtered_candidates"] == [
        {"candidate_id": "conflict", "reason_codes": ["accepted_rescue_conflict"]}
    ]


def test_handoff_does_not_create_recommendation_intent_or_serve_offer() -> None:
    artifact = _handoff()

    assert artifact["recommendation_served"] is False
    assert artifact["recommendation_intent_state_created"] is False
    assert artifact["intake_handoff_created"] is False
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["production_db_mutation_allowed"] is False
    assert artifact["canonical_mutation_changed"] is False
    assert artifact["rescue_posture_summary"]["recommendation_offer_served"] is False


def test_handoff_blocks_without_passed_commit_effect_or_refreshed_budget() -> None:
    artifact = _handoff(
        commit_effect=_commit_effect(
            status="blocked",
            refreshed_current_budget_view={},
        )
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "rescue_commit_effect.status_not_pass",
        "rescue_commit_effect.refreshed_current_budget_view_missing",
    ]
    assert artifact["recommendation_runtime_patch"] is None
