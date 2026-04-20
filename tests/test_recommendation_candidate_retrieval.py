from __future__ import annotations

from app.application.recommendation_candidate_spec import build_recommendation_candidate_spec
from app.application.recommendation_candidate_retrieval import build_recommendation_candidates
from app.application.recommendation_context import build_recommendation_context
from app.domain import ActiveBodyPlanView, CurrentBudgetView
from app.schemas import RecommendationCandidate


def _candidate(
    candidate_id: str,
    title: str,
    *,
    kcal: int,
    kind: str = "generic",
    store_name: str | None = None,
    source_metadata: dict[str, object] | None = None,
) -> RecommendationCandidate:
    return RecommendationCandidate(
        candidate_id=candidate_id,
        candidate_kind=kind,  # type: ignore[arg-type]
        title=title,
        store_name=store_name,
        estimated_kcal=kcal,
        fit_summary="ok",
        source_metadata=source_metadata or {},
    )


def _context(*, remaining_kcal: int, raw_user_input: str = ""):
    return build_recommendation_context(
        user_id=1,
        current_budget_view=CurrentBudgetView(
            user_id=1,
            local_date="2026-04-18",
            budget_kcal=1800,
            consumed_kcal=1800 - remaining_kcal,
            remaining_kcal=remaining_kcal,
        ),
        active_body_plan_view=ActiveBodyPlanView(
            user_id=1,
            plan_status="active",
            daily_budget_kcal=1800,
        ),
        raw_user_input=raw_user_input,
    )


def test_candidate_retrieval_prefers_historical_then_golden_then_fallback() -> None:
    context = _context(remaining_kcal=700)
    result = build_recommendation_candidates(
        context_packet=context,
        candidate_spec=build_recommendation_candidate_spec(context_packet=context),
        historical_matches=[
            _candidate("h1", "Chicken Bowl", kcal=520, store_name="Store A"),
        ],
        golden_orders=[
            _candidate("g1", "Rice Box", kcal=600, kind="golden_order", store_name="Store B"),
        ],
        safe_defaults=[
            _candidate("s1", "Salad", kcal=450, kind="safe_fallback", store_name="Store C"),
        ],
    )

    assert result.candidate_count == 3
    assert [item.candidate_id for item in result.candidate_items] == ["h1", "g1", "s1"]
    assert result.candidate_items[0].source_metadata["retrieval_tier"] == "historical_match"
    assert result.candidate_source_summary["historical_match"] == 1
    assert result.candidate_source_summary["golden_order"] == 1
    assert result.candidate_source_summary["safe_fallback"] == 1


def test_candidate_retrieval_applies_kcal_filter_before_ordering() -> None:
    context = _context(remaining_kcal=500)
    result = build_recommendation_candidates(
        context_packet=context,
        candidate_spec=build_recommendation_candidate_spec(context_packet=context),
        historical_matches=[
            _candidate("h1", "Too Big", kcal=820, store_name="Store A"),
        ],
        golden_orders=[
            _candidate("g1", "Good Fit", kcal=430, kind="golden_order", store_name="Store B"),
        ],
        safe_defaults=[
            _candidate("s1", "Backup", kcal=480, kind="safe_fallback", store_name="Store C"),
        ],
    )

    assert [item.candidate_id for item in result.candidate_items] == ["g1", "s1"]
    assert result.candidate_filter_reasons["h1"] == ["exceeds_remaining_budget"]


def test_candidate_retrieval_uses_safe_defaults_for_cold_start() -> None:
    context = _context(remaining_kcal=650)
    result = build_recommendation_candidates(
        context_packet=context,
        candidate_spec=build_recommendation_candidate_spec(context_packet=context),
        historical_matches=[],
        golden_orders=[],
        safe_defaults=[
            _candidate("s1", "Default Bento", kcal=520, kind="safe_fallback"),
            _candidate("s2", "Default Soup", kcal=300, kind="safe_fallback"),
        ],
    )

    assert result.candidate_count == 2
    assert result.candidate_source_summary["safe_fallback"] == 2
    assert "missing_historical_matches" in result.coverage_gaps
    assert "cold_start" in result.coverage_gaps


def test_candidate_retrieval_is_driven_by_candidate_spec_filters() -> None:
    context = _context(remaining_kcal=700, raw_user_input="I want something light")
    result = build_recommendation_candidates(
        context_packet=context,
        candidate_spec=build_recommendation_candidate_spec(context_packet=context),
        historical_matches=[
            _candidate(
                "heavy",
                "Heavy Plate",
                kcal=520,
                kind="generic",
                store_name="Store A",
                source_metadata={"item_kind": "fried"},
            ),
            _candidate(
                "light",
                "Light Bowl",
                kcal=420,
                kind="generic",
                store_name="Store B",
                source_metadata={"item_kind": "salad"},
            ),
        ],
    )

    assert [item.candidate_id for item in result.candidate_items] == ["light"]
    assert result.candidate_filter_reasons["heavy"] == ["excluded_by_candidate_spec"]
