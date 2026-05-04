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
    validate_recommendation_shadow_fixture,
)
from app.recommendation.domain.shadow import (
    CandidateSpec,
    RecommendationShadowFixtureValidationError,
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
    assert not hasattr(result, "top_pick")
    assert not hasattr(result, "hint_packet")
    assert result.selection_owner == "manager_llm_not_run"
    assert result.llm_ranking_used is False
    assert result.manager_selection_required is True
    assert result.runtime_recommendation_selected is False
    assert result.shadow_leading_candidate is not None
    assert result.candidate_hint_packet_drafts
    assert all(
        draft.is_canonical_truth is False
        and draft.selection_authority == "none_shadow_candidate_only"
        and draft.requires_explicit_user_or_manager_selection is True
        for draft in result.candidate_hint_packet_drafts
    )
    assert result.flags == RecommendationShadowFlags()
    assert result.fixture_governance["validation_status"] == "pass"
    assert "sparse_preference_profile_allowed" in result.fixture_governance["notes"]


def test_fixture_validation_rejects_missing_hard_budget_context() -> None:
    scenario = _scenario(
        scenario_id="missing-budget",
        current_budget_view={"budget_kcal": 1600, "consumed_kcal": 900},
        candidates=[_candidate("c1", "tofu bento")],
    )

    try:
        validate_recommendation_shadow_fixture(scenario)
    except RecommendationShadowFixtureValidationError as exc:
        assert exc.reason_codes == ["missing_current_budget_remaining_kcal"]
    else:
        raise AssertionError("fixture validation should reject missing remaining_kcal")


def test_fixture_validation_rejects_missing_hard_body_plan_context() -> None:
    scenario = _scenario(
        scenario_id="missing-body-plan",
        active_body_plan_view={"goal_type": "lose_weight"},
        candidates=[_candidate("c1", "tofu bento")],
    )

    try:
        validate_recommendation_shadow_fixture(scenario)
    except RecommendationShadowFixtureValidationError as exc:
        assert exc.reason_codes == ["missing_active_body_plan_daily_budget_kcal"]
    else:
        raise AssertionError("fixture validation should reject missing active body plan budget")


def test_fixture_validation_rejects_invalid_candidate_kcal_range() -> None:
    scenario = _scenario(
        scenario_id="bad-kcal-range",
        candidates=[
            _candidate("bad-1", "impossible bento", kcal_min=700, kcal_max=500),
            _candidate("bad-2", "zero meal", kcal_min=0, kcal_max=0),
        ],
    )

    try:
        validate_recommendation_shadow_fixture(scenario)
    except RecommendationShadowFixtureValidationError as exc:
        assert exc.reason_codes == [
            "candidate:bad-1:invalid_kcal_range",
            "candidate:bad-2:invalid_kcal_range",
        ]
    else:
        raise AssertionError("fixture validation should reject invalid kcal ranges")


def test_fixture_validation_rejects_boolean_hard_context_values() -> None:
    budget_scenario = _scenario(
        scenario_id="bool-budget",
        current_budget_view={"remaining_kcal": True, "budget_kcal": 1600, "consumed_kcal": 900},
        candidates=[_candidate("c1", "tofu bento")],
    )
    body_scenario = _scenario(
        scenario_id="bool-body",
        active_body_plan_view={
            "daily_budget_kcal": True,
            "goal_type": "lose_weight",
            "plan_status": "active",
        },
        candidates=[_candidate("c1", "tofu bento")],
    )

    for scenario, expected_code in [
        (budget_scenario, "missing_current_budget_remaining_kcal"),
        (body_scenario, "missing_active_body_plan_daily_budget_kcal"),
    ]:
        try:
            validate_recommendation_shadow_fixture(scenario)
        except RecommendationShadowFixtureValidationError as exc:
            assert exc.reason_codes == [expected_code]
        else:
            raise AssertionError("fixture validation should reject boolean hard context")


def test_candidate_fixture_rejects_string_or_boolean_kcal_values_before_eval() -> None:
    for raw_range in [
        {"min": "350", "max": "550"},
        {"min": True, "max": True},
    ]:
        try:
            RecommendationCandidateFixture(
                candidate_id="bad-kcal",
                title="bad kcal",
                estimated_kcal_range=raw_range,
            )
        except ValueError as exc:
            assert "estimated_kcal_range" in str(exc)
        else:
            raise AssertionError("candidate fixture should reject non-strict kcal values")


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
    assert result.shadow_leading_candidate is not None
    assert result.shadow_leading_candidate.candidate_id == "bento-1"
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

    assert result.shadow_leading_candidate is not None
    assert result.shadow_leading_candidate.candidate_id == "golden-1"
    assert (
        result.deterministic_shadow_candidate_order[0].score
        > result.deterministic_shadow_candidate_order[1].score
    )
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
    assert result.shadow_leading_candidate is not None
    assert result.shadow_leading_candidate.candidate_id == "low-1"
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
    assert result.candidate_hint_packet_drafts
    assert result.candidate_hint_packet_drafts[0].current_surface_channel == "chat"


def test_shadow_eval_artifact_contains_required_non_claim_flags() -> None:
    artifact = build_recommendation_shadow_eval_artifact(
        [_scenario("artifact-1", candidates=[_candidate("c1", "tofu bento")])]
    )

    assert artifact.shadow_mode is True
    assert artifact.track_status == {
        "track": "RecommendationShadow",
        "slice_id": "recommendation_shadow_manager_selection_boundary",
        "shadow_mode": True,
        "recommendation_served": False,
        "intake_committed": False,
        "meal_thread_mutated": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "durable_memory_written": False,
        "manager_context_injected": False,
        "live_provider_used": False,
    }
    assert artifact.summary["scenario_count"] == 1
    assert artifact.summary["mode_counts"] == {"general": 1}
    assert artifact.integrity["validation_status"] == "pass"
    assert artifact.integrity["invalid_scenario_count"] == 0
    assert artifact.integrity["runtime_effect_allowed_count"] == 0
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
    assert artifact.evals[0].runtime_effect_allowed is False


def test_default_shadow_eval_writer_creates_requested_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "recommendation_shadow_eval.json"

    output = write_default_recommendation_shadow_eval_artifact(output_path)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output == output_path
    assert payload["artifact_type"] == "recommendation_shadow_eval"
    assert payload["shadow_mode"] is True
    assert payload["integrity"]["validation_status"] == "pass"
    assert payload["integrity"]["invalid_scenario_count"] == 0
    assert len(payload["evals"]) >= 6
    assert all(eval_item["recommendation_served"] is False for eval_item in payload["evals"])
    assert all("top_pick" not in eval_item for eval_item in payload["evals"])
    assert all("hint_packet" not in eval_item for eval_item in payload["evals"])
    assert all(eval_item["shadow_leading_candidate"] is not None for eval_item in payload["evals"])
    assert all(
        all(draft["is_canonical_truth"] is False for draft in eval_item["candidate_hint_packet_drafts"])
        for eval_item in payload["evals"]
    )


def test_menu_scan_mode_uses_menu_items_without_intake_commit() -> None:
    scenario = _scenario(
        scenario_id="menu-scan",
        recommendation_mode="menu_scan",
        candidate_spec=CandidateSpec(
            desired_meal_style="light",
            acceptable_cuisine_families=["taiwanese"],
            soft_target_kcal_band={"min": 300, "max": 620},
            priority_signals=["budget_fit", "menu_scan_item"],
        ),
        candidates=[
            _candidate(
                "menu-high-1",
                "fried pork chop rice",
                source_type="menu_scan_item",
                kcal_min=760,
                kcal_max=940,
                cuisine_family="taiwanese",
            ),
            _candidate(
                "menu-fit-1",
                "grilled chicken rice",
                source_type="menu_scan_item",
                kcal_min=480,
                kcal_max=620,
                cuisine_family="taiwanese",
                protein_posture="high",
            ),
        ],
    )

    result = evaluate_recommendation_shadow_scenario(scenario)

    assert result.recommendation_mode == "menu_scan"
    assert result.shadow_leading_candidate is not None
    assert result.shadow_leading_candidate.candidate_id == "menu-fit-1"
    assert result.candidate_hint_packet_drafts
    assert (
        result.candidate_hint_packet_drafts[0].selection_context["recommendation_mode"]
        == "menu_scan"
    )
    assert result.candidate_hint_packet_drafts[0].is_canonical_truth is False
    assert result.intake_committed is False
    assert result.flags.meal_thread_mutated is False
    assert result.mode_notes == [
        "menu_scan_fixture_only",
        "parsed_menu_items_are_candidate_sources_not_intake_truth",
    ]


def test_swap_suggestion_mode_is_informational_and_does_not_create_proposal() -> None:
    scenario = _scenario(
        scenario_id="swap-suggestion",
        recommendation_mode="swap_suggestion",
        recent_committed_meals_view={
            "meals": [
                {
                    "title": "large fried chicken bento",
                    "total_kcal": 930,
                    "cuisine_family": "taiwanese",
                    "item_patterns": ["fried"],
                }
            ]
        },
        candidate_spec=CandidateSpec(
            desired_meal_style="lighter_alternative",
            acceptable_cuisine_families=["taiwanese", "convenience_store"],
            soft_target_kcal_band={"min": 300, "max": 620},
            swaps_allowed=True,
            priority_signals=["swap_suggestion", "budget_fit", "high_protein"],
            protein_posture="high",
        ),
        candidates=[
            _candidate(
                "swap-1",
                "grilled chicken bento half rice",
                source_type="safe_fallback",
                kcal_min=480,
                kcal_max=620,
                cuisine_family="taiwanese",
                protein_posture="high",
                item_patterns=["grilled", "bento"],
            )
        ],
    )

    result = evaluate_recommendation_shadow_scenario(scenario)

    assert result.recommendation_mode == "swap_suggestion"
    assert result.shadow_leading_candidate is not None
    assert result.shadow_leading_candidate.candidate_id == "swap-1"
    assert result.expected_user_value == "informational_swap_option_without_proposal"
    assert result.flags.intake_committed is False
    assert result.flags.meal_thread_mutated is False
    assert result.flags.day_budget_mutated is False
    assert result.mode_notes == [
        "swap_suggestion_fixture_only",
        "informational_only_no_proposal_state",
    ]


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
    mode_counts = artifact.summary["mode_counts"]

    assert {
        "cold_start_lunch",
        "known_negative_preference",
        "golden_order_lunch",
        "avoid_repeat_dinner",
        "budget_tight",
        "app_usage_style_concise",
        "menu_scan_fixture",
        "swap_suggestion_fixture",
    }.issubset(scenario_ids)
    assert mode_counts["general"] >= 6
    assert mode_counts["menu_scan"] == 1
    assert mode_counts["swap_suggestion"] == 1


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
    assert result.shadow_leading_candidate is not None
    assert "golden_order" not in result.shadow_leading_candidate.ranking_reasons


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
        ROOT / "app" / "recommendation" / "application" / "shadow_fixture_import.py",
        ROOT / "app" / "recommendation" / "application" / "shadow_scorecard.py",
        ROOT / "scripts" / "build_recommendation_shadow_eval.py",
        ROOT / "scripts" / "build_recommendation_shadow_eval_from_fixtures.py",
        ROOT / "scripts" / "build_recommendation_shadow_scorecard.py",
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
    recommendation_mode: str = "general",
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
        recommendation_mode=recommendation_mode,
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
