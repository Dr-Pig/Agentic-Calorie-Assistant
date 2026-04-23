from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.text_integrity import corruption_summary, find_text_corruption
from scripts.runner_timeout_contract import apply_runner_timeout_contract
from scripts.run_v2_benchmark_shadow_eval import build_normalized_registry, build_shadow_report
from scripts.run_v2_bundle2_live_eval import (
    DEFAULT_BASE_URL,
    _body_plan,
    _contains_any,
    _fresh_user,
    _get_json,
    _onboarding_payload,
    _post_json,
    _same_turn_sync_checks,
    _trace,
    _trace_final_decision,
)

OUTPUT_DIR = ROOT / "runtime" / "evals" / "v2_benchmark_regression"


def _today(base_url: str, *, user_id: str, local_date: str) -> dict[str, Any]:
    return _get_json(base_url, "/today/current-budget", {"user_id": user_id, "local_date": local_date})


def _seed_onboarding(base_url: str, *, user_id: str, local_date: str) -> dict[str, Any]:
    return _post_json(
        base_url,
        "/v2/estimate",
        {
            "user_id": user_id,
            "local_date": local_date,
            "onboarding": _onboarding_payload(),
        },
    )


def _apply_text_integrity(case: dict[str, Any]) -> dict[str, Any]:
    findings = find_text_corruption(
        {
            "assistant_messages": case.get("assistant_messages"),
            "today_snapshot": case.get("today_snapshot"),
            "extra": case.get("extra"),
        }
    )
    checks = dict(case.get("checks") or {})
    checks["text_integrity"] = not findings
    case["checks"] = checks
    case["passed"] = all(checks.values())
    if findings:
        case["error"] = {"text_integrity_findings": corruption_summary(findings)}
    return case


def _case_report(
    *,
    case: dict[str, Any],
    user_id: str,
    request_ids: list[str],
    assistant_messages: list[str],
    today_snapshot: dict[str, Any],
    trace_refs: list[str],
    checks: dict[str, bool],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case["source_case_id"],
        "title": case.get("title"),
        "source_suite": case.get("source_suite"),
        "user_id": user_id,
        "request_ids": request_ids,
        "assistant_messages": assistant_messages,
        "today_snapshot": today_snapshot,
        "body_plan_snapshot": None,
        "trace_refs": trace_refs,
        "checks": checks,
        "passed": all(checks.values()),
        "extra": extra or {},
    }


def _retrieval_honesty_checks(*, response: dict[str, Any], trace: dict[str, Any], evidence: dict[str, Any]) -> tuple[dict[str, bool], dict[str, Any]]:
    nutrition_payload = ((trace.get("tool_outputs") or {}).get("nutrition_payload") or {})
    trace_contract = dict(nutrition_payload.get("trace_contract") or {})
    grounding_summary = dict(trace_contract.get("grounding_summary") or {})
    raw_why_not_exact = evidence.get("why_not_exact") or trace_contract.get("why_not_exact") or []
    if isinstance(raw_why_not_exact, str):
        why_not_exact = [raw_why_not_exact] if raw_why_not_exact.strip() else []
    else:
        why_not_exact = [str(item) for item in raw_why_not_exact if str(item).strip()]
    source_type = grounding_summary.get("source_type") or grounding_summary.get("top_source_type") or trace_contract.get("source_type")
    identity_confidence = grounding_summary.get("identity_confidence") or trace_contract.get("identity_confidence")
    eligibility = str(evidence.get("eligibility") or "")
    exact_count = int(evidence.get("exact_count") or 0)
    search_attempt_count = int(evidence.get("search_attempt_count") or 0)
    exact_like_reply = not _contains_any(
        str(response.get("assistant_message") or ""),
        ["約", "大概", "rough", "around", "可能", "range", "between"],
    )
    checks = {
        "retrieval_metadata_visible": "eligibility" in evidence
        and "exact_count" in evidence
        and "search_attempt_count" in evidence
        and (bool(why_not_exact) or eligibility == "exact"),
        "unusable_evidence_not_exact_like_finalize": not (
            eligibility == "unusable" and exact_count == 0 and exact_like_reply
        ),
    }
    extra = {
        "eligibility": eligibility,
        "exact_count": exact_count,
        "search_attempt_count": search_attempt_count,
        "source_type": source_type,
        "identity_confidence": identity_confidence,
        "why_not_exact": why_not_exact,
    }
    return checks, extra


