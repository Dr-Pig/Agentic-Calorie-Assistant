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
    parser = argparse.ArgumentParser(description="Run nutrition output contract benchmark.")
    parser.add_argument(
        "--fixture",
        default=str(ROOT / "tests" / "fixtures" / "nutrition_output_contract_benchmark.yaml"),
        help="Path to nutrition contract fixture.",
    )
    parser.add_argument("--case", default=None, help="Optional single case id.")
    parser.add_argument("--no-search", action="store_true", help="Disable search during runs.")
    parser.add_argument("--output", default=None, help="Optional output path.")
    return parser


def _macro_mode(payload: Any) -> str:
    return str((payload.macro_breakdown or {}).get("macro_source") or "unavailable")


def _contract_checks(case: dict[str, Any], payload: Any) -> dict[str, bool]:
    expected_contract = dict((case.get("expected_contract") or {}))
    component_breakdown_required = bool(expected_contract.get("component_breakdown_required"))
    evidence_ids_required = bool(expected_contract.get("evidence_ids_required"))
    expected_macro_mode = str(expected_contract.get("macro_mode") or "")
    return {
        "kcal_present": int(payload.estimated_kcal or 0) > 0,
        "component_breakdown_present": (not component_breakdown_required) or bool(payload.component_breakdown),
        "evidence_ids_respected": (not evidence_ids_required) or bool(payload.evidence_ids_used),
        "macro_mode_match": (not expected_macro_mode) or _macro_mode(payload) == expected_macro_mode,
    }


async def _run_case(case: dict[str, Any], *, allow_search: bool) -> dict[str, Any]:
    payload = await run_text_meal_canary(
        EstimateRequest(text=case["input"], allow_search=allow_search),
        provider=primary_provider,
        primary_provider=primary_provider,
        planner_provider=planner_provider,
        request_id=f"nutrition-contract-{case['id']}-{uuid.uuid4().hex[:6]}",
        search_adapter=search_provider if allow_search else None,
    )
    checks = _contract_checks(case, payload)
    return {
        "id": case["id"],
        "input": case["input"],
        "checks": checks,
        "pass": all(checks.values()),
        "actual": {
            "estimated_kcal": payload.estimated_kcal,
            "component_breakdown_count": len(payload.component_breakdown or []),
            "evidence_ids_used": list(payload.evidence_ids_used or []),
            "macro_source": _macro_mode(payload),
            "macro_breakdown": payload.macro_breakdown,
            "best_estimate_mode": payload.best_estimate_mode,
        },
        "trace_contract": payload.trace_contract,
    }


async def _run_all(cases: list[dict[str, Any]], *, allow_search: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in cases:
        result = await _run_case(case, allow_search=allow_search)
        results.append(result)
        print(
            f"[{'pass' if result['pass'] else 'fail'}] {result['id']} "
            f"kcal={result['actual']['estimated_kcal']} "
            f"components={result['actual']['component_breakdown_count']} "
            f"macro={result['actual']['macro_source']}"
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
    output_path = Path(args.output) if args.output else ROOT / ".logs" / f"nutrition_contract_benchmark_{now_tag}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
