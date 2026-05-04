from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

from app.recommendation.application.shadow_evaluator import (
    build_recommendation_shadow_eval_artifact,
    evaluate_recommendation_shadow_scenario,
)
from app.recommendation.domain.shadow import (
    CandidateSpec,
    RecommendationCandidateFixture,
    RecommendationShadowContextFixture,
    RecommendationShadowFlags,
)
from scripts.build_recommendation_shadow_eval import (
    build_default_recommendation_shadow_eval_artifact,
    write_default_recommendation_shadow_eval_artifact,
)


ROOT = Path(__file__).resolve().parents[1]


def test_cold_start_shadow_eval_uses_fallback_candidates_without_runtime_effect() -> None:
    scenario = _scenario(
        scenario_id="cold-start-lunch",
        preference_profile_summary={"event_count": 0, "top_items": [], "cuisine_families": []},
        candidates=[
            _candidate(
                "safe-1",
                "7-11 tea egg and sweet potato",
                source_type="safe_fallback",
                kcal_min=260,
                kcal_max=360,
                protein_posture="medium",
            ),
            _candidate(
                "generic-1",
                "simple chicken salad",
                source_type="generic_healthy",
                kcal_min=320,
                kcal_max=460,
                protein_posture="high",
            ),
        ],
    )

    result = evaluate_recommendation_shadow_scenario(scenario)

    assert result.shadow_mode is True
    assert result.runtime_effect_allowed is False
    assert result.cold_start_used is True
    assert result.candidate_source_summary.candidate_count == 2
    assert result.top_pick is not None
    assert result.hint_packet is not None
    assert result.hint_packet.is_canonical_truth is False
    assert result.selection_owner == "offline_shadow_evaluator_only"
    assert result.manager_selection_required_before_runtime_serving is True
    assert result.flags == RecommendationShadowFlags()


def test_confirmed_negative_preference_filters_candidate_but_soft_preference_only_ranks() -> None:
    scenario = _scenario(
        scenario_id="negative-vs-soft-preference",
        negative_preference_summary={
            "items": [
                {
                    "pattern": "sugary_drinks",
                    "status": "confirmed_negative_preference",
                    "reason": "user_verbal",
                }
            ]
        },
        preference_profile_summary={
            "event_count": 3,
            "top_items": [{"label": "bubble tea", "count": 2}],
            "cuisine_families": [{"label": "taiwanese", "count": 2}],
        },
        candidate_spec=CandidateSpec(
            desired_meal_style="light",
            acceptable_cuisine_families=["taiwanese"],
            soft_target_kcal_band={"min": 250, "max": 650},
            priority_signals=["preferred_cuisine", "avoid_repeat_from_today"],
        ),
        candidates=[
            _candidate(
                "drink-1",
                "bubble tea",
                source_type="historical_preference",
                kcal_min=450,
                kcal_max=650,
                item_patterns=["sugary_drinks"],
            ),
            _candidate(
                "bento-1",
                "chicken bento half rice",
                source_type="historical_preference",
                kcal_min=480,
                kcal_max=620,
                cuisine_family="taiwanese",
                item_patterns=["bento"],
            ),
        ],
    )

    result = evaluate_recommendation_shadow_scenario(scenario)

    assert [item.candidate_id for item in result.filtered_candidates] == ["drink-1"]
    assert result.filtered_candidates[0].reason_codes == ["confirmed_negative_preference"]
    assert result.top_pick is not None
    assert result.top_pick.candidate_id == "bento-1"
    assert "preferred_cuisine:taiwanese" in result.soft_preferences
    assert "preferred_cuisine:taiwanese" not in result.hard_constraints


def test_golden_order_and_avoid_repeat_shape_shadow_ranking_basis() -> None:
    scenario = _scenario(
        scenario_id="golden-order-avoid-repeat",
        recent_committed_meals_view={
            "meals": [
                {
                    "title": "beef noodles",
                    "cuisine_family": "taiwanese",
                    "item_patterns": ["noodles"],
                }
            ]
        },
        golden_order_summary={
            "orders": [
                {
                    "store_name": "FamilyMart",
                    "item_names": ["salad chicken", "sweet potato"],
                    "count": 4,
                }
            ]
        },
        candidate_spec=CandidateSpec(
            desired_meal_style="filling",
            acceptable_cuisine_families=["taiwanese", "convenience_store"],
            soft_target_kcal_band={"min": 350, "max": 650},
            priority_signals=["golden_order", "avoid_repeat_from_today", "high_protein"],
            avoid_repeat_from_today=True,
        ),
        candidates=[
            _candidate(
                "repeat-1",
                "beef noodle soup",
                source_type="safe_fallback",
                kcal_min=520,
                kcal_max=690,
                cuisine_family="taiwanese",
                item_patterns=["noodles"],
            ),
            _candidate(
                "golden-1",
                "FamilyMart salad chicken and sweet potato",
                store_name="FamilyMart",
                source_type="golden_order",
                kcal_min=360,
                kcal_max=520,
                cuisine_family="convenience_store",
                item_patterns=["salad_chicken", "sweet_potato"],
                protein_posture="high",
            ),
        ],
    )

    result = evaluate_recommendation_shadow_scenario(scenario)

    assert result.top_pick is not None
    assert result.top_pick.candidate_id == "golden-1"
    assert result.ranked_candidates[0].score > result.ranked_candidates[1].score
    assert "golden_order:FamilyMart" in result.memory_candidates_used
    assert "avoid_repeat_from_today:noodles" in result.soft_preferences
    assert "repeat-1" in result.memory_candidates_ignored