def _run_exact_case(case: dict[str, Any], *, base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user(f"benchmark-{case['source_case_id']}")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    response = _post_json(
        base_url,
        "/v2/estimate",
        {
            "user_id": user_id,
            "local_date": local_date,
            "allow_search": True,
            "text": case["input_text"],
        },
    )
    trace = _trace(base_url, response)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    evidence = ((response.get("sidecar") or {}).get("evidence") or {})
    retrieval_checks, retrieval_extra = _retrieval_honesty_checks(response=response, trace=trace, evidence=evidence)
    checks = {
        "request_id": bool((response.get("audit") or {}).get("request_id")),
        "trace_roundtrip": trace.get("request_id") == (response.get("audit") or {}).get("request_id"),
        "canonical_commit": bool((response.get("state_delta") or {}).get("canonical_commit")),
        "today_has_meal": int(today.get("active_meal_count") or 0) == 1 and int(today.get("consumed_kcal") or 0) > 0,
        "no_followup": _trace_final_decision(trace).get("final_action") != "ask_followup",
        "evidence_exact": str(evidence.get("eligibility") or "") == "exact"
        and int(evidence.get("exact_count") or 0) >= 1,
        "same_turn_budget_sync": _same_turn_sync_checks(response=response, trace=trace, today=today)["same_turn_budget_sync"],
        **retrieval_checks,
    }
    return _case_report(
        case=case,
        user_id=user_id,
        request_ids=[(response.get("audit") or {}).get("request_id")],
        assistant_messages=[str(response.get("assistant_message") or "")],
        today_snapshot=today,
        trace_refs=[str((response.get("audit") or {}).get("admin_trace_url") or "")],
        checks=checks,
        extra={
            "source_domain": case.get("source_domain"),
            "evidence_topology": case.get("evidence_topology"),
            **retrieval_extra,
        },
    )


def _run_replay_case(case: dict[str, Any], *, base_url: str, local_date: str) -> dict[str, Any]:
    user_id = _fresh_user(f"benchmark-{case['source_case_id']}")
    _seed_onboarding(base_url, user_id=user_id, local_date=local_date)
    turn1 = _post_json(
        base_url,
        "/v2/estimate",
        {
            "user_id": user_id,
            "local_date": local_date,
            "allow_search": False,
            "text": case["input_text"].split(" || ")[0],
        },
    )
    trace1 = _trace(base_url, turn1)
    turn2 = _post_json(
        base_url,
        "/v2/estimate",
        {
            "user_id": user_id,
            "local_date": local_date,
            "allow_search": False,
            "text": case["input_text"].split(" || ")[1],
        },
    )
    trace2 = _trace(base_url, turn2)
    today = _today(base_url, user_id=user_id, local_date=local_date)
    checks = {
        "turn1_request_id": bool((turn1.get("audit") or {}).get("request_id")),
        "turn2_request_id": bool((turn2.get("audit") or {}).get("request_id")),
        "turn1_no_commit": not bool((turn1.get("state_delta") or {}).get("canonical_commit")),
        "turn2_commit": bool((turn2.get("state_delta") or {}).get("canonical_commit")),
        "same_thread_attachment": str((((today.get("meals") or [{}])[0]).get("source_request_id") or ""))
        == str((turn2.get("audit") or {}).get("request_id") or ""),
        "turn2_finalized": _trace_final_decision(trace2).get("final_action") in {"commit", "overshoot_note"},
        "same_turn_budget_sync": _same_turn_sync_checks(response=turn2, trace=trace2, today=today)["same_turn_budget_sync"],
    }
    return _case_report(
        case=case,
        user_id=user_id,
        request_ids=[(turn1.get("audit") or {}).get("request_id"), (turn2.get("audit") or {}).get("request_id")],
        assistant_messages=[str(turn1.get("assistant_message") or ""), str(turn2.get("assistant_message") or "")],
        today_snapshot=today,
        trace_refs=[
            str((turn1.get("audit") or {}).get("admin_trace_url") or ""),
            str((turn2.get("audit") or {}).get("admin_trace_url") or ""),
        ],
        checks=checks,
        extra={
            "turn1_final_action": _trace_final_decision(trace1).get("final_action"),
            "turn2_final_action": _trace_final_decision(trace2).get("final_action"),
            "evidence_topology": case.get("evidence_topology"),
        },
    )


def _run_case(case: dict[str, Any], *, base_url: str, local_date: str) -> dict[str, Any]:
    topology = str(case.get("evidence_topology") or "")
    if topology.startswith("replay_"):
        return _run_replay_case(case, base_url=base_url, local_date=local_date)
    return _run_exact_case(case, base_url=base_url, local_date=local_date)


def _build_report(
    *,
    base_url: str,
    local_date: str,
    selected_cases: list[dict[str, Any]],
    results: list[dict[str, Any]],
    run_mode: str = "full",
    timed_out: bool = False,
    interrupted: bool = False,
) -> dict[str, Any]:
    execution_complete = len(results) == len(selected_cases)
    report = {
        "base_url": base_url,
        "local_date": local_date,
        "execution_complete": execution_complete,
        "summary": {
            "total_cases": len(results),
            "expected_total_cases": len(selected_cases),
            "passed_cases": sum(1 for result in results if result.get("passed")),
            "failed_cases": [result["case_id"] for result in results if not result.get("passed")],
            "runner_case_status": "pass" if execution_complete and all(result.get("passed") for result in results) else "fail",
        },
        "selected_cases": [
            {
                "source_case_id": case["source_case_id"],
                "source_suite": case["source_suite"],
                "source_domain": case.get("source_domain"),
                "case_family": case.get("case_family"),
                "evidence_topology": case.get("evidence_topology"),
                "promotion_reason": case.get("promotion_reason"),
            }
            for case in selected_cases
        ],
        "cases": results,
    }
    return apply_runner_timeout_contract(
        report,
        expected_total_cases=len(selected_cases),
        completed_cases=len(results),
        run_mode=run_mode,
        timed_out=timed_out,
        interrupted=interrupted,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run promoted blocking benchmark regression cases.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--local-date", default=datetime.now().date().isoformat())
    parser.add_argument("--case-id", action="append", default=None, help="Run only the selected promoted blocking case id(s).")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    registry = build_normalized_registry()
    shadow_report = build_shadow_report(registry)
    selected_cases = list(shadow_report.get("blocking_registry") or [])
    if args.case_id:
        wanted = {str(case_id) for case_id in args.case_id}
        selected_cases = [case for case in selected_cases if str(case.get("source_case_id")) in wanted]
        if not selected_cases:
            raise SystemExit(f"unknown blocking case id(s): {', '.join(args.case_id)}")
    run_mode = "shard" if args.case_id else "full"

    results: list[dict[str, Any]] = []
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_path = OUTPUT_DIR / f"benchmark_blocking_eval_{stamp}.json"
    for case in selected_cases:
        try:
            result = _run_case(case, base_url=args.base_url, local_date=args.local_date)
        except Exception as exc:  # noqa: BLE001
            result = {
                "case_id": case["source_case_id"],
                "title": case.get("title"),
                "source_suite": case.get("source_suite"),
                "user_id": None,
                "request_ids": [],
                "assistant_messages": [],
                "today_snapshot": {},
                "body_plan_snapshot": None,
                "trace_refs": [],
                "checks": {"runner_ok": False},
                "passed": False,
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "extra": {"promotion_reason": case.get("promotion_reason")},
            }
        results.append(_apply_text_integrity(result))
        partial_report = _build_report(
            base_url=args.base_url,
            local_date=args.local_date,
            selected_cases=selected_cases,
            results=results,
            run_mode=run_mode,
        )
        output_path.write_text(json.dumps(partial_report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{case['source_case_id']}: {'PASS' if results[-1]['passed'] else 'FAIL'}")

    report = _build_report(base_url=args.base_url, local_date=args.local_date, selected_cases=selected_cases, results=results, run_mode=run_mode)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"saved: {output_path}")
    return 0 if report["summary"]["runner_case_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
