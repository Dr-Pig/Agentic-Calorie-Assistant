from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.benchmark_loader import load_benchmark_cases
from app.routes import planner_provider, primary_provider, search_provider
from app.schemas import EstimateRequest
from app.usecases.text_meal import run_text_meal_canary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run retrieval / external search benchmark.")
    parser.add_argument(
        "--fixture",
        default=str(ROOT / "tests" / "fixtures" / "retrieval_external_search_benchmark.yaml"),
        help="Path to retrieval benchmark fixture.",
    )
    parser.add_argument("--case", default=None, help="Optional single case id.")
    parser.add_argument("--no-search", action="store_true", help="Disable search during runs.")
    parser.add_argument("--output", default=None, help="Optional output path.")
    return parser


def _checks(case: dict[str, Any], payload: Any) -> dict[str, bool]:
    expected = dict(case.get("expected_retrieval") or {})
    reasoning_state = dict(payload.reasoning_state or payload.trace_contract.get("reasoning_state") or {})
    observation = dict(reasoning_state.get("observation_summary") or {})
    return {
        "search_usage_match": bool(payload.used_search) == bool(expected.get("should_use_search")),
        "exact_lane_match": bool(int(reasoning_state.get("exact_lane_count") or 0) > 0) == bool(expected.get("should_have_exact_lane")),
        "anchor_lane_match": bool(int(reasoning_state.get("anchor_lane_count") or 0) > 0) == bool(expected.get("should_have_anchor_lane")),
        "official_evidence_match": bool(reasoning_state.get("official_evidence_present")) == bool(expected.get("should_have_official_evidence")),
        "template_only_match": (observation.get("coverage_status") == "template_only") == bool(expected.get("should_keep_template_only")),
        "kcal_suppression_match": (int(payload.estimated_kcal or 0) <= 0) == bool(expected.get("should_suppress_kcal")),
    }


async def _run_case(case: dict[str, Any], *, allow_search: bool) -> dict[str, Any]:
    payload = await run_text_meal_canary(
        EstimateRequest(text=case["input"], allow_search=allow_search),
        provider=primary_provider,
        primary_provider=primary_provider,
        planner_provider=planner_provider,
        request_id=f"retrieval-benchmark-{case['id']}-{uuid.uuid4().hex[:6]}",
        search_adapter=search_provider if allow_search else None,
    )
    checks = _checks(case, payload)
    reasoning_state = dict(payload.reasoning_state or payload.trace_contract.get("reasoning_state") or {})
    return {
        "id": case["id"],
        "input": case["input"],
        "checks": checks,
        "pass": all(checks.values()),
        "actual": {
            "used_search": bool(payload.used_search),
            "estimated_kcal": int(payload.estimated_kcal or 0),
            "reasoning_state": reasoning_state,
            "best_estimate_mode": payload.best_estimate_mode,
            "follow_up_needed": bool(payload.follow_up_needed),
        },
        "trace_contract": payload.trace_contract,
    }


async def _run_all(cases: list[dict[str, Any]], *, allow_search: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in cases:
        result = await _run_case(case, allow_search=allow_search)
        results.append(result)
        state = result["actual"]["reasoning_state"]
        print(
            f"[{'pass' if result['pass'] else 'fail'}] {result['id']} "
            f"search={result['actual']['used_search']} "
            f"exact={int(state.get('exact_lane_count') or 0)} "
            f"anchor={int(state.get('anchor_lane_count') or 0)} "
            f"template={int(state.get('template_lane_count') or 0)} "
            f"kcal={result['actual']['estimated_kcal']}"
        )
    return results


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    cases = load_benchmark_cases(args.fixture)
    if args.case:
        cases = [case for case in cases if case.get("id") == args.case]
    if not cases:
        raise SystemExit("No benchmark cases matched.")

    results = asyncio.run(_run_all(cases, allow_search=not bool(args.no_search)))
    summary = {
        "total_cases": len(results),
        "passed": sum(1 for item in results if item["pass"]),
        "failed": sum(1 for item in results if not item["pass"]),
    }
    report = {"fixture": str(Path(args.fixture).resolve()), "summary": summary, "cases": results}

    now_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = Path(args.output) if args.output else ROOT / ".logs" / f"retrieval_external_search_benchmark_{now_tag}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
