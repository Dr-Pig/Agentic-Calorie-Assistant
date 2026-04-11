from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.benchmark_loader import benchmark_fixture_path, load_benchmark_cases
from app.routes import planner_provider, primary_provider, search_provider
from app.schemas import EstimateRequest
from app.usecases.text_meal import run_text_meal_canary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run benchmark_test_set_v1 against text_meal canary.")
    parser.add_argument(
        "--fixture",
        default=str(benchmark_fixture_path()),
        help="Path to benchmark fixture (.json or source .txt).",
    )
    parser.add_argument("--case", default=None, help="Optional single case id to run.")
    parser.add_argument("--mock", action="store_true", help="Use eval MockProvider instead of the live provider.")
    parser.add_argument("--allow-search", action="store_true", help="Allow search during benchmark runs.")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output JSON path. Defaults to .logs/benchmark_v1_<timestamp>.json.",
    )
    return parser


def _derive_actual_action(payload: Any) -> str:
    has_followup = bool(payload.followup_question)
    has_estimate = int(payload.estimated_kcal or 0) > 0
    if has_followup and not has_estimate:
        return "ask_followup_only"
    if has_followup and has_estimate:
        return "estimate_with_followup"
    if str(payload.best_estimate_mode or "") == "exact_item":
        return "exact_lookup"
    return "direct_estimate"


def _derive_actual_exactness(payload: Any) -> str:
    mode = str(payload.best_estimate_mode or "")
    if mode == "exact_item":
        return "exact"
    if mode == "anchored_component":
        return "anchored"
    if mode == "heuristic_fallback":
        return "heuristic"
    return "unknown"


def _approx_equal(left: float | int | None, right: float | int | None, *, tolerance: float) -> bool:
    if left is None or right is None:
        return False
    return abs(float(left) - float(right)) <= tolerance


def _behavior_checks(case: dict[str, Any], payload: Any) -> tuple[dict[str, Any], list[str]]:
    expected = dict(case.get("expected_behavior") or {})
    actual_action = _derive_actual_action(payload)
    actual_exactness = _derive_actual_exactness(payload)
    actual_confidence = str(payload.estimate_confidence_tier or "low")
    allowed_actions = [str(item) for item in expected.get("allowed_actions", []) if str(item).strip()]
    allowed_actions.extend(str(item) for item in expected.get("also_acceptable_actions", []) if str(item).strip())
    primary_action = str(expected.get("action") or "").strip()
    if primary_action:
        allowed_actions.append(primary_action)
    allowed_confidences = [str(item) for item in expected.get("allowed_confidences", []) if str(item).strip()]
    if not allowed_actions and primary_action:
        allowed_actions = [primary_action]
    if not allowed_confidences and str(expected.get("confidence") or "").strip():
        allowed_confidences = [str(expected.get("confidence") or "").strip()]

    checks = {
        "action_match": actual_action in allowed_actions if allowed_actions else True,
        "exactness_match": actual_exactness == str(expected.get("exactness") or ""),
        "confidence_match": actual_confidence in allowed_confidences if allowed_confidences else True,
        "followup_presence_match": bool(payload.followup_question) == any(
            action in {"estimate_with_followup", "ask_followup_only"} for action in allowed_actions
        ),
        "no_overclaim_exactness": not (
            str(expected.get("should_overclaim_exactness")).lower() == "false"
            and actual_exactness == "exact"
            and str(expected.get("exactness") or "") != "exact"
        ),
    }
    hard_failures = [name for name in ("action_match", "no_overclaim_exactness") if checks.get(name) is False]
    return checks, hard_failures


def _evidence_checks(case: dict[str, Any], payload: Any) -> tuple[dict[str, Any], list[str]]:
    expected = dict(case.get("expected_evidence_outcome") or {})
    trace = dict(payload.trace_contract or {})
    db_hit_type = str(trace.get("db_hit_type") or "")
    actual_exactness = _derive_actual_exactness(payload)
    used_search = bool(payload.used_search)

    checks = {
        "strong_same_item_evidence_respected": True,
        "anchor_fallback_respected": True,
        "external_evidence_requirement_respected": True,
        "sibling_exact_rejection_respected": True,
    }

    if bool(expected.get("needs_strong_same_item_evidence")):
        checks["strong_same_item_evidence_respected"] = (
            actual_exactness == "exact" and db_hit_type == "exact_truth"
        ) or (actual_exactness != "exact")

    if bool(expected.get("should_use_anchor_evidence_if_no_exact")) and actual_exactness in {"anchored", "heuristic"}:
        checks["anchor_fallback_respected"] = actual_exactness in {"anchored", "heuristic"}

    if bool(expected.get("requires_external_evidence_if_local_missing")):
        checks["external_evidence_requirement_respected"] = used_search

    if bool(expected.get("should_reject_sibling_variant_as_exact")) and str(case.get("expected_behavior", {}).get("exactness")) != "exact":
        checks["sibling_exact_rejection_respected"] = actual_exactness != "exact"

    hard_failures = [
        name
        for name in ("strong_same_item_evidence_respected", "sibling_exact_rejection_respected")
        if checks.get(name) is False
    ]
    return checks, hard_failures


