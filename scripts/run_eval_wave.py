"""Batch evaluation runner for text_meal canary.

Usage:
    # Mock provider (offline, tests trace contract + evaluator logic):
    python scripts/run_eval_wave.py --mode eval --mock

    # Real provider (online, full end-to-end):
    python scripts/run_eval_wave.py --mode eval

    # Retrieval-only mode (reuses retrieval_sanity_cases.json):
    python scripts/run_eval_wave.py --mode retrieval
"""
from __future__ import annotations

import argparse
import asyncio
import collections
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

from app.agent.local_knowledge_selector import search_local_knowledge
from app.schemas import EstimateRequest
from app.usecases.text_meal import run_text_meal_canary


# ---------------------------------------------------------------------------
# Mock provider — returns a plausible structured answer without network calls
# ---------------------------------------------------------------------------

class MockProvider:
    """Returns a canned structured JSON answer for offline evaluator testing.

    The mock gives a generic mid-range answer so the evaluator + trace
    contract logic can be exercised end-to-end without LLM calls.
    """

    async def complete_with_trace(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        stage: str,
        max_tokens: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_input = str(user_payload.get("user_input") or user_payload.get("raw_user_input") or "")
        trace = {
            "stage": stage,
            "provider": "mock",
            "model": "mock-eval",
            "raw_content": "{}",
            "parsed_object": None,
            "finish_reason": "stop",
            "completion_tokens": 0,
            "prompt_tokens": 0,
        }
        if stage.startswith("planner_pass"):
            parsed = {
                "intent": "food_estimation",
                "route": "estimation",
                "normalized_user_input": user_input,
                "input_signals": {"modalities": ["text"], "foods": [], "brands": [], "portion_clues": []},
                "missing_info": [],
                "route_hints": {},
            }
        else:
            kcal_most = 420
            if "拉麵" in user_input:
                kcal_most = 900
            
            parsed = {
                "food_origin": "generic_common",
                "food_class": "mixed_meal",
                "dish_structure": "multi_component_simple",
                "needs_external_data": True,
                "private_info_risk": "low",
                "title": user_input,
                "components": ["主食", "蛋白質", "蔬菜"],
                "protein_g": 20,
                "carb_g": 50,
                "fat_g": 15,
                "kcal_low": kcal_most - 50,
                "kcal_high": kcal_most + 100,
                "kcal_most_likely": kcal_most,
                "uncertainty_factors": ["份量不明"],
                "followup_questions": [],
                "top_uncertainty_drivers": [
                    {"driver_type": "portion_size", "reason": "份量不明"},
                ],
                "external_data_query": user_input,
            }
        trace["parsed_object"] = parsed
        return parsed, trace


# ---------------------------------------------------------------------------
# Retrieval-only runner (reuses retrieval_sanity_cases.json format)
# ---------------------------------------------------------------------------

def _title_matches(expected: str, actual: str) -> bool:
    e, a = str(expected or "").strip(), str(actual or "").strip()
    return bool(e and a and (e in a or a in e))


def _brand_matches(expected: str, actual: str) -> bool:
    e, a = str(expected or "").strip(), str(actual or "").strip()
    if not e:
        return not a
    return bool(a and (e in a or a in e))


def _run_retrieval_case(case: dict[str, Any]) -> dict[str, Any]:
    query = str(case["query"])
    docs = search_local_knowledge(query, user_input=query, limit=5)
    top = docs[0] if docs else {}
    title_ok = _title_matches(str(case.get("expected_title", "")), str(top.get("title", "")))
    brand_ok = _brand_matches(str(case.get("expected_brand", "")), str(top.get("brand", "")))
    exact_ok = top.get("evidence_role") == "exact_truth"
    confidence_ok = top.get("match_confidence") in {"high", "medium"}
    passed = bool(docs and title_ok and brand_ok and exact_ok and confidence_ok)
    return {
        "id": case["id"],
        "bucket": case["bucket"],
        "query": query,
        "passed": passed,
        "verdict": "win" if passed else "loss",
        "checks": {"title_ok": title_ok, "brand_ok": brand_ok, "exact_ok": exact_ok, "confidence_ok": confidence_ok},
        "top_hit": {
            "title": top.get("title"),
            "brand": top.get("brand"),
            "evidence_role": top.get("evidence_role"),
            "match_confidence": top.get("match_confidence"),
        },
    }


# ---------------------------------------------------------------------------
# Full eval runner
# ---------------------------------------------------------------------------

async def _run_eval_case(
    case: dict[str, Any],
    *,
    provider: Any,
) -> dict[str, Any]:
    request = EstimateRequest(text=case["input_text"], allow_search=False)
    request_id = f"eval-{case['id']}-{uuid.uuid4().hex[:6]}"

    payload = await run_text_meal_canary(
        request,
        provider=provider,
        request_id=request_id,
    )

    trace_contract = payload.trace_contract or {}
    north_star = payload.north_star_evaluation or {}

    # --- Compare against expectations ---
    checks: dict[str, Any] = {}

    # kcal plausible range
    kcal_range = case.get("kcal_plausible_range")
    if kcal_range and payload.estimated_kcal > 0:
        checks["kcal_in_range"] = kcal_range[0] <= payload.estimated_kcal <= kcal_range[1]
    elif kcal_range:
        checks["kcal_in_range"] = None  # can't check, kcal is 0 (possibly ASK_USER)

    # exact truth usage
    if case.get("should_use_exact_truth"):
        checks["exact_truth_used"] = trace_contract.get("db_hit_type") == "exact_truth"

    # follow-up
    checks["has_followup"] = bool(payload.followup_question)
    if case.get("should_follow_up") is True:
        checks["followup_expected_and_present"] = checks["has_followup"]
    elif case.get("should_follow_up") is False:
        checks["followup_not_expected_and_absent"] = not checks["has_followup"]

    # route family
    expected_family = case.get("expected_route_family")
    actual_family = trace_contract.get("route_family")
    if expected_family is not None:
        checks["route_family_match"] = actual_family == expected_family

    # followup policy decision
    expected_policy = case.get("expected_followup_policy_decision")
    actual_policy = trace_contract.get("followup_policy_decision")
    if expected_policy is not None:
        checks["followup_policy_match"] = actual_policy == expected_policy

    # failed layer
    expected_failed = case.get("expected_failed_layer")
    actual_failed = north_star.get("failed_layer")
    checks["failed_layer_match"] = actual_failed == expected_failed

    # risk family
    expected_risk = set(case.get("expected_risk_family", []))
    actual_risk = set(str(item) for item in trace_contract.get("risk_flags", []))
    if expected_risk:
        checks["risk_family_overlap"] = bool(expected_risk & actual_risk)

    return {
        "id": case["id"],
        "bucket": case["bucket"],
        "input_text": case["input_text"],
        "verdict": str(north_star.get("win_loss_neutral", "neutral")),
        "failed_layer": north_star.get("failed_layer"),
        "why": north_star.get("why"),
        "improved_dimension": north_star.get("improved_dimension"),
        "checks": checks,
        "actual": {
            "estimated_kcal": payload.estimated_kcal,
            "best_answer_source": payload.best_answer_source,
            "best_estimate_mode": payload.best_estimate_mode,
            "route_family": actual_family,
            "followup_policy_decision": actual_policy,
            "db_hit_type": trace_contract.get("db_hit_type"),
            "followup_question": payload.followup_question,
            "risk_flags": list(actual_risk),
            "retry_triggered": payload.retry_triggered,
            "route_target": payload.route_target,
        },
    }


# ---------------------------------------------------------------------------
# Wave summary builder
# ---------------------------------------------------------------------------

def _build_eval_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    verdict_counts = collections.Counter(str(r["verdict"]) for r in results)
    bucket_results: dict[str, dict[str, int]] = {}
    for r in results:
        b = r["bucket"]
        if b not in bucket_results:
            bucket_results[b] = {"win": 0, "neutral": 0, "loss": 0}
        v = str(r["verdict"])
        if v in bucket_results[b]:
            bucket_results[b][v] += 1

    layer_failures = collections.Counter(
        str(r["failed_layer"]) for r in results if r.get("failed_layer")
    )

    # followup precision/recall
    followup_tp = sum(1 for r in results if r["checks"].get("followup_expected_and_present") is True)
    followup_fn = sum(1 for r in results if r["checks"].get("followup_expected_and_present") is False)
    followup_fp = sum(1 for r in results if r["checks"].get("followup_not_expected_and_absent") is False)
    followup_precision = followup_tp / max(followup_tp + followup_fp, 1)
    followup_recall = followup_tp / max(followup_tp + followup_fn, 1)

    # exact truth hit rate
    exact_expected = [r for r in results if r["checks"].get("exact_truth_used") is not None]
    exact_hits = sum(1 for r in exact_expected if r["checks"].get("exact_truth_used") is True)
    exact_truth_hit_rate = exact_hits / max(len(exact_expected), 1)

    # retry & rescue
    retry_count = sum(1 for r in results if r["actual"].get("retry_triggered"))
    rescue_count = sum(1 for r in results if str(r["actual"].get("best_answer_source", "")).startswith("reference_card") or str(r["actual"].get("best_answer_source", "")).startswith("meal_template"))

    return {
        "total_cases": len(results),
        "results": dict(verdict_counts),
        "layer_failure_rate": dict(layer_failures),
        "bucket_results": bucket_results,
        "followup_precision": round(followup_precision, 3),
        "followup_recall": round(followup_recall, 3),
        "exact_truth_hit_rate": round(exact_truth_hit_rate, 3),
        "retry_count": retry_count,
        "rescue_count": rescue_count,
    }


def _build_retrieval_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_bucket: dict[str, dict[str, int]] = {}
    for r in results:
        b = r["bucket"]
        if b not in by_bucket:
            by_bucket[b] = {"total": 0, "passed": 0, "failed": 0}
        by_bucket[b]["total"] += 1
        by_bucket[b]["passed" if r["passed"] else "failed"] += 1
    return {
        "total_cases": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
        "by_bucket": by_bucket,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Batch evaluation runner for text_meal canary.")
    parser.add_argument("--mode", choices=["eval", "retrieval"], default="eval", help="Run mode.")
    parser.add_argument("--fixture", default=None, help="Override fixture path.")
    parser.add_argument("--output", default=None, help="Override output path.")
    parser.add_argument("--mock", action="store_true", help="Use mock provider (offline, no LLM calls).")
    args = parser.parse_args()

    now_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if args.mode == "retrieval":
        fixture_path = Path(args.fixture) if args.fixture else ROOT / "tests" / "fixtures" / "retrieval_sanity_cases.json"
        output_path = Path(args.output) if args.output else ROOT / ".logs" / f"eval_retrieval_{now_tag}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cases = json.loads(fixture_path.read_text(encoding="utf-8"))
        results = [_run_retrieval_case(c) for c in cases]
        summary = _build_retrieval_summary(results)
        report = {"wave_id": f"retrieval_{now_tag}", "mode": "retrieval", "summary": summary, "cases": results}
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"Saved to: {output_path}")
        return 0

    # eval mode
    fixture_path = Path(args.fixture) if args.fixture else ROOT / "tests" / "fixtures" / "eval_cases.json"
    output_path = Path(args.output) if args.output else ROOT / ".logs" / f"eval_wave_{now_tag}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    provider = MockProvider() if args.mock else _build_real_provider()

    async def _run_all() -> list[dict[str, Any]]:
        results = []
        for case in cases:
            result = await _run_eval_case(case, provider=provider)
            results.append(result)
            status = "[OK]" if result["verdict"] != "loss" else "[NG]"
            print(f"  {status} {result['id']} -> {result['verdict']}  kcal={result['actual']['estimated_kcal']}  src={result['actual']['best_answer_source']}")
        return results

    results = asyncio.run(_run_all())
    summary = _build_eval_summary(results)
    report = {
        "wave_id": f"eval_{now_tag}",
        "mode": "eval",
        "provider": "mock" if args.mock else "builderspace",
        "summary": summary,
        "cases": results,
    }
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Saved to: {output_path}")
    return 0


def _build_real_provider() -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter
    adapter = BuilderSpaceAdapter()
    if not adapter.readiness().get("configured"):
        print("ERROR: BuilderSpace is not configured. Set AI_BUILDER_TOKEN and AI_BUILDER_BASE_URL, or use --mock.")
        raise SystemExit(1)
    return adapter


if __name__ == "__main__":
    raise SystemExit(main())
