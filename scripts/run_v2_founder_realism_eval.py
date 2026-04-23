from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.text_integrity import find_text_corruption
from scripts.runner_timeout_contract import apply_runner_timeout_contract


DEFAULT_BASE_URL = "http://127.0.0.1:8010"
OUTPUT_DIR = ROOT / "runtime" / "evals" / "v2_founder_realism"


def _post_json(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        urllib.parse.urljoin(base_url, path),
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(base_url: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(urllib.parse.urljoin(base_url, path) + query, method="GET")
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fresh_user(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _seed_onboarding(base_url: str, *, user_id: str, local_date: str) -> None:
    _post_json(
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


def _trace(base_url: str, response: dict[str, Any]) -> dict[str, Any]:
    return _get_json(base_url, response["audit"]["admin_trace_url"])


def _today(base_url: str, *, user_id: str, local_date: str) -> dict[str, Any]:
    return _get_json(base_url, "/today/current-budget", {"user_id": user_id, "local_date": local_date})


def _contains_int(text: str, value: int) -> bool:
    return str(int(value)) in str(text or "")


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = str(text or "").lower()
    return any(needle.lower() in lowered for needle in needles)


def _same_turn_sync_checks(*, response: dict[str, Any], trace: dict[str, Any], today: dict[str, Any]) -> dict[str, bool]:
    budget_summary = (trace.get("tool_outputs") or {}).get("budget_summary") or {}
    sidecar_today = ((response.get("sidecar") or {}).get("ui") or {}).get("today") or {}
    expected_remaining = budget_summary.get("predicted_remaining_kcal_after")
    if expected_remaining is None:
        expected_remaining = ((trace.get("sidecar_output") or {}).get("overshoot") or {}).get("predicted_remaining_kcal_after")
    if expected_remaining is None:
        expected_remaining = ((trace.get("sidecar_output") or {}).get("ui") or {}).get("today", {}).get("remaining_kcal")
    if expected_remaining is None:
        expected_remaining = today.get("remaining_kcal")
    expected_remaining = int(expected_remaining or 0)
    return {
        "reply_remaining_matches_predicted": _contains_int(response.get("assistant_message", ""), expected_remaining),
        "sidecar_remaining_matches_predicted": int(sidecar_today.get("remaining_kcal") or 0) == expected_remaining,
        "today_remaining_matches_predicted": int(today.get("remaining_kcal") or 0) == expected_remaining,
        "response_sidecar_today_budget_sync": _contains_int(response.get("assistant_message", ""), expected_remaining)
        and int(sidecar_today.get("remaining_kcal") or 0) == expected_remaining
        and int(today.get("remaining_kcal") or 0) == expected_remaining,
    }


def _trace_round_1(trace: dict[str, Any]) -> dict[str, Any]:
    rounds = trace.get("manager_rounds") or []
    if isinstance(rounds, list) and rounds:
        first = rounds[0] or {}
        if isinstance(first, dict):
            return dict(first.get("decision") or {})
    return {}


def _trace_final_decision(trace: dict[str, Any]) -> dict[str, Any]:
    return dict(trace.get("manager_final_decision") or {})


def _macro_surface_checks(today: dict[str, Any], response: dict[str, Any], trace: dict[str, Any]) -> dict[str, bool]:
    sidecar_macro = ((response.get("sidecar") or {}).get("macro") or {})
    show_macro = bool(today.get("show_macro"))
    assistant_message = response.get("assistant_message", "")
    mentions_macro = _contains_any(assistant_message, ["protein", "carb", "fat", "蛋白", "碳水", "脂肪"])
    return {
        "today_macro_fields_present": all(key in today for key in ("consumed_protein", "consumed_carbs", "consumed_fat", "show_macro")),
        "chat_macro_visibility_contract": show_macro or not mentions_macro,
        "macro_trace_visible": bool(sidecar_macro),
        "macro_contract_matrix_visible": bool((trace.get("tool_outputs") or {}).get("macro_summary") or sidecar_macro),
    }


def _base_case_report(
    *,
    case_id: str,
    user_id: str,
    request_ids: list[str],
    assistant_messages: list[str],
    today_snapshot: dict[str, Any],
    trace_refs: list[str],
    checks: dict[str, bool],
    blocking_checks: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blocking_failed = [name for name in blocking_checks if not checks.get(name, False)]
    report = {
        "case_id": case_id,
        "user_id": user_id,
        "request_ids": request_ids,
        "assistant_messages": assistant_messages,
        "today_snapshot": today_snapshot,
        "trace_refs": trace_refs,
        "checks": checks,
        "blocking": blocking_checks,
        "passed": not blocking_failed,
        "blocking_failed": blocking_failed,
        "extra": extra or {},
    }
    corruption = find_text_corruption(report)
    report["checks"]["text_integrity"] = not corruption
    if corruption:
        report["blocking_failed"].append("text_integrity")
        report["passed"] = False
        report["extra"]["text_integrity_findings"] = corruption
    return report


def _run_fr001(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("founder-fr001")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    result = _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": "喝了一杯抹茶燕麥奶無糖"})
    trace = _trace(base_url, result)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    evidence = (trace.get("tool_outputs") or {}).get("evidence_summary") or {}
    latency = trace.get("latency_tracking") or {}
    checks = {
        **_same_turn_sync_checks(response=result, trace=trace, today=today),
        "trace_roundtrip": trace.get("request_id") == result["audit"]["request_id"],
        "latency_trace_present": int(latency.get("total_duration_ms") or 0) > 0,
        "provenance_visible": "eligibility" in evidence,
        "no_high_confidence_component_hallucination": not (
            str(evidence.get("eligibility") or "") == "unusable"
            and _contains_any(result.get("assistant_message", ""), ["抹茶粉 40 kcal", "matcha powder 40"])
        ),
    }
    return _base_case_report(
        case_id="FR-001",
        user_id=user_id,
        request_ids=[result["audit"]["request_id"]],
        assistant_messages=[result["assistant_message"]],
        today_snapshot=today,
        trace_refs=[result["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=[
            "reply_remaining_matches_predicted",
            "sidecar_remaining_matches_predicted",
            "today_remaining_matches_predicted",
            "response_sidecar_today_budget_sync",
            "trace_roundtrip",
            "latency_trace_present",
            "provenance_visible",
            "no_high_confidence_component_hallucination",
        ],
        extra={"latency_ms": latency.get("total_duration_ms"), "eligibility": evidence.get("eligibility")},
    )


def _run_fr002(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("founder-fr002")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    result = _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": "然後他晚餐吃蒸餃"})
    trace = _trace(base_url, result)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    checks = {
        "no_premature_commit": result["state_delta"]["canonical_commit"] is False,
        "asks_count_or_gives_range": _contains_any(result["assistant_message"], ["幾顆", "多少顆", "-", "到"]),
        "not_high_confidence_component_split": not _contains_any(result["assistant_message"], ["蒸餃皮 200", "餡料 180"]),
    }
    return _base_case_report(
        case_id="FR-002",
        user_id=user_id,
        request_ids=[result["audit"]["request_id"]],
        assistant_messages=[result["assistant_message"]],
        today_snapshot=today,
        trace_refs=[result["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=["no_premature_commit", "asks_count_or_gives_range", "not_high_confidence_component_split"],
        extra={"final_action": _trace_final_decision(trace).get("final_action")},
    )


def _run_fr003(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("founder-fr003")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    first = _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": "然後他晚餐吃蒸餃"})
    second = _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": "喔我剛剛的蒸餃吃了12顆喔"})
    trace = _trace(base_url, second)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    md1 = _trace_round_1(trace)
    checks = {
        "attached_to_prior_meal": _contains_any(json.dumps(md1.get("target_attachment") or {}, ensure_ascii=False), ["蒸餃"]),
        "owned_lane_not_new_intake": str(md1.get("pending_followup_resolution_mode") or "").lower() in {"resolve_existing_followup", "resolved"} or str(md1.get("clarify_posture") or "") == "item_correction",
        "same_turn_sync": _same_turn_sync_checks(response=second, trace=trace, today=today)["response_sidecar_today_budget_sync"],
    }
    return _base_case_report(
        case_id="FR-003",
        user_id=user_id,
        request_ids=[first["audit"]["request_id"], second["audit"]["request_id"]],
        assistant_messages=[first["assistant_message"], second["assistant_message"]],
        today_snapshot=today,
        trace_refs=[first["audit"]["admin_trace_url"], second["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=["attached_to_prior_meal", "owned_lane_not_new_intake", "same_turn_sync"],
    )


def _run_fr004(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("founder-fr004")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    result = _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": "我消夜還吃了一個大麥克"})
    trace = _trace(base_url, result)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    evidence = ((trace.get("tool_outputs") or {}).get("evidence_summary") or {})
    nutrition_payload = ((trace.get("tool_outputs") or {}).get("nutrition_payload") or {})
    trace_contract = dict(nutrition_payload.get("trace_contract") or {})
    grounding_summary = dict(trace_contract.get("grounding_summary") or {})
    why_not_exact = list(evidence.get("why_not_exact") or trace_contract.get("why_not_exact") or [])
    exact_like_reply = not _contains_any(result.get("assistant_message", ""), ["約", "rough", "估", "大概", "可能", "range"])
    checks = {
        "provenance_visible": "eligibility" in evidence and bool(why_not_exact),
        "retrieval_metadata_visible": "search_attempt_count" in evidence and ("db_hit_type" in evidence or "family_rule" in evidence),
        "unusable_evidence_not_presented_as_exact": not (
            str(evidence.get("eligibility") or "") == "unusable" and exact_like_reply
        ),
        "same_turn_sync": _same_turn_sync_checks(response=result, trace=trace, today=today)["response_sidecar_today_budget_sync"],
    }
    return _base_case_report(
        case_id="FR-004",
        user_id=user_id,
        request_ids=[result["audit"]["request_id"]],
        assistant_messages=[result["assistant_message"]],
        today_snapshot=today,
        trace_refs=[result["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=["provenance_visible", "retrieval_metadata_visible", "unusable_evidence_not_presented_as_exact", "same_turn_sync"],
        extra={
            "eligibility": evidence.get("eligibility"),
            "why_not_exact": why_not_exact,
            "search_attempt_count": evidence.get("search_attempt_count"),
            "source_type": grounding_summary.get("source_type") or grounding_summary.get("top_source_type") or trace_contract.get("source_type"),
            "identity_confidence": grounding_summary.get("identity_confidence") or trace_contract.get("identity_confidence"),
        },
    )


def _run_fr005(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("founder-fr005")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    result = _post_json(base_url, "/v2/estimate", {"user_id": user_id, "local_date": local_date, "allow_search": False, "text": "我剛吃了一碗滷肉飯和一杯無糖豆漿"})
    trace = _trace(base_url, result)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    checks = {
        **_macro_surface_checks(today, result, trace),
        **_same_turn_sync_checks(response=result, trace=trace, today=today),
    }
    return _base_case_report(
        case_id="FR-005",
        user_id=user_id,
        request_ids=[result["audit"]["request_id"]],
        assistant_messages=[result["assistant_message"]],
        today_snapshot=today,
        trace_refs=[result["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=[
            "today_macro_fields_present",
            "chat_macro_visibility_contract",
            "macro_trace_visible",
            "macro_contract_matrix_visible",
            "response_sidecar_today_budget_sync",
        ],
    )


def _build_report(
    base_url: str,
    local_date: str,
    cases: list[dict[str, Any]],
    *,
    expected_total_cases: int,
    run_mode: str = "full",
    timed_out: bool = False,
    interrupted: bool = False,
) -> dict[str, Any]:
    failed = [case["case_id"] for case in cases if not case["passed"]]
    execution_complete = len(cases) == expected_total_cases
    report = {
        "base_url": base_url,
        "local_date": local_date,
        "execution_complete": execution_complete,
        "summary": {
            "total_cases": len(cases),
            "expected_total_cases": expected_total_cases,
            "blocking_failed": len(failed),
            "failed_cases": failed,
            "founder_gate": "pass" if execution_complete and not failed else "fail",
        },
        "cases": cases,
    }
    return apply_runner_timeout_contract(
        report,
        expected_total_cases=expected_total_cases,
        completed_cases=len(cases),
        run_mode=run_mode,
        timed_out=timed_out,
        interrupted=interrupted,
        pass_fields=("founder_gate",),
    )


def _all_case_runners() -> dict[str, Any]:
    return {
        "FR-001": _run_fr001,
        "FR-002": _run_fr002,
        "FR-003": _run_fr003,
        "FR-004": _run_fr004,
        "FR-005": _run_fr005,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run V2 founder realism suite.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--local-date", default=datetime.now().date().isoformat())
    parser.add_argument("--case-id", action="append", default=None, help="Run only selected founder realism case id(s).")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"founder_realism_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    runners = _all_case_runners()
    selected_ids = list(runners.keys()) if not args.case_id else [case_id for case_id in args.case_id if case_id in runners]
    if args.case_id and len(selected_ids) != len(args.case_id):
        unknown = [case_id for case_id in args.case_id if case_id not in runners]
        raise SystemExit(f"unknown founder realism case id(s): {', '.join(unknown)}")
    run_mode = "shard" if args.case_id else "full"

    cases: list[dict[str, Any]] = []
    expected_total_cases = len(selected_ids)
    for case_id in selected_ids:
        case = runners[case_id](args.base_url, args.local_date)
        cases.append(case)
        partial = _build_report(args.base_url, args.local_date, cases, expected_total_cases=expected_total_cases, run_mode=run_mode)
        out.write_text(json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"case_id": case_id, "passed": case["passed"]}, ensure_ascii=False))

    report = _build_report(args.base_url, args.local_date, cases, expected_total_cases=expected_total_cases, run_mode=run_mode)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"founder_gate": report["summary"]["founder_gate"], "blocking_failed": report["summary"]["blocking_failed"], "out": str(out)}, ensure_ascii=False))
    return 0 if report["summary"]["founder_gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
