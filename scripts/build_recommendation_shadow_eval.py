from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.recommendation.application.shadow_evaluator import (  # noqa: E402
    build_recommendation_shadow_eval_artifact,
)
from app.recommendation.domain.shadow import (  # noqa: E402
    CandidateSpec,
    RecommendationCandidateFixture,
    RecommendationShadowContextFixture,
    RecommendationShadowEvalArtifact,
)


DEFAULT_OUTPUT = ROOT / "artifacts" / "recommendation_shadow_eval.json"


def build_default_recommendation_shadow_eval_artifact() -> RecommendationShadowEvalArtifact:
    return build_recommendation_shadow_eval_artifact(_default_scenarios())


def write_default_recommendation_shadow_eval_artifact(
    output_path: Path = DEFAULT_OUTPUT,
) -> Path:
    artifact = build_default_recommendation_shadow_eval_artifact()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _default_scenarios() -> list[RecommendationShadowContextFixture]:
    return [
        _scenario(
            scenario_id="cold_start_lunch",
            preference_profile_summary={"event_count": 0, "top_items": [], "cuisine_families": []},
            candidate_spec=CandidateSpec(
                desired_meal_style="light",
                acceptable_cuisine_families=["generic", "convenience_store"],
                soft_target_kcal_band={"min": 250, "max": 650},
                priority_signals=["budget_fit", "safe_fallback"],
            ),
            candidates=[
                _candidate(
                    "cold-safe-1",
                    "7-11 tea egg and sweet potato",
                    source_type="safe_fallback",
                    store_name="7-11",
                    kcal_min=260,
                    kcal_max=360,
                    cuisine_family="convenience_store",
                    item_patterns=["tea_egg", "sweet_potato"],
                ),
                _candidate(
                    "cold-generic-1",
                    "simple chicken salad",
                    source_type="generic_healthy",
                    kcal_min=320,
                    kcal_max=460,
                    protein_posture="high",
                ),
            ],
        ),
        _scenario(
            scenario_id="known_negative_preference",
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
                "event_count": 5,
                "top_items": [{"label": "bubble tea", "count": 2}],
                "cuisine_families": [{"label": "taiwanese", "count": 4}],
            },
            candidate_spec=CandidateSpec(
                desired_meal_style="light",
                acceptable_cuisine_families=["taiwanese"],
                soft_target_kcal_band={"min": 300, "max": 650},
                priority_signals=["preferred_cuisine"],
            ),
            candidates=[
                _candidate(
                    "negative-drink-1",
                    "bubble tea",
                    source_type="historical_preference",
                    kcal_min=450,
                    kcal_max=650,
                    cuisine_family="taiwanese",
                    item_kind="drink",
                    item_patterns=["sugary_drinks"],
                ),
                _candidate(
                    "negative-meal-1",
                    "chicken bento half rice",
                    source_type="historical_preference",
                    kcal_min=480,
                    kcal_max=620,
                    cuisine_family="taiwanese",
                    item_patterns=["bento"],
                ),
            ],
        ),
        _scenario(
            scenario_id="golden_order_lunch",
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
                acceptable_cuisine_families=["convenience_store", "taiwanese"],
                soft_target_kcal_band={"min": 350, "max": 650},
                priority_signals=["golden_order", "high_protein"],
                protein_posture="high",
            ),
            candidates=[
                _candidate(
                    "golden-1",
                    "FamilyMart salad chicken and sweet potato",
                    source_type="golden_order",
                    store_name="FamilyMart",
                    kcal_min=360,
                    kcal_max=520,
                    cuisine_family="convenience_store",
                    protein_posture="high",
                    item_patterns=["salad_chicken", "sweet_potato"],
                ),
                _candidate(
                    "golden-backup-1",
                    "tofu bento",
                    source_type="safe_fallback",
                    kcal_min=460,
                    kcal_max=610,
                    cuisine_family="taiwanese",
                    item_patterns=["bento"],
                ),
            ],
        ),
        _scenario(
            scenario_id="avoid_repeat_dinner",
            recent_committed_meals_view={
                "meals": [
                    {
                        "title": "beef noodles",
                        "cuisine_family": "taiwanese",
                        "item_patterns": ["noodles"],
                    }
                ]
            },
            candidate_spec=CandidateSpec(
                desired_meal_style="filling",
                acceptable_cuisine_families=["taiwanese", "japanese"],
                soft_target_kcal_band={"min": 350, "max": 700},
                priority_signals=["avoid_repeat_from_today", "budget_fit"],
                avoid_repeat_from_today=True,
            ),
            candidates=[
                _candidate(
                    "repeat-1",
                    "beef noodle soup",
                    source_type="safe_fallback",
                    kcal_min=520,
                    kcal_max=680,
                    cuisine_family="taiwanese",
                    item_patterns=["noodles"],
                ),
                _candidate(
                    "repeat-alt-1",
                    "grilled fish rice set",
                    source_type="safe_fallback",
                    kcal_min=480,
                    kcal_max=640,
                    cuisine_family="japanese",
                    protein_posture="high",
                    item_patterns=["rice_set", "fish"],
                ),
            ],
        ),
        _scenario(
            scenario_id="budget_tight",
            current_budget_view={"remaining_kcal": 420, "budget_kcal": 1600, "consumed_kcal": 1180},
            candidate_spec=CandidateSpec(
                desired_meal_style="light",
                acceptable_cuisine_families=["any"],
                soft_target_kcal_band={"min": 220, "max": 420},
                budget_fit_posture="tight",
                priority_signals=["budget_fit"],
            ),
            candidates=[
                _candidate(
                    "tight-high-1",
                    "large pork cutlet rice",
                    kcal_min=780,
                    kcal_max=980,
                    item_patterns=["fried", "rice"],
                ),
                _candidate(
                    "tight-low-1",
                    "soy milk and tea egg",
                    kcal_min=220,
                    kcal_max=360,
                    item_kind="snack_meal",
                    protein_posture="medium",
                    item_patterns=["soy_milk", "tea_egg"],
                ),
            ],
        ),
        _scenario(
            scenario_id="app_usage_style_concise",
            app_usage_style_candidate={"presentation_density": "concise"},
            candidate_spec=CandidateSpec(
                desired_meal_style="light",
                acceptable_cuisine_families=["generic"],
                soft_target_kcal_band={"min": 250, "max": 600},
                priority_signals=["presentation_density"],
            ),
            candidates=[
                _candidate("style-1", "chicken rice bowl", kcal_min=420, kcal_max=560),
                _candidate("style-2", "tofu salad", kcal_min=280, kcal_max=420),
            ],
        ),
        _scenario(
            scenario_id="menu_scan_fixture",
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
                    item_patterns=["fried", "rice"],
                ),
                _candidate(
                    "menu-fit-1",
                    "grilled chicken rice",
                    source_type="menu_scan_item",
                    kcal_min=480,
                    kcal_max=620,
                    cuisine_family="taiwanese",
                    protein_posture="high",
                    item_patterns=["grilled", "rice"],
                ),
            ],
        ),
        _scenario(
            scenario_id="swap_suggestion_fixture",
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
        ),
    ]


def _scenario(
    *,
    scenario_id: str,
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
        user_id="dogfood-user",
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
        confidence=0.7,
        source_refs=[f"fixture:{candidate_id}"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the offline recommendation shadow eval artifact."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write the JSON artifact.",
    )
    args = parser.parse_args()
    output = write_default_recommendation_shadow_eval_artifact(args.output)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
