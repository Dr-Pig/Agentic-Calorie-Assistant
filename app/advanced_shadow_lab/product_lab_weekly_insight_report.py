from __future__ import annotations

from collections import Counter
from typing import Any, Mapping


def build_weekly_insight_report(fixture: Mapping[str, Any]) -> dict[str, Any]:
    budgets = _dicts(fixture.get("budget_summaries"))
    meals = _dicts(fixture.get("meal_logs"))
    bodies = _dicts(fixture.get("body_observations"))
    days = max(7, len(budgets))
    overshoot_days = sum(1 for row in budgets if _float(row.get("overshoot_kcal")) > 0)
    at_or_under = max(0, len(budgets) - overshoot_days)
    logging_coverage = round(len({_date(row.get("logged_at")) for row in meals}) / days, 2)
    posture = (
        "ready_for_lab_chat"
        if len(budgets) >= 7 and logging_coverage >= 0.5
        else "degraded_insufficient_logging_coverage"
    )
    report = {
        "report_id": (
            f"weekly:{fixture.get('user_id') or 'unknown'}:"
            f"{fixture.get('week_id') or ''}"
        ),
        "user_id": str(fixture.get("user_id") or ""),
        "week_start_date": str(fixture.get("week_start_date") or ""),
        "week_end_date": str(fixture.get("week_end_date") or ""),
        "generated_at": str(fixture.get("generated_at") or ""),
        "report_posture": posture,
        "deficit_achievement_rate": round(at_or_under / days, 2),
        "overshoot_days": overshoot_days,
        "overshoot_pattern": _overshoot_pattern(budgets),
        "top_calorie_sources": _top_sources(meals),
        "logging_coverage": logging_coverage,
        "weight_trend_summary": _weight_trend(bodies),
        "swap_opportunities": [dict(row) for row in fixture.get("swap_opportunities") or []],
        "positive_highlights": _positive_highlights(at_or_under, logging_coverage),
        "canonical_product_mutation_allowed": False,
    }
    return {**report, "narrative_summary": weekly_insight_narrative(report)}


def weekly_insight_report_blockers(report: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _float(report.get("logging_coverage")) < 0.5:
        blockers.append("weekly_insight.logging_coverage_below_threshold")
    if not report.get("week_start_date") or not report.get("week_end_date"):
        blockers.append("weekly_insight.week_window_missing")
    return blockers


def weekly_insight_chat_copy(report: Mapping[str, Any]) -> str:
    if report.get("report_posture") != "ready_for_lab_chat":
        return "Weekly check-in is waiting for more logged days before summarizing."
    return str(report.get("narrative_summary") or "")


def weekly_insight_narrative(report: Mapping[str, Any]) -> str:
    if report.get("report_posture") != "ready_for_lab_chat":
        return "This week needs more logged days before a useful pattern summary."
    return (
        f"Weekly check-in: {int(round(_float(report.get('deficit_achievement_rate')) * 7))} "
        f"of 7 days were at or under target, with {report.get('overshoot_days')} "
        "overshoot day(s). The most useful next step is to watch the top source "
        f"{_top_source_name(report)}."
    )


def weekly_insight_source_refs(
    fixture: Mapping[str, Any], report: Mapping[str, Any]
) -> list[str]:
    return [
        "weekly_insight_shadow_plan",
        f"weekly_insight_report:{report.get('report_id') or ''}",
        *[str(row.get("trace_id") or "") for row in _dicts(fixture.get("budget_summaries"))],
    ]


def _top_source_name(report: Mapping[str, Any]) -> str:
    sources = report.get("top_calorie_sources")
    if isinstance(sources, list) and sources:
        first = sources[0]
        if isinstance(first, Mapping):
            return str(first.get("source") or "unknown")
    return "unknown"


def _top_sources(meals: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    totals: Counter[str] = Counter()
    for row in meals:
        totals[str(row.get("calorie_source") or "unknown")] += int(
            _float(row.get("estimated_kcal"))
        )
    total = sum(totals.values()) or 1
    return [
        {
            "source": source,
            "total_kcal": kcal,
            "share_of_logged_kcal": round(kcal / total, 2),
        }
        for source, kcal in totals.most_common(3)
    ]


def _overshoot_pattern(budgets: list[Mapping[str, Any]]) -> str:
    dates = [
        str(row.get("date") or "")
        for row in budgets
        if _float(row.get("overshoot_kcal")) > 0
    ]
    return "none" if not dates else "overshoot_on_" + ",".join(dates)


def _weight_trend(bodies: list[Mapping[str, Any]]) -> str:
    weights = [_float(row.get("weight_kg")) for row in bodies if row.get("weight_kg")]
    if len(weights) < 2:
        return "not_enough_weight_observations"
    return f"{round(weights[-1] - weights[0], 1):+.1f} kg across available observations"


def _positive_highlights(at_or_under: int, coverage: float) -> list[str]:
    return [
        f"{at_or_under} day(s) at or under budget",
        f"{int(coverage * 100)}% logging coverage",
    ]


def _dicts(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in value or [] if isinstance(row, Mapping)]


def _date(value: Any) -> str:
    return str(value or "").split("T", 1)[0]


def _float(value: Any) -> float:
    return value if isinstance(value, (int, float)) else 0.0


__all__ = [
    "build_weekly_insight_report",
    "weekly_insight_chat_copy",
    "weekly_insight_report_blockers",
    "weekly_insight_source_refs",
]