def test_budget_tight_filters_over_budget_and_keeps_lower_calorie_candidate() -> None:
    scenario = _scenario(
        scenario_id="budget-tight",
        current_budget_view={"remaining_kcal": 420, "budget_kcal": 1600, "consumed_kcal": 1180},
        candidate_spec=CandidateSpec(
            desired_meal_style="light",
            acceptable_cuisine_families=["any"],
            soft_target_kcal_band={"min": 250, "max": 420},
            budget_fit_posture="tight",
        ),
        candidates=[
            _candidate("high-1", "large pork cutlet rice", kcal_min=780, kcal_max=980),
            _candidate("low-1", "soy milk and tea egg", kcal_min=220, kcal_max=360),
        ],
    )

    result = evaluate_recommendation_shadow_scenario(scenario)

    assert [item.candidate_id for item in result.filtered_candidates] == ["high-1"]
    assert "over_budget" in result.filtered_candidates[0].reason_codes
    assert result.top_pick is not None
    assert result.top_pick.candidate_id == "low-1"
    assert result.risk_if_wrong == "medium"


def test_app_usage_style_sets_concise_presentation_policy() -> None:
    scenario = _scenario(
        scenario_id="concise-style",
        app_usage_style_candidate={"presentation_density": "concise"},
        candidates=[
            _candidate("c1", "chicken rice bowl", kcal_min=420, kcal_max=560),
            _candidate("c2", "tofu salad", kcal_min=280, kcal_max=420),
        ],
    )

    result = evaluate_recommendation_shadow_scenario(scenario)

    assert result.presentation_policy == "concise"
    assert result.hint_packet is not None
    assert result.hint_packet.current_surface_channel == "chat"


def test_shadow_eval_artifact_contains_required_non_claim_flags() -> None:
    artifact = build_recommendation_shadow_eval_artifact(
        [_scenario("artifact-1", candidates=[_candidate("c1", "tofu bento")])]
    )

    assert artifact.shadow_mode is True
    assert artifact.real_runtime_effect is False
    assert artifact.recommendation_served is False
    assert artifact.intake_committed is False
    assert artifact.meal_thread_mutated is False
    assert artifact.day_budget_mutated is False
    assert artifact.body_plan_mutated is False
    assert artifact.durable_memory_written is False
    assert artifact.manager_context_injected is False
    assert artifact.live_provider_used is False
    assert artifact.product_readiness_claimed is False
    assert artifact.private_self_use_approved is False
    assert artifact.selection_owner == "offline_shadow_evaluator_only"
    assert artifact.manager_selection_required_before_runtime_serving is True
    assert artifact.evals[0].runtime_effect_allowed is False
    assert artifact.evals[0].manager_selection_required_before_runtime_serving is True


def test_default_shadow_eval_writer_creates_requested_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "recommendation_shadow_eval.json"

    output = write_default_recommendation_shadow_eval_artifact(output_path)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output == output_path
    assert payload["artifact_type"] == "recommendation_shadow_eval"
    assert payload["shadow_mode"] is True
    assert payload["selection_owner"] == "offline_shadow_evaluator_only"
    assert payload["manager_selection_required_before_runtime_serving"] is True
    assert len(payload["evals"]) >= 6
    assert all(eval_item["recommendation_served"] is False for eval_item in payload["evals"])
    assert all(eval_item["manager_selection_required_before_runtime_serving"] is True for eval_item in payload["evals"])
    assert all(eval_item["hint_packet"]["is_canonical_truth"] is False for eval_item in payload["evals"])


def test_shadow_eval_script_runs_by_file_path_without_pythonpath(tmp_path: Path) -> None:
    output_path = tmp_path / "recommendation_shadow_eval.json"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_recommendation_shadow_eval.py",
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "recommendation_shadow_eval"
    assert payload["shadow_mode"] is True


def test_default_fixture_scenarios_cover_core_shadow_cases() -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()
    scenario_ids = {item.scenario_id for item in artifact.evals}

    assert {
        "cold_start_lunch",
        "known_negative_preference",
        "golden_order_lunch",
        "avoid_repeat_dinner",
        "budget_tight",
        "app_usage_style_concise",
    }.issubset(scenario_ids)


