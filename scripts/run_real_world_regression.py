from __future__ import annotations

import argparse
import asyncio
import collections
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.providers.builderspace_adapter import BuilderSpaceAdapter
from app.schemas import EstimateRequest
from app.search.tavily_adapter import TavilyAdapter
from app.usecases.text_meal import _normalize_user_input_for_estimation, run_text_meal_canary


def _load_cases(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Fixture must be a JSON array.")
    return data


def _build_wave_summary(results: list[dict]) -> dict:
    by_category = collections.Counter()
    by_best_answer_source = collections.Counter()
    by_failed_layer = collections.Counter()
    by_verdict = collections.Counter()
    by_failure_family = collections.Counter()
    followup_decisions = collections.Counter()
    db_hit_types = collections.Counter()

    for result in results:
        if result.get("category"):
            by_category[result["category"]] += 1
        if result.get("best_answer_source"):
            by_best_answer_source[result["best_answer_source"]] += 1
        if result.get("failed_layer"):
            by_failed_layer[result["failed_layer"]] += 1
        if result.get("north_star_verdict"):
            by_verdict[result["north_star_verdict"]] += 1
        if result.get("failure_family"):
            by_failure_family[result["failure_family"]] += 1
        if result.get("followup_decision"):
            followup_decisions[result["followup_decision"]] += 1
        if result.get("db_hit_type"):
            db_hit_types[result["db_hit_type"]] += 1

    return {
        "total_cases": len(results),
        "by_category": dict(by_category),
        "by_best_answer_source": dict(by_best_answer_source),
        "by_failed_layer": dict(by_failed_layer),
        "by_north_star_verdict": dict(by_verdict),
        "by_failure_family": dict(by_failure_family),
        "by_followup_decision": dict(followup_decisions),
        "by_db_hit_type": dict(db_hit_types),
    }


async def _run_case(case: dict, *, provider: BuilderSpaceAdapter, search: TavilyAdapter, allow_search: bool) -> dict:
    raw_input = str(case["user_input"])
    normalization = _normalize_user_input_for_estimation(raw_input)
    payload = await run_text_meal_canary(
        EstimateRequest(text=raw_input, allow_search=allow_search),
        provider=provider,
        request_id=str(case["id"]),
        search_adapter=search,
    )
    return {
        "id": case["id"],
        "category": case.get("category"),
        "raw_input": raw_input,
        "normalized_input": normalization["normalized_text"],
        "expected_normalized_input": case.get("expected_normalized_input"),
        "normalizer_applied": normalization["normalizer_applied"],
        "normalizer_notes": normalization["notes"],
        "meal_title": payload.meal_title,
        "estimated_kcal": payload.estimated_kcal,
        "protein_g": payload.protein_g,
        "carb_g": payload.carb_g,
        "fat_g": payload.fat_g,
        "best_answer_source": payload.best_answer_source,
        "best_estimate_mode": payload.best_estimate_mode,
        "estimate_confidence_tier": payload.estimate_confidence_tier,
        "failure_family": payload.failure_family,
        "trace_contract": payload.trace_contract,
        "failed_layer": payload.failed_layer,
        "primary_failure_reason": payload.primary_failure_reason,
        "north_star_evaluation": payload.north_star_evaluation,
        "north_star_verdict": payload.north_star_evaluation.get("win_loss_neutral"),
        "followup_decision": payload.trace_contract.get("followup_decision"),
        "db_hit_type": payload.trace_contract.get("db_hit_type"),
        "used_search": payload.used_search,
        "search_query": payload.search_query,
        "search_quality": payload.search_quality,
        "retrieved_evidence_summary": payload.retrieved_evidence_summary,
        "reply_text": payload.reply_text,
    }


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Run the real-world regression fixture against live provider/search.")
    parser.add_argument(
        "--fixture",
        default=str(ROOT / "tests" / "fixtures" / "real_world_regression_cases.json"),
        help="Path to the regression fixture JSON file.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / ".logs" / "real_world_regression_results.json"),
        help="Path to write the regression results JSON file.",
    )
    parser.add_argument(
        "--allow-search",
        action="store_true",
        help="Enable external search during regression.",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    fixture_path = Path(args.fixture).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    provider = BuilderSpaceAdapter()
    search = TavilyAdapter()
    cases = _load_cases(fixture_path)

    results: list[dict] = []
    for case in cases:
        result = await _run_case(case, provider=provider, search=search, allow_search=args.allow_search)
        results.append(result)
        summary = {
            "id": result["id"],
            "category": result["category"],
            "normalized_input": result["normalized_input"],
            "estimated_kcal": result["estimated_kcal"],
            "best_answer_source": result["best_answer_source"],
            "best_estimate_mode": result["best_estimate_mode"],
            "estimate_confidence_tier": result["estimate_confidence_tier"],
            "failure_family": result["failure_family"],
            "failed_layer": result["failed_layer"],
            "north_star_verdict": result["north_star_verdict"],
            "followup_decision": result["followup_decision"],
            "db_hit_type": result["db_hit_type"],
            "used_search": result["used_search"],
            "search_quality": result["search_quality"],
        }
        print(json.dumps(summary, ensure_ascii=False))

    wave_summary = _build_wave_summary(results)
    output_payload = {
        "wave_summary": wave_summary,
        "cases": results,
    }
    output_path.write_text(json.dumps(output_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nWave summary:")
    print(json.dumps(wave_summary, ensure_ascii=False, indent=2))
    print(f"\nSaved regression results to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