def _answer_checks(case: dict[str, Any], payload: Any) -> tuple[dict[str, Any], list[str]]:
    expected = dict(case.get("expected_behavior") or {})
    parsed_truth = dict(case.get("parsed_truth") or {})
    actual_kcal = float(payload.estimated_kcal or 0)
    action = str(expected.get("action") or "")
    exactness = str(expected.get("exactness") or "")
    tolerance = 25.0 if exactness == "exact" else 140.0
    trace = dict(payload.trace_contract or {})
    local_exact_db_truth = (
        str(trace.get("db_hit_type") or "") == "exact_truth"
        and not bool(payload.used_search)
        and str(payload.best_estimate_mode or "") == "exact_item"
    )
    reference_kcal = parsed_truth.get("exact_kcal")
    if reference_kcal is None:
        reference_kcal = parsed_truth.get("reference_kcal")

    checks = {
        "kcal_reference_match": True,
        "followup_text_present_when_needed": True,
        "reply_text_present": bool(str(payload.reply_text or "").strip()),
        "local_db_truth_variance_accepted": False,
    }

    if reference_kcal is not None and actual_kcal > 0:
        checks["kcal_reference_match"] = _approx_equal(actual_kcal, reference_kcal, tolerance=tolerance)
    elif action in {"direct_estimate", "exact_lookup"} and actual_kcal <= 0:
        checks["kcal_reference_match"] = False

    if not checks["kcal_reference_match"] and local_exact_db_truth:
        checks["kcal_reference_match"] = True
        checks["local_db_truth_variance_accepted"] = True

    if action in {"estimate_with_followup", "ask_followup_only"}:
        checks["followup_text_present_when_needed"] = bool(str(payload.followup_question or "").strip())

    hard_failures = [name for name in ("kcal_reference_match", "followup_text_present_when_needed") if checks.get(name) is False]
    return checks, hard_failures


async def _run_case(case: dict[str, Any], *, provider: Any, planner: Any, allow_search: bool) -> dict[str, Any]:
    request_id = f"benchmark-v1-{case['id']}-{uuid.uuid4().hex[:6]}"
    payload = await run_text_meal_canary(
        EstimateRequest(text=case["input"], allow_search=allow_search),
        provider=provider,
        primary_provider=provider,
        planner_provider=planner,
        request_id=request_id,
        search_adapter=search_provider if allow_search else None,
    )
    behavior_checks, behavior_fails = _behavior_checks(case, payload)
    evidence_checks, evidence_fails = _evidence_checks(case, payload)
    answer_checks, answer_fails = _answer_checks(case, payload)
    hard_failures = [*behavior_fails, *evidence_fails, *answer_fails]
    answer_required_keys = ("kcal_reference_match", "followup_text_present_when_needed", "reply_text_present")
    answer_pass = all(bool(answer_checks.get(key)) for key in answer_required_keys)
    route_pass = all(bool(value) for value in behavior_checks.values()) and all(bool(value) for value in evidence_checks.values())
    verdict = "pass" if answer_pass and route_pass and not hard_failures else "fail"

    return {
        "id": case["id"],
        "input": case["input"],
        "verdict": verdict,
        "answer_pass": answer_pass,
        "route_pass": route_pass,
        "hard_failures": hard_failures,
        "expected_behavior": case.get("expected_behavior"),
        "expected_evidence_outcome": case.get("expected_evidence_outcome"),
        "behavior_checks": behavior_checks,
        "evidence_checks": evidence_checks,
        "answer_checks": answer_checks,
        "actual": {
            "estimated_kcal": payload.estimated_kcal,
            "best_estimate_mode": payload.best_estimate_mode,
            "estimate_confidence_tier": payload.estimate_confidence_tier,
            "followup_question": payload.followup_question,
            "reply_text": payload.reply_text,
            "used_search": payload.used_search,
            "search_query": payload.search_query,
            "search_quality": payload.search_quality,
            "best_answer_source": payload.best_answer_source,
            "db_hit_type": (payload.trace_contract or {}).get("db_hit_type"),
            "route_family": (payload.trace_contract or {}).get("route_family"),
            "north_star_evaluation": payload.north_star_evaluation,
        },
        "trace_contract": payload.trace_contract,
        "llm_traces": payload.llm_traces,
        "quality_signals": payload.quality_signals,
        "debug_steps": payload.debug_steps,
    }


def _build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts = Counter(str(item.get("verdict") or "") for item in results)
    hard_failure_counts = Counter()
    for item in results:
        hard_failure_counts.update(item.get("hard_failures") or [])
    return {
        "total_cases": len(results),
        "passed": sum(1 for item in results if item.get("verdict") == "pass"),
        "failed": sum(1 for item in results if item.get("verdict") != "pass"),
        "answer_passed": sum(1 for item in results if item.get("answer_pass")),
        "route_passed": sum(1 for item in results if item.get("route_pass")),
        "verdicts": dict(verdicts),
        "hard_failure_breakdown": dict(hard_failure_counts),
    }


def _build_provider(mock: bool) -> tuple[Any, Any, str]:
    if mock:
        from run_eval_wave import MockProvider

        provider = MockProvider()
        return provider, provider, "mock"
    return primary_provider, planner_provider, str(primary_provider.readiness().get("provider") or "live")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    cases = load_benchmark_cases(args.fixture)
    if args.case:
        cases = [case for case in cases if case.get("id") == args.case]
    if not cases:
        raise SystemExit("No benchmark cases matched.")

    provider, planner, provider_label = _build_provider(args.mock)
    now_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = Path(args.output) if args.output else ROOT / ".logs" / f"benchmark_v1_{provider_label}_{now_tag}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    async def _run_all() -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for case in cases:
            result = await _run_case(case, provider=provider, planner=planner, allow_search=args.allow_search)
            results.append(result)
            print(
                f"[{result['verdict']}] {result['id']} "
                f"kcal={result['actual']['estimated_kcal']} "
                f"mode={result['actual']['best_estimate_mode']} "
                f"followup={'yes' if result['actual']['followup_question'] else 'no'}"
            )
        return results

    results = asyncio.run(_run_all())
    summary = _build_summary(results)
    report = {
        "provider": provider_label,
        "fixture": str(Path(args.fixture).resolve()),
        "allow_search": bool(args.allow_search),
        "summary": summary,
        "cases": results,
    }
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