def test_empty_golden_order_items_do_not_boost_unrelated_candidates() -> None:
    scenario = _scenario(
        scenario_id="empty-golden-order",
        golden_order_summary={
            "orders": [
                {
                    "store_name": "Unrelated Store",
                    "item_names": [],
                    "count": 4,
                }
            ]
        },
        candidate_spec=CandidateSpec(
            desired_meal_style="light",
            acceptable_cuisine_families=["generic"],
            soft_target_kcal_band={"min": 250, "max": 650},
            priority_signals=["golden_order"],
        ),
        candidates=[
            _candidate(
                "generic-1",
                "tofu bento",
                source_type="safe_fallback",
                store_name="Different Store",
                kcal_min=360,
                kcal_max=520,
            )
        ],
    )

    result = evaluate_recommendation_shadow_scenario(scenario)

    assert result.memory_candidates_used == []
    assert result.top_pick is not None
    assert "golden_order" not in result.top_pick.ranking_reasons


def test_active_runtime_does_not_import_recommendation_shadow_evaluator() -> None:
    active_entrypoints = [
        ROOT / "app" / "main.py",
        ROOT / "app" / "routes.py",
        ROOT / "app" / "schemas.py",
        ROOT / "app" / "models.py",
        ROOT / "app" / "composition" / "v2_routes.py",
        ROOT / "app" / "composition" / "intake_routes.py",
        ROOT / "app" / "composition" / "intake_turn_orchestrator.py",
        ROOT / "app" / "composition" / "intake_execution_orchestrator.py",
        ROOT / "app" / "runtime" / "application" / "manager_service.py",
        ROOT / "app" / "runtime" / "agent" / "manager_context_payload.py",
    ]

    violations: list[str] = []
    for path in active_entrypoints:
        if not path.exists():
            continue
        for imported in _absolute_imports(path):
            if imported.startswith("app.recommendation.application.shadow_evaluator"):
                violations.append(f"{path.relative_to(ROOT)} imports {imported}")

    assert not violations


def test_shadow_evaluator_modules_do_not_import_live_runtime_provider_or_persistence() -> None:
    paths = [
        ROOT / "app" / "recommendation" / "domain" / "shadow.py",
        ROOT / "app" / "recommendation" / "application" / "shadow_evaluator.py",
        ROOT / "scripts" / "build_recommendation_shadow_eval.py",
    ]

    forbidden_import_prefixes = (
        "app.providers",
        "app.runtime.agent",
        "app.runtime.application.manager_service",
        "app.runtime.agent.manager_context_payload",
        "app.intake.infrastructure",
        "app.budget.infrastructure",
        "app.body.infrastructure",
        "sqlalchemy",
        "requests",
        "httpx",
    )
    violations: list[str] = []
    for path in paths:
        for imported in _absolute_imports(path):
            if imported.startswith(forbidden_import_prefixes):
                violations.append(f"{path.relative_to(ROOT)} imports {imported}")

    assert not violations


def _scenario(
    scenario_id: str,
    *,
    current_budget_view: dict | None = None,
    active_body_plan_view: dict | None = None,
    recent_committed_meals_view: dict | None = None,
    open_proposals_view: dict | None = None,
    proactive_status_view: dict | None = None,
    preference_profile_summary: dict | None = None,
    negative_preference_summary: dict | None = None,
    golden_order_summary: dict | None = None,
    app_usage_style_candidate: dict | None = None,
    candidate_spec: CandidateSpec | None = None,
    candidates: list[RecommendationCandidateFixture] | None = None,
) -> RecommendationShadowContextFixture:
    return RecommendationShadowContextFixture(
        scenario_id=scenario_id,
        user_id="user-1",
        local_date="2026-05-04",
        channel="chat",
        recorded_at="2026-05-04T12:00:00+08:00",
        timezone="Asia/Taipei",
        current_budget_view=current_budget_view
        or {"remaining_kcal": 700, "budget_kcal": 1600, "consumed_kcal": 900},
        active_body_plan_view=active_body_plan_view
        or {"daily_budget_kcal": 1600, "goal_type": "lose_weight", "plan_status": "active"},
        recent_committed_meals_view=recent_committed_meals_view or {"meals": []},
        open_proposals_view=open_proposals_view or {"proposals": []},
        proactive_status_view=proactive_status_view or {"status": "inactive"},
        preference_profile_summary=preference_profile_summary or {"event_count": 1},
        negative_preference_summary=negative_preference_summary or {"items": []},
        golden_order_summary=golden_order_summary or {"orders": []},
        app_usage_style_candidate=app_usage_style_candidate or {},
        candidate_spec=candidate_spec or CandidateSpec(),
        candidate_source_fixture=candidates or [],
    )


def _candidate(
    candidate_id: str,
    title: str,
    *,
    store_name: str | None = None,
    source_type: str = "safe_fallback",
    kcal_min: int = 350,
    kcal_max: int = 550,
    cuisine_family: str = "generic",
    item_kind: str = "meal",
    staple_type: str | None = None,
    protein_posture: str = "medium",
    item_patterns: list[str] | None = None,
) -> RecommendationCandidateFixture:
    return RecommendationCandidateFixture(
        candidate_id=candidate_id,
        title=title,
        store_name=store_name,
        source_type=source_type,
        estimated_kcal_range={"min": kcal_min, "max": kcal_max},
        cuisine_family=cuisine_family,
        item_kind=item_kind,
        staple_type=staple_type,
        protein_posture=protein_posture,
        item_patterns=item_patterns or [],
        source_refs=[f"fixture:{candidate_id}"],
    )


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports
