from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.text_integrity import corruption_summary, find_text_corruption
from scripts.eval_bootstrap import build_bootstrap_checklist, build_bundle_verdict
from scripts.live_eval_readiness import (
    DEFAULT_LOCAL_LIVE_BASE_URL,
    PHASE_C_LIVE_BLOCKING_CHECKS,
    build_live_preflight_report,
    build_phase_c_live_readiness,
    fetch_server_ping,
    summarize_phase_c_gate_status,
)
from scripts.runner_timeout_contract import apply_runner_timeout_contract


DEFAULT_BASE_URL = DEFAULT_LOCAL_LIVE_BASE_URL
OUTPUT_DIR = ROOT / "runtime" / "evals" / "v2_bundle2_live"


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


def _onboarding_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "sex": "female",
        "age_years": 25,
        "height_cm": 160,
        "current_weight_kg": 65,
        "goal_type": "lose_weight",
        "weekly_target_rate_kg": 1.5,
        "timezone": "Asia/Taipei",
    }
    payload.update(overrides)
    return payload


def _seed_onboarding(base_url: str, *, user_id: str, local_date: str, **overrides: Any) -> dict[str, Any]:
    return _post_json(
        base_url,
        "/v2/estimate",
        {"user_id": user_id, "local_date": local_date, "onboarding": _onboarding_payload(**overrides)},
    )


def _body_plan(base_url: str, *, user_id: str) -> dict[str, Any]:
    return _get_json(base_url, "/body-plan/active", {"user_id": user_id})


def _trace(base_url: str, response: dict[str, Any]) -> dict[str, Any]:
    return _get_json(base_url, response["audit"]["admin_trace_url"])


def _today(base_url: str, *, user_id: str, local_date: str) -> dict[str, Any]:
    return _get_json(base_url, "/today/current-budget", {"user_id": user_id, "local_date": local_date})


def _trace_round_1(trace: dict[str, Any]) -> dict[str, Any]:
    rounds = trace.get("manager_rounds") or []
    if isinstance(rounds, list) and rounds:
        first = rounds[0] or {}
        if isinstance(first, dict):
            return dict(first.get("decision") or {})
    return {}


def _trace_final_decision(trace: dict[str, Any]) -> dict[str, Any]:
    return dict(trace.get("manager_final_decision") or {})


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = str(text or "").lower()
    return any(needle.lower() in lowered for needle in needles)


def _contains_int(text: str, value: int) -> bool:
    return str(int(value)) in str(text or "")


def _contains_range(text: str) -> bool:
    return bool(re.search(r"\d+\s*[-–~]\s*\d+", str(text or "")))


def _same_turn_sync_checks(*, response: dict[str, Any], trace: dict[str, Any], today: dict[str, Any]) -> dict[str, bool]:
    budget_summary = (trace.get("tool_outputs") or {}).get("budget_summary") or {}
    sidecar_today = (((response.get("sidecar") or {}).get("ui") or {}).get("today") or {})
    predicted_remaining = budget_summary.get("predicted_remaining_kcal_after")
    if predicted_remaining is None:
        predicted_remaining = sidecar_today.get("remaining_kcal")
    if predicted_remaining is None:
        predicted_remaining = today.get("remaining_kcal")
    predicted_remaining = int(predicted_remaining or 0)
    return {
        "reply_remaining_matches_predicted": _contains_int(response.get("assistant_message", ""), predicted_remaining),
        "sidecar_remaining_matches_predicted": int(sidecar_today.get("remaining_kcal") or 0) == predicted_remaining,
        "today_remaining_matches_predicted": int(today.get("remaining_kcal") or 0) == predicted_remaining,
        "same_turn_budget_sync": _contains_int(response.get("assistant_message", ""), predicted_remaining)
        and int(sidecar_today.get("remaining_kcal") or 0) == predicted_remaining
        and int(today.get("remaining_kcal") or 0) == predicted_remaining,
    }


