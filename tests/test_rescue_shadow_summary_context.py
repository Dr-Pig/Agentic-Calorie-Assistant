from __future__ import annotations

import ast
from pathlib import Path

from app.rescue.application.shadow_summary_context import (
    build_rescue_shadow_summary_context_projection,
)


ROOT = Path(__file__).resolve().parents[1]


def test_rescue_shadow_context_consumes_memory_summaries_without_runtime_effects() -> None:
    projection = build_rescue_shadow_summary_context_projection(
        memory_summary_projection=_memory_projection(),
        derived_memory_views=_derived_views(),
    )

    assert projection["artifact_type"] == "rescue_shadow_summary_context_projection"
    assert projection["status"] == "pass"
    assert projection["owner"] == "app/rescue"
    assert projection["memory_summary_projection_used"] is True
    assert projection["runtime_effect_allowed"] is False
    assert projection["rescue_committed"] is False
    assert projection["proposal_committed"] is False
    assert projection["day_budget_mutated"] is False
    assert projection["body_plan_mutated"] is False
    assert projection["durable_memory_written"] is False
    assert projection["manager_context_injected"] is False
    assert projection["proactive_sent"] is False
    assert projection["recommendation_served"] is False

    assert projection["memory_signal_summary"] == {
        "preference_candidate_count": 1,
        "negative_preference_blocker_count": 1,
        "suppression_blocker_count": 1,
    }
    assert projection["rescue_history_context"]["rescue_event_count"] == 2
    assert projection["adherence_context"]["adherence_posture"] == "mixed"


def test_rescue_shadow_context_records_suppression_and_history_as_review_context_only() -> None:
    projection = build_rescue_shadow_summary_context_projection(
        memory_summary_projection=_memory_projection(),
        derived_memory_views=_derived_views(),
    )

    assert projection["suppression_context"] == [
        {
            "candidate_id": "suppress-1",
            "trigger_type": "rescue_nudge",
            "summary": "user often ignores rescue nudges",
            "review_context_only": True,
        }
    ]
    assert projection["history_review_notes"] == [
        "rescue_history_present_for_future_viability_review",
        "adherence_summary_present_for_future_viability_review",
    ]
    assert projection["rescue_needed"] is None
    assert projection["send_or_skip"] is None
    assert projection["candidate_copy"] is None


def test_rescue_shadow_context_does_not_create_invitation_copy_or_proposal() -> None:
    projection = build_rescue_shadow_summary_context_projection(
        memory_summary_projection=_memory_projection(),
        derived_memory_views=_derived_views(),
    )

    assert projection["proposal_card"] is None
    assert projection["primary_actions"] == []
    assert projection["recommended_days"] is None
    assert projection["daily_kcal_adjustment"] is None
    assert "not_rescue_invitation" in projection["non_claims"]
    assert "not_proactive_send_or_skip_decision" in projection["non_claims"]


def test_rescue_shadow_context_blocks_memory_projection_claim_drift() -> None:
    memory = _memory_projection()
    memory["rescue_proposal_committed"] = True

    projection = build_rescue_shadow_summary_context_projection(
        memory_summary_projection=memory,
        derived_memory_views=_derived_views(),
    )

    assert projection["status"] == "blocked"
    assert "consumer_summary_projection.rescue_proposal_committed" in projection["blockers"]
    assert projection["memory_signal_summary"] == {}
    assert projection["proposal_committed"] is False


def test_active_runtime_entrypoints_do_not_import_rescue_shadow_summary_context() -> None:
    active_entrypoints = [
        ROOT / "app" / "main.py",
        ROOT / "app" / "routes.py",
        ROOT / "app" / "schemas.py",
        ROOT / "app" / "runtime" / "application" / "manager_service.py",
        ROOT / "app" / "runtime" / "agent" / "manager_context_payload.py",
    ]
    forbidden = "app.rescue.application.shadow_summary_context"

    violations: list[str] = []
    for path in active_entrypoints:
        if not path.exists():
            continue
        violations.extend(
            f"{path.relative_to(ROOT)} imports {imported}"
            for imported in _absolute_imports(path)
            if imported.startswith(forbidden)
        )

    assert not violations


def _memory_projection() -> dict:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "accepted_shadow_candidate_ids": ["pref-1"],
            "negative_preference_blockers": ["neg-1"],
        },
        "suppression_summary": {
            "suppression_blockers": [
                {
                    "candidate_id": "suppress-1",
                    "trigger_type": "rescue_nudge",
                    "summary": "user often ignores rescue nudges",
                }
            ]
        },
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "rescue_proposal_committed": False,
        "retrieval_ranking_changed": False,
    }


def _derived_views() -> dict:
    return {
        "artifact_type": "derived_memory_views_shadow_eval",
        "rescue_history_summary": {
            "source_kind": "derived_read_model",
            "is_durable_memory_truth": False,
            "rescue_event_count": 2,
            "overshoot_day_count": 3,
            "rescue_viability_posture": "shadow_candidate_only",
        },
        "adherence_summary": {
            "source_kind": "derived_read_model",
            "is_durable_memory_truth": False,
            "budget_day_count": 7,
            "at_or_under_target_day_count": 4,
            "overshoot_day_count": 3,
            "average_overshoot_kcal": 220.0,
            "adherence_posture": "mixed",
        },
    }


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports
