from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval_bootstrap import build_bootstrap_checklist, build_bundle_verdict
from scripts.live_eval_readiness import (
    DEFAULT_LOCAL_LIVE_BASE_URL,
    build_live_preflight_report,
    fetch_server_ping,
)
from scripts.runner_timeout_contract import apply_runner_timeout_contract


DEFAULT_BASE_URL = DEFAULT_LOCAL_LIVE_BASE_URL
OUTPUT_DIR = ROOT / "runtime" / "evals" / "v2_bundle1_live"


def _post_json(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        urllib.parse.urljoin(base_url, path),
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(base_url: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(urllib.parse.urljoin(base_url, path) + query, method="GET")
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_text(base_url: str, path: str, params: dict[str, Any] | None = None) -> str:
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(urllib.parse.urljoin(base_url, path) + query, method="GET")
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read().decode("utf-8")


def _contains_int(text: str, value: int) -> bool:
    return str(int(value)) in text


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def _count_digits(text: str) -> int:
    return len(re.findall(r"\d+", text))


def _same_turn_sync_checks(*, result: dict[str, Any], trace: dict[str, Any], today: dict[str, Any]) -> dict[str, bool]:
    budget_summary = (trace.get("tool_outputs") or {}).get("budget_summary") or {}
    predicted_remaining = budget_summary.get("predicted_remaining_kcal_after")
    sidecar_remaining = (((result.get("sidecar") or {}).get("ui") or {}).get("today") or {}).get("remaining_kcal")
    if predicted_remaining is None:
        predicted_remaining = sidecar_remaining
    if predicted_remaining is None:
        predicted_remaining = today.get("remaining_kcal")
    predicted_remaining = int(predicted_remaining or 0)
    return {
        "reply_remaining_matches_predicted": _contains_int(result.get("assistant_message", ""), predicted_remaining),
        "sidecar_remaining_matches_predicted": int(sidecar_remaining or 0) == predicted_remaining,
        "today_remaining_matches_predicted": int(today.get("remaining_kcal") or 0) == predicted_remaining,
        "response_sidecar_today_budget_sync": _contains_int(result.get("assistant_message", ""), predicted_remaining)
        and int(sidecar_remaining or 0) == predicted_remaining
        and int(today.get("remaining_kcal") or 0) == predicted_remaining,
    }


def _fresh_user(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    journey: str
    priority: str
    description: str


def _onboarding_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "sex": "female",
        "age_years": 28,
        "height_cm": 162,
        "current_weight_kg": 63,
        "goal_type": "lose_weight",
        "target_weight_kg": 55,
        "weekly_target_rate_kg": 0.5,
        "timezone": "Asia/Taipei",
    }
    payload.update(overrides)
    return payload


def _meal_lurou() -> str:
    return "\u6211\u525b\u5403\u4e86\u4e00\u7897\u6ef7\u8089\u98ef\u548c\u4e00\u676f\u7121\u7cd6\u8c46\u6f3f"


def _meal_multi() -> str:
    return "\u6211\u525b\u5403\u4e86\u6392\u9aa8\u4fbf\u7576\u3001\u4e00\u676f\u7121\u7cd6\u7da0\u8336\u3001\u9084\u6709\u4e00\u9846\u8336\u8449\u86cb"


def _meal_beef_noodle() -> str:
    return "\u6211\u525b\u5403\u4e86\u4e00\u7897\u725b\u8089\u9eb5"


def _budget_query() -> str:
    return "\u6211\u4eca\u5929\u9084\u80fd\u5403\u591a\u5c11\uff1f"


def _run_case_a001(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle1-a001")
    onboarding = _post_json(
        base_url,
        "/v2/estimate",
        {"user_id": user_id, "local_date": local_date, "onboarding": _onboarding_payload(activity_level="sedentary")},
    )
    reply = onboarding["assistant_message"]
    body_plan = _get_json(base_url, "/body-plan/active", {"user_id": user_id})
    today = _get_json(base_url, "/today/current-budget", {"user_id": user_id, "local_date": local_date})
    request_id = onboarding["audit"]["request_id"]
    trace = _get_json(base_url, onboarding["audit"]["admin_trace_url"])
    checks = {
        "chat_has_tdee": "TDEE" in reply,
        "chat_has_target": "Daily target" in reply,
        "chat_contains_ui_tdee": _contains_int(reply, int(body_plan["estimated_tdee"] or 0)),
        "chat_contains_ui_target": _contains_int(reply, int(body_plan["daily_budget_kcal"] or 0)),
        "body_plan_created": body_plan["body_plan_id"] is not None,
        "ledger_seeded": today["budget_kcal"] == body_plan["daily_budget_kcal"] and today["consumed_kcal"] == 0,
        "trace_roundtrip": trace.get("request_id") == request_id,
    }
    return {
        "case_id": "A-001",
        "user_id": user_id,
        "passed": all(checks.values()),
        "checks": checks,
        "request_id": request_id,
        "assistant_message": reply,
        "today": today,
        "body_plan": body_plan,
    }


def _run_case_a002(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle1-a002")
    onboarding = _post_json(
        base_url,
        "/v2/estimate",
        {
            "user_id": user_id,
            "local_date": local_date,
            "onboarding": _onboarding_payload(
                sex="male",
                age_years=30,
                height_cm=175,
                current_weight_kg=80,
                target_weight_kg=70,
                activity_level=None,
            ),
        },
    )
    body_plan = _get_json(base_url, "/body-plan/active", {"user_id": user_id})
    checks = {
        "body_plan_created": body_plan["body_plan_id"] is not None,
        "activity_fallback_applied": body_plan["activity_level"] == "sedentary",
        "tdee_positive": int(body_plan["estimated_tdee"] or 0) > 0,
        "request_trace_present": bool(onboarding["audit"]["request_id"]),
    }
    return {"case_id": "A-002", "user_id": user_id, "passed": all(checks.values()), "checks": checks, "body_plan": body_plan}


def _run_case_a003(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle1-a003")
    onboarding = _post_json(
        base_url,
        "/v2/estimate",
        {
            "user_id": user_id,
            "local_date": local_date,
            "onboarding": _onboarding_payload(
                sex="female",
                age_years=25,
                height_cm=160,
                current_weight_kg=65,
                activity_level="sedentary",
                weekly_target_rate_kg=1.5,
            ),
        },
    )
    body_plan = _get_json(base_url, "/body-plan/active", {"user_id": user_id})
    checks = {
        "body_plan_created": body_plan["body_plan_id"] is not None,
        "floor_applied": int(body_plan["daily_budget_kcal"] or 0) >= 1200,
        "safety_floor_present": int(body_plan["safety_floor_kcal"] or 0) == 1200,
        "chat_has_target": "Daily target" in onboarding["assistant_message"],
    }
    return {"case_id": "A-003", "user_id": user_id, "passed": all(checks.values()), "checks": checks, "body_plan": body_plan}


def _seed_onboarding(base_url: str, user_id: str, local_date: str) -> dict[str, Any]:
    return _post_json(
        base_url,
        "/v2/estimate",
        {
            "user_id": user_id,
            "local_date": local_date,
            "onboarding": {
                "sex": "female",
                "age_years": 30,
                "height_cm": 165,
                "current_weight_kg": 58,
                "daily_lifestyle": "sedentary_with_some_walking",
                "weekly_exercise_days_band": "3_4",
                "goal_type": "lose_weight",
                "weekly_target_rate_kg": 0.5,
                "timezone": "Asia/Taipei",
            },
        },
    )


def _run_case_b001(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle1-b001")
    _seed_onboarding(base_url, user_id, local_date)
    result = _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": _meal_lurou()})
    reply = result["assistant_message"]
    today = _get_json(base_url, "/today/current-budget", {"user_id": user_id, "local_date": local_date})
    trace = _get_json(base_url, result["audit"]["admin_trace_url"])
    checks = {
        "reply_has_food_names": _contains_any(reply, ["滷肉飯", "豆漿"]),
        "reply_has_total_number": _count_digits(reply) >= 2,
        "reply_has_remaining": "Remaining" in reply,
        "canonical_commit": result["state_delta"]["canonical_commit"] is True,
        "today_consumed_positive": int(today["consumed_kcal"] or 0) > 0,
        "today_remaining_matches_budget_math": int(today["remaining_kcal"] or 0) == int(today["budget_kcal"] or 0) - int(today["consumed_kcal"] or 0),
        "trace_roundtrip": trace.get("request_id") == result["request_id"],
        **_same_turn_sync_checks(result=result, trace=trace, today=today),
    }
    return {"case_id": "B-001", "user_id": user_id, "passed": all(checks.values()), "checks": checks, "assistant_message": reply, "today": today}


def _run_case_b002(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle1-b002")
    _seed_onboarding(base_url, user_id, local_date)
    _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": _meal_lurou()})
    result = _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": _budget_query()})
    reply = result["assistant_message"]
    today = _get_json(base_url, "/today/current-budget", {"user_id": user_id, "local_date": local_date})
    checks = {
        "target_in_reply": _contains_int(reply, int(today["budget_kcal"] or 0)),
        "consumed_in_reply": _contains_int(reply, int(today["consumed_kcal"] or 0)),
        "remaining_in_reply": _contains_int(reply, int(today["remaining_kcal"] or 0)),
        "no_llm_recalc_drift": result["remaining_budget"]["remaining_kcal"] == today["remaining_kcal"],
    }
    return {"case_id": "B-002", "user_id": user_id, "passed": all(checks.values()), "checks": checks, "assistant_message": reply, "today": today}


def _run_case_b003(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle1-b003")
    _seed_onboarding(base_url, user_id, local_date)
    result = _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": _meal_multi()})
    today = _get_json(base_url, "/today/current-budget", {"user_id": user_id, "local_date": local_date})
    trace = _get_json(base_url, result["audit"]["admin_trace_url"])
    payload = (
        ((trace.get("tool_outputs") or {}).get("nutrition_payload") or {})
        or (((trace.get("tool_outputs") or {}).get("nutrition_artifact") or {}).get("payload") or {})
    )
    checks = {
        "canonical_commit": result["state_delta"]["canonical_commit"] is True,
        "one_meal_thread": int(today["active_meal_count"] or 0) == 1,
        "three_components": len(payload.get("component_estimates") or []) == 3,
        "reply_has_total": _count_digits(result["assistant_message"]) >= 2,
    }
    return {
        "case_id": "B-003",
        "user_id": user_id,
        "request_id": result["audit"]["request_id"],
        "passed": all(checks.values()),
        "checks": checks,
        "assistant_message": result["assistant_message"],
        "trace_payload": payload,
    }


def _run_case_b004(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle1-b004")
    result = _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": _meal_beef_noodle()})
    reply = result["assistant_message"]
    today = _get_json(base_url, "/today/current-budget", {"user_id": user_id, "local_date": local_date})
    checks = {
        "intake_not_blocked": result["manager_decision"]["intent_type"] == "log_meal",
        "reply_has_kcal_number": _count_digits(reply) >= 1,
        "reply_has_no_remaining": "Remaining" not in reply and "target" not in reply.lower(),
        "today_has_no_budget": int(today["budget_kcal"] or 0) == 0,
    }
    return {"case_id": "B-004", "user_id": user_id, "passed": all(checks.values()), "checks": checks, "assistant_message": reply, "today": today}


def _run_case_j001(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle1-j001")
    result = _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": _budget_query()})
    reply = result["assistant_message"]
    today = _get_json(base_url, "/today/current-budget", {"user_id": user_id, "local_date": local_date})
    checks = {
        "onboarding_required": result["manager_decision"]["intent_type"] == "onboarding_required",
        "reply_mentions_onboarding": "onboarding" in reply.lower(),
        "reply_has_no_kcal": "kcal" not in reply.lower(),
        "today_no_budget": int(today["budget_kcal"] or 0) == 0 and int(today["remaining_kcal"] or 0) == 0,
    }
    return {"case_id": "J-001", "user_id": user_id, "passed": all(checks.values()), "checks": checks, "assistant_message": reply, "today": today}


def _run_case_j002(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle1-j002")
    result = _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": _meal_beef_noodle()})
    reply = result["assistant_message"]
    today = _get_json(base_url, "/today/current-budget", {"user_id": user_id, "local_date": local_date})
    checks = {
        "intake_allowed": result["manager_decision"]["intent_type"] == "log_meal",
        "reply_has_kcal_number": _count_digits(reply) >= 1,
        "reply_has_no_remaining": "Remaining" not in reply and "target" not in reply.lower(),
        "no_budget_ledger_created": int(today["budget_kcal"] or 0) == 0,
    }
    return {"case_id": "J-002", "user_id": user_id, "passed": all(checks.values()), "checks": checks, "assistant_message": reply, "today": today}


CASE_RUNNERS = [
    _run_case_a001,
    _run_case_a002,
    _run_case_a003,
    _run_case_b001,
    _run_case_b002,
    _run_case_b003,
    _run_case_b004,
    _run_case_j001,
    _run_case_j002,
]

CASE_RUNNER_MAP: dict[str, Callable[[str, str], dict[str, Any]]] = {
    "A-001": _run_case_a001,
    "A-002": _run_case_a002,
    "A-003": _run_case_a003,
    "B-001": _run_case_b001,
    "B-002": _run_case_b002,
    "B-003": _run_case_b003,
    "B-004": _run_case_b004,
    "J-001": _run_case_j001,
    "J-002": _run_case_j002,
}


def _select_case_runners(case_ids: list[str] | None) -> list[tuple[str, Callable[[str, str], dict[str, Any]]]]:
    if not case_ids:
        return list(CASE_RUNNER_MAP.items())
    unknown = [case_id for case_id in case_ids if case_id not in CASE_RUNNER_MAP]
    if unknown:
        raise ValueError(f"Unknown case_id(s): {', '.join(unknown)}")
    return [(case_id, CASE_RUNNER_MAP[case_id]) for case_id in case_ids]


def _run_mode(case_ids: list[str] | None) -> str:
    if not case_ids:
        return "full"
    return "single_case" if len(case_ids) == 1 else "shard"


def _selection_metadata(case_ids: list[str] | None, *, completed_cases: int = 0) -> dict[str, Any]:
    selected = _select_case_runners(case_ids)
    run_mode = _run_mode(case_ids)
    return {
        "run_mode": run_mode,
        "selected_case_ids": [case_id for case_id, _ in selected],
        "expected_total_cases": len(selected),
        "completed_cases": completed_cases,
        "full_acceptance_package_run": run_mode == "full",
    }


def _runner_case_status(*, all_cases_pass: bool, run_mode: str) -> str:
    if run_mode != "full":
        return "diagnostic"
    return "pass" if all_cases_pass else "fail"


def _readiness_claim_scope_for_run(*, live_preflight_scope: str, run_mode: str) -> str:
    if run_mode != "full":
        return "diagnostic_case_run"
    return live_preflight_scope


def _case_error_result(case_id: str, exc: Exception) -> dict[str, Any]:
    if isinstance(exc, urllib.error.HTTPError):
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "case_id": case_id,
            "passed": False,
            "checks": {"http_ok": False},
            "error": {"status": exc.code, "body": body},
        }
    return {
        "case_id": case_id,
        "passed": False,
        "checks": {"runner_ok": False},
        "error": {"type": type(exc).__name__, "message": str(exc)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Bundle 1 live E2E eval cases against /v2/estimate.")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument("--local-date", default=datetime.now().date().isoformat())
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    selected_case_runners = _select_case_runners(args.case_id)
    selection = _selection_metadata(args.case_id)
    base_url = args.base_url or DEFAULT_BASE_URL
    base_url_explicit = args.base_url is not None
    ping_payload, ping_error = fetch_server_ping(base_url)
    live_preflight = build_live_preflight_report(
        base_url=base_url,
        base_url_explicit=base_url_explicit,
        ping_payload=ping_payload,
        ping_error=ping_error,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output) if args.output else OUTPUT_DIR / f"bundle1_live_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    results: list[dict[str, Any]] = []
    for case_id, runner in selected_case_runners:
        try:
            case_result = runner(base_url, args.local_date)
        except urllib.error.HTTPError as exc:
            case_result = _case_error_result(case_id, exc)
        except Exception as exc:
            case_result = _case_error_result(case_id, exc)
        results.append(case_result)
        status = "PASS" if case_result["passed"] else "FAIL"
        print(f"{case_result['case_id']}: {status}")

    selection = _selection_metadata(args.case_id, completed_cases=len(results))
    p0_ids = {"A-001", "B-001", "B-002", "J-001"}
    p0_pass = all(result["passed"] for result in results if result["case_id"] in p0_ids)
    all_cases_pass = all(result["passed"] for result in results)
    bootstrap = build_bootstrap_checklist(bundle=1)
    coverage_status = bootstrap["parity_audit"]["coverage_status"]
    founder_status = bootstrap["founder_realism"]["status"]
    runner_case_status = _runner_case_status(all_cases_pass=all_cases_pass, run_mode=selection["run_mode"])
    readiness_claim_scope = _readiness_claim_scope_for_run(
        live_preflight_scope=live_preflight["readiness_claim_scope"],
        run_mode=selection["run_mode"],
    )
    verdict = build_bundle_verdict(
        runner_case_status=runner_case_status,
        coverage_status=coverage_status,
        founder_realism_status=founder_status,
        checklist=bootstrap,
    )
    summary = {
        "total_cases": len(results),
        "passed_cases": sum(1 for result in results if result["passed"]),
        "failed_cases": [result["case_id"] for result in results if not result["passed"]],
        "p0_pass": p0_pass,
        "all_cases_pass": all_cases_pass,
        "live_test_mode": live_preflight["live_test_mode"],
        "server_ping_status": live_preflight["server_ping_status"],
        "phase_c_gate_status": "not_applicable",
        "readiness_claim_scope": readiness_claim_scope,
        **selection,
        **verdict,
    }
    report = {
        "base_url": base_url,
        **selection,
        "live_test_mode": live_preflight["live_test_mode"],
        "server_ping_status": live_preflight["server_ping_status"],
        "provider_readiness": live_preflight["provider_readiness"],
        "readiness_claim_scope": readiness_claim_scope,
        "phase_c_gate_status": "not_applicable",
        "live_preflight": live_preflight,
        "local_date": args.local_date,
        "bootstrap_checklist": bootstrap,
        "summary": summary,
        "cases": results,
    }
    report = apply_runner_timeout_contract(
        report,
        expected_total_cases=selection["expected_total_cases"],
        completed_cases=len(results),
        run_mode=selection["run_mode"],
    )
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = report["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"saved: {output_path}")
    if selection["run_mode"] != "full":
        return 0 if all_cases_pass else 1
    return 0 if summary["runner_case_status"] == "pass" and summary["coverage_status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