def _macro_visibility_checks(response: dict[str, Any], today: dict[str, Any], trace: dict[str, Any]) -> dict[str, bool]:
    assistant_message = response.get("assistant_message", "")
    mentions_macro = _contains_any(assistant_message, ["protein", "carb", "fat", "蛋白質", "碳水", "脂肪"])
    show_macro = bool(today.get("show_macro"))
    positive_macro_totals = all(int(today.get(key) or 0) > 0 for key in ("consumed_protein", "consumed_carbs", "consumed_fat"))
    evidence = ((trace.get("tool_outputs") or {}).get("evidence_summary") or {})
    high_uncertainty = str(evidence.get("eligibility") or "") in {"generic", "unusable"} and int(evidence.get("exact_count") or 0) == 0
    return {
        "turn1_macro_hidden": not show_macro and not mentions_macro,
        "macro_alignment_contract": (not show_macro) or positive_macro_totals,
        "turn2_macro_totals_positive": positive_macro_totals,
        "macro_uncertainty_visibility": (not show_macro) if high_uncertainty else True,
        "chat_macro_visibility_contract": show_macro or not mentions_macro,
    }


def _overshoot_checks(response: dict[str, Any], today: dict[str, Any], trace: dict[str, Any]) -> dict[str, bool]:
    assistant_message = response.get("assistant_message", "")
    remaining = int(today.get("remaining_kcal") or 0)
    overshoot = abs(min(remaining, 0))
    sidecar_today = (((response.get("sidecar") or {}).get("ui") or {}).get("today") or {})
    return {
        "reply_mentions_over": _contains_any(assistant_message, ["over", "超出", "超標"]),
        "sidecar_overshoot": int(sidecar_today.get("remaining_kcal") or 0) < 0,
        "remaining_negative": remaining < 0,
        "reply_matches_today_remaining": _contains_int(assistant_message, overshoot),
    }


def _corruption_checks(report: dict[str, Any]) -> dict[str, bool]:
    findings = find_text_corruption(report)
    return {"text_integrity": not findings, "text_integrity_findings": corruption_summary(findings) if findings else None}


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
        "blocking_failed": blocking_failed,
        "passed": not blocking_failed,
        "extra": extra or {},
    }
    integrity = _corruption_checks(report)
    report["checks"]["text_integrity"] = integrity["text_integrity"]
    if not integrity["text_integrity"]:
        report["blocking_failed"].append("text_integrity")
        report["passed"] = False
        report["extra"]["text_integrity_findings"] = integrity["text_integrity_findings"]
    return report


def _phase_c_checked_case(
    *,
    checks: dict[str, bool],
    response: dict[str, Any],
    trace: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> tuple[dict[str, bool], dict[str, Any]]:
    phase_c_readiness = build_phase_c_live_readiness(response=response, trace=trace)
    merged_checks = {**checks, **phase_c_readiness["checks"]}
    merged_extra = dict(extra or {})
    merged_extra["phase_c_live_readiness"] = phase_c_readiness["summary"]
    return merged_checks, merged_extra


def _log(base_url: str, *, user_id: str, local_date: str, text: str, allow_search: bool = False) -> dict[str, Any]:
    return _post_json(
        base_url,
        "/v2/estimate",
        {"user_id": user_id, "local_date": local_date, "allow_search": allow_search, "text": text},
    )


def _run_case_c001(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle2-c001")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    turn1 = _log(base_url, user_id=user_id, local_date=local_date, text="我喝了一杯珍珠奶茶")
    trace1 = _trace(base_url, turn1)
    today1 = _today(base_url, user_id=user_id, local_date=local_date)
    turn2 = _log(base_url, user_id=user_id, local_date=local_date, text="半糖大杯")
    trace2 = _trace(base_url, turn2)
    today2 = _today(base_url, user_id=user_id, local_date=local_date)
    checks = {
        "turn1_no_commit": turn1["state_delta"]["canonical_commit"] is False,
        "turn1_has_range": _contains_range(turn1["assistant_message"]) or _contains_any(turn1["assistant_message"], ["約", "大概"]),
        "turn1_asks_detail": _contains_any(turn1["assistant_message"], ["糖", "杯", "大小", "幾分糖"]),
        **_macro_visibility_checks(turn1, today1, trace1),
        "turn2_commit": turn2["state_delta"]["canonical_commit"] is True,
        **{k: v for k, v in _macro_visibility_checks(turn2, today2, trace2).items() if k != "turn1_macro_hidden"},
        **_same_turn_sync_checks(response=turn2, trace=trace2, today=today2),
    }
    checks, extra = _phase_c_checked_case(checks=checks, response=turn2, trace=trace2)
    return _base_case_report(
        case_id="C-001",
        user_id=user_id,
        request_ids=[turn1["audit"]["request_id"], turn2["audit"]["request_id"]],
        assistant_messages=[turn1["assistant_message"], turn2["assistant_message"]],
        today_snapshot=today2,
        trace_refs=[turn1["audit"]["admin_trace_url"], turn2["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=[
            "turn1_no_commit",
            "turn1_has_range",
            "turn1_asks_detail",
            "turn1_macro_hidden",
            "macro_alignment_contract",
            "turn2_macro_totals_positive",
            "chat_macro_visibility_contract",
            "same_turn_budget_sync",
            *PHASE_C_LIVE_BLOCKING_CHECKS,
        ],
        extra=extra,
    )


def _run_case_c002(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle2-c002")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    response = _log(base_url, user_id=user_id, local_date=local_date, text="我喝了一杯全糖大杯珍珠奶茶")
    trace = _trace(base_url, response)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    checks = {
        "committed": response["state_delta"]["canonical_commit"] is True,
        "no_followup": _trace_final_decision(trace).get("final_action") != "ask_followup",
        **_macro_visibility_checks(response, today, trace),
        **_same_turn_sync_checks(response=response, trace=trace, today=today),
    }
    checks, extra = _phase_c_checked_case(checks=checks, response=response, trace=trace)
    return _base_case_report(
        case_id="C-002",
        user_id=user_id,
        request_ids=[response["audit"]["request_id"]],
        assistant_messages=[response["assistant_message"]],
        today_snapshot=today,
        trace_refs=[response["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=["committed", "no_followup", "same_turn_budget_sync", *PHASE_C_LIVE_BLOCKING_CHECKS],
        extra=extra,
    )


def _run_case_d001(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle2-d001")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    turn1 = _log(base_url, user_id=user_id, local_date=local_date, text="我吃了家常菜")
    trace1 = _trace(base_url, turn1)
    today1 = _today(base_url, user_id=user_id, local_date=local_date)
    turn2 = _log(base_url, user_id=user_id, local_date=local_date, text="有青菜、豆腐、滷蛋")
    trace2 = _trace(base_url, turn2)
    today2 = _today(base_url, user_id=user_id, local_date=local_date)
    checks = {
        "turn1_no_commit": turn1["state_delta"]["canonical_commit"] is False,
        "turn1_asks_dish_details": _contains_any(turn1["assistant_message"], ["什麼", "菜色", "內容", "有哪些"]),
        "turn2_commit": turn2["state_delta"]["canonical_commit"] is True,
        **_macro_visibility_checks(turn1, today1, trace1),
        **{k: v for k, v in _macro_visibility_checks(turn2, today2, trace2).items() if k != "turn1_macro_hidden"},
        **_same_turn_sync_checks(response=turn2, trace=trace2, today=today2),
    }
    checks, extra = _phase_c_checked_case(checks=checks, response=turn2, trace=trace2)
    return _base_case_report(
        case_id="D-001",
        user_id=user_id,
        request_ids=[turn1["audit"]["request_id"], turn2["audit"]["request_id"]],
        assistant_messages=[turn1["assistant_message"], turn2["assistant_message"]],
        today_snapshot=today2,
        trace_refs=[turn1["audit"]["admin_trace_url"], turn2["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=[
            "turn1_no_commit",
            "turn1_asks_dish_details",
            "turn2_commit",
            "turn1_macro_hidden",
            "same_turn_budget_sync",
            *PHASE_C_LIVE_BLOCKING_CHECKS,
        ],
        extra=extra,
    )


def _run_case_d002(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle2-d002")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    response = _log(base_url, user_id=user_id, local_date=local_date, text="我吃了家常菜，有青菜、豆腐、滷蛋")
    trace = _trace(base_url, response)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    checks = {
        "committed": response["state_delta"]["canonical_commit"] is True,
        "no_followup": _trace_final_decision(trace).get("final_action") != "ask_followup",
        **_same_turn_sync_checks(response=response, trace=trace, today=today),
    }
    checks, extra = _phase_c_checked_case(checks=checks, response=response, trace=trace)
    return _base_case_report(
        case_id="D-002",
        user_id=user_id,
        request_ids=[response["audit"]["request_id"]],
        assistant_messages=[response["assistant_message"]],
        today_snapshot=today,
        trace_refs=[response["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=["committed", "no_followup", "same_turn_budget_sync", *PHASE_C_LIVE_BLOCKING_CHECKS],
        extra=extra,
    )


def _seed_near_overshoot(base_url: str, *, user_id: str, local_date: str) -> None:
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    _log(base_url, user_id=user_id, local_date=local_date, text="我剛吃了排骨便當和珍珠奶茶")


def _run_case_e001(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle2-e001")
    _seed_near_overshoot(base_url, user_id=user_id, local_date=local_date)
    response = _log(base_url, user_id=user_id, local_date=local_date, text="我剛吃了一個排骨便當")
    trace = _trace(base_url, response)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    checks = {
        **_overshoot_checks(response, today, trace),
        **_macro_visibility_checks(response, today, trace),
        **_same_turn_sync_checks(response=response, trace=trace, today=today),
        "no_rescue_in_same_reply": not _contains_any(response["assistant_message"], ["建議", "rescue", "補救"]),
    }
    checks, extra = _phase_c_checked_case(checks=checks, response=response, trace=trace)
    return _base_case_report(
        case_id="E-001",
        user_id=user_id,
        request_ids=[response["audit"]["request_id"]],
        assistant_messages=[response["assistant_message"]],
        today_snapshot=today,
        trace_refs=[response["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=[
            "reply_mentions_over",
            "sidecar_overshoot",
            "remaining_negative",
            "no_rescue_in_same_reply",
            "same_turn_budget_sync",
            *PHASE_C_LIVE_BLOCKING_CHECKS,
        ],
        extra=extra,
    )


def _run_case_e002(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle2-e002")
    _seed_near_overshoot(base_url, user_id=user_id, local_date=local_date)
    response = _log(base_url, user_id=user_id, local_date=local_date, text="我剛吃了一碗牛肉麵")
    trace = _trace(base_url, response)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    checks = {
        **_overshoot_checks(response, today, trace),
        **_same_turn_sync_checks(response=response, trace=trace, today=today),
    }
    checks, extra = _phase_c_checked_case(checks=checks, response=response, trace=trace)
    return _base_case_report(
        case_id="E-002",
        user_id=user_id,
        request_ids=[response["audit"]["request_id"]],
        assistant_messages=[response["assistant_message"]],
        today_snapshot=today,
        trace_refs=[response["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=[
            "reply_mentions_over",
            "remaining_negative",
            "reply_matches_today_remaining",
            "same_turn_budget_sync",
            *PHASE_C_LIVE_BLOCKING_CHECKS,
        ],
        extra=extra,
    )


def _run_case_e003(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle2-e003")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    response = _log(base_url, user_id=user_id, local_date=local_date, text="我剛吃了一碗牛肉麵")
    trace = _trace(base_url, response)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    checks = {
        "not_overshoot_reply": not _contains_any(response["assistant_message"], ["超出", "超標", "over"]),
        "remaining_not_negative": int(today.get("remaining_kcal") or 0) >= 0,
        **_same_turn_sync_checks(response=response, trace=trace, today=today),
    }
    checks, extra = _phase_c_checked_case(checks=checks, response=response, trace=trace)
    return _base_case_report(
        case_id="E-003",
        user_id=user_id,
        request_ids=[response["audit"]["request_id"]],
        assistant_messages=[response["assistant_message"]],
        today_snapshot=today,
        trace_refs=[response["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=["not_overshoot_reply", "remaining_not_negative", "same_turn_budget_sync", *PHASE_C_LIVE_BLOCKING_CHECKS],
        extra=extra,
    )


def _run_case_k001(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle2-k001")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    setup = _log(base_url, user_id=user_id, local_date=local_date, text="我剛吃了一碗牛肉麵和一杯無糖豆漿")
    correction = _log(base_url, user_id=user_id, local_date=local_date, text="剛才那杯豆漿我記錯了，應該是有糖豆漿，大概 150 kcal")
    trace = _trace(base_url, correction)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    text = json.dumps({"reply": correction["assistant_message"], "today": today, "trace": trace}, ensure_ascii=False)
    checks = {
        "new_meal_version_created": bool(correction["state_delta"].get("new_meal_version_created")),
        "old_version_superseded": bool(correction["state_delta"].get("old_version_superseded")),
        "ledger_updated": bool(correction["state_delta"].get("ledger_updated")),
        "preserved_non_target_items": _contains_any(text, ["牛肉麵"]),
        "corrected_target_present": _contains_any(text, ["豆漿", "150"]),
        "correction_total_not_collapsed_to_target_only": int(today.get("consumed_kcal") or 0) > 150,
        "target_item_replaced_not_appended_duplicate": not _contains_any(text, ["無糖豆漿"]) or _contains_any(text, ["有糖豆漿"]),
        "corrected_total_matches_preserved_plus_target": int(today.get("consumed_kcal") or 0) >= 700,
        "correction_macro_updated": all(int(today.get(key) or 0) > 0 for key in ("consumed_protein", "consumed_carbs", "consumed_fat")),
        **_macro_visibility_checks(correction, today, trace),
        **_same_turn_sync_checks(response=correction, trace=trace, today=today),
    }
    checks, extra = _phase_c_checked_case(checks=checks, response=correction, trace=trace)
    return _base_case_report(
        case_id="K-001",
        user_id=user_id,
        request_ids=[setup["audit"]["request_id"], correction["audit"]["request_id"]],
        assistant_messages=[setup["assistant_message"], correction["assistant_message"]],
        today_snapshot=today,
        trace_refs=[setup["audit"]["admin_trace_url"], correction["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=[
            "new_meal_version_created",
            "old_version_superseded",
            "ledger_updated",
            "preserved_non_target_items",
            "corrected_target_present",
            "correction_total_not_collapsed_to_target_only",
            "target_item_replaced_not_appended_duplicate",
            "corrected_total_matches_preserved_plus_target",
            "correction_macro_updated",
            "same_turn_budget_sync",
            *PHASE_C_LIVE_BLOCKING_CHECKS,
        ],
        extra=extra,
    )


def _run_case_k002(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle2-k002")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    setup = _log(base_url, user_id=user_id, local_date=local_date, text="我剛吃了一碗牛肉麵和一杯無糖豆漿")
    correction = _log(base_url, user_id=user_id, local_date=local_date, text="豆漿我沒喝")
    trace = _trace(base_url, correction)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    text = json.dumps({"reply": correction["assistant_message"], "today": today, "trace": trace}, ensure_ascii=False)
    checks = {
        "same_thread_preserved": int(today.get("active_meal_count") or 0) >= 1,
        "target_item_removed_not_new_meal": _contains_any(text, ["移除", "沒喝", "牛肉麵"]),
        "corrected_total_matches_removed_target_delta": int(today.get("consumed_kcal") or 0) < 680,
        "correction_macro_updated": all(int(today.get(key) or 0) > 0 for key in ("consumed_protein", "consumed_carbs", "consumed_fat")),
        **_same_turn_sync_checks(response=correction, trace=trace, today=today),
    }
    checks, extra = _phase_c_checked_case(checks=checks, response=correction, trace=trace)
    return _base_case_report(
        case_id="K-002",
        user_id=user_id,
        request_ids=[setup["audit"]["request_id"], correction["audit"]["request_id"]],
        assistant_messages=[setup["assistant_message"], correction["assistant_message"]],
        today_snapshot=today,
        trace_refs=[setup["audit"]["admin_trace_url"], correction["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=[
            "same_thread_preserved",
            "target_item_removed_not_new_meal",
            "corrected_total_matches_removed_target_delta",
            "correction_macro_updated",
            "same_turn_budget_sync",
            *PHASE_C_LIVE_BLOCKING_CHECKS,
        ],
        extra=extra,
    )


def _run_case_k003(base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user("bundle2-k003")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    _log(base_url, user_id=user_id, local_date=local_date, text="我剛吃了一碗牛肉麵和一杯無糖豆漿")
    _log(base_url, user_id=user_id, local_date=local_date, text="剛才那杯豆漿我記錯了，應該是有糖豆漿，大概 150 kcal")
    query = _log(base_url, user_id=user_id, local_date=local_date, text="我今天吃了多少？")
    trace = _trace(base_url, query)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    checks = {
        "reply_mentions_current_consumed": _contains_int(query["assistant_message"], int(today.get("consumed_kcal") or 0)),
        **_macro_visibility_checks(query, today, trace),
        **_same_turn_sync_checks(response=query, trace=trace, today=today),
    }
    return _base_case_report(
        case_id="K-003",
        user_id=user_id,
        request_ids=[query["audit"]["request_id"]],
        assistant_messages=[query["assistant_message"]],
        today_snapshot=today,
        trace_refs=[query["audit"]["admin_trace_url"]],
        checks=checks,
        blocking_checks=["reply_mentions_current_consumed", "chat_macro_visibility_contract", "same_turn_budget_sync"],
    )


CASE_RUNNERS = [
    _run_case_c001,
    _run_case_c002,
    _run_case_d001,
    _run_case_d002,
    _run_case_e001,
    _run_case_e002,
    _run_case_e003,
    _run_case_k001,
    _run_case_k002,
    _run_case_k003,
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Bundle 2 live E2E eval cases against /v2/estimate.")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--local-date", default=datetime.now().date().isoformat())
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
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
    output_path = Path(args.output) if args.output else OUTPUT_DIR / f"bundle2_live_eval_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"

    results: list[dict[str, Any]] = []
    for runner in CASE_RUNNERS:
        try:
            result = runner(base_url, args.local_date)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            result = {
                "case_id": runner.__name__.replace("_run_case_", "").upper(),
                "passed": False,
                "checks": {"http_ok": False},
                "error": {"status": exc.code, "body": body},
            }
        except Exception as exc:
            result = {
                "case_id": runner.__name__.replace("_run_case_", "").upper(),
                "passed": False,
                "checks": {"runner_ok": False},
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
        results.append(result)
        print(f"{result['case_id']}: {'PASS' if result['passed'] else 'FAIL'}")

    p0_ids = {"C-001", "D-001", "E-001", "E-002", "K-001"}
    p0_pass = all(result.get("passed") for result in results if result["case_id"] in p0_ids)
    all_cases_pass = all(result.get("passed") for result in results)
    phase_c_gate_status = summarize_phase_c_gate_status(results)
    bootstrap = build_bootstrap_checklist(bundle=2)
    coverage_status = bootstrap["parity_audit"]["coverage_status"]
    founder_status = bootstrap["founder_realism"]["status"]
    runner_case_status = "pass" if all_cases_pass else "fail"
    verdict = build_bundle_verdict(
        runner_case_status=runner_case_status,
        coverage_status=coverage_status,
        founder_realism_status=founder_status,
        checklist=bootstrap,
    )
    summary = {
        "total_cases": len(results),
        "passed_cases": sum(1 for result in results if result.get("passed")),
        "failed_cases": [result["case_id"] for result in results if not result.get("passed")],
        "p0_pass": p0_pass,
        "p0_failed": sum(1 for result in results if result["case_id"] in p0_ids and not result.get("passed")),
        "all_cases_pass": all_cases_pass,
        "live_test_mode": live_preflight["live_test_mode"],
        "server_ping_status": live_preflight["server_ping_status"],
        "phase_c_gate_status": phase_c_gate_status,
        "readiness_claim_scope": live_preflight["readiness_claim_scope"],
        **verdict,
    }
    report = {
        "base_url": base_url,
        "live_test_mode": live_preflight["live_test_mode"],
        "server_ping_status": live_preflight["server_ping_status"],
        "provider_readiness": live_preflight["provider_readiness"],
        "readiness_claim_scope": live_preflight["readiness_claim_scope"],
        "phase_c_gate_status": phase_c_gate_status,
        "live_preflight": live_preflight,
        "local_date": args.local_date,
        "bootstrap_checklist": bootstrap,
        "summary": summary,
        "cases": results,
    }
    report = apply_runner_timeout_contract(
        report,
        expected_total_cases=len(CASE_RUNNERS),
        completed_cases=len(results),
        run_mode="full",
    )
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = report["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"saved: {output_path}")
    return 0 if summary["runner_case_status"] == "pass" and summary["coverage_status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
