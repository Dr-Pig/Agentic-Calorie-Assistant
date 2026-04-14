"""Runner for the Golden Lane Set V1.
Enforces file-backed input to prevent PowerShell encoding corruption.
"""

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

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.providers.builderspace_adapter import BuilderSpaceAdapter
from app.schemas import EstimateRequest
from app.usecases.text_meal import run_text_meal_canary
from scripts.audit_io_guard import enforce_file_backed_audit_input, load_json_audit_fixture


def _extract_policy_evidence(payload: Any) -> tuple[str | None, str | None]:
    trace_contract = payload.trace_contract or {}
    policy = trace_contract.get("followup_policy_decision")
    route = trace_contract.get("route_family")
    if policy or route:
        return policy, route

    payload_action = str(getattr(payload, "action_taken", "") or "")
    payload_follow_up = bool(getattr(payload, "follow_up_needed", False))
    payload_kcal = int(getattr(payload, "estimated_kcal", 0) or 0)
    if payload_action == "clarify_before_estimate":
        return "clarify_before_estimate", route
    if payload_kcal > 0 and payload_action in {"direct_answer", "answer_with_uncertainty"}:
        return "estimate_ok", route

    for trace in payload.llm_traces or []:
        if trace.get("stage") == "decision_pass":
            parsed = trace.get("parsed_object") or {}
            decision_next_action = parsed.get("next_action")
            if decision_next_action == "run_clarify":
                return "clarify_before_estimate", route
            if decision_next_action == "run_nutrition_resolution":
                return "estimate_ok", route
        if trace.get("stage", "").startswith("nutrition_resolution_pass"):
            parsed = trace.get("parsed_object") or {}
            action_taken = str(parsed.get("action_taken") or "")
            kcal = int(parsed.get("kcal_most_likely") or parsed.get("estimated_kcal") or 0)
            resolution_mode = str(parsed.get("resolution_mode") or "")
            if action_taken == "clarify_before_estimate" or resolution_mode == "cannot_estimate_yet":
                return "clarify_before_estimate", route
            if kcal > 0 and action_taken in {"direct_answer", "answer_with_uncertainty"}:
                return "estimate_ok", route
        if trace.get("stage") == "final_response_pass":
            parsed = trace.get("parsed_object") or {}
            if parsed.get("asked_follow_up") is True:
                continue
    return policy, route


async def _run_golden_case(case: dict[str, Any], provider: BuilderSpaceAdapter) -> dict[str, Any]:
    request = EstimateRequest(text=case["input_text"], allow_search=False)
    request_id = f"golden-{case['id']}-{uuid.uuid4().hex[:6]}"

    payload = await run_text_meal_canary(
        request,
        provider=provider,
        request_id=request_id,
    )

    policy, route = _extract_policy_evidence(payload)

    is_ask_first = policy in {"clarify_before_estimate", "clarify_policy_unresolved"}
    is_estimate_ok = not is_ask_first

    expected_followup = case.get("should_follow_up")
    if expected_followup is True:
        match = is_ask_first
    elif expected_followup is False:
        match = is_estimate_ok
    else:
        match = None

    return {
        "id": case["id"],
        "request_id": request_id,
        "input": case["input_text"],
        "expected_clarify_first": expected_followup,
        "actual_policy": policy,
        "actual_route": route,
        "match": match,
        "raw_kcal": payload.estimated_kcal,
        "trace_contract": payload.trace_contract,
        "llm_traces": payload.llm_traces,
        "payload": payload.model_dump(mode="json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden Benchmark Runner (file-backed only).")
    parser.add_argument("--fixture", default=None, help="Path to Golden cases JSON.")
    args = parser.parse_args()

    enforce_file_backed_audit_input(audit_name="founder_golden_audit")

    fixture_path = (
        Path(args.fixture)
        if args.fixture
        else ROOT / "docs" / "quality" / "benchmarks" / "founder_fit_golden_v1.json"
    )

    if not fixture_path.exists():
        print(f"Fixture not found: {fixture_path}", file=sys.stderr)
        return 1

    cases = load_json_audit_fixture(path=fixture_path, audit_name="founder_golden_audit")

    adapter = BuilderSpaceAdapter()
    if not adapter.readiness().get("configured"):
        print("ERROR: BuilderSpace is not configured. Set AI_BUILDER_TOKEN.", file=sys.stderr)
        return 1

    print(f"Running Golden Benchmark V1 against {len(cases)} cases...")
    print(f"Provider Configured: {adapter.readiness().get('configured')}")
    print("Execution Method: File Backed (Safe)")

    async def _run_all() -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for case in cases:
            res = await _run_golden_case(case, provider=adapter)
            results.append(res)
            status = "PASS" if res["match"] else "FAIL"
            print(f"  {status} {res['id']}: {res['input']}")
            print(
                f"     Expected ask_first={res['expected_clarify_first']}, Got policy={res['actual_policy']}"
            )
        return results

    results = asyncio.run(_run_all())

    now_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = ROOT / ".logs" / f"founder_golden_audit_{now_tag}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "wave_id": f"golden_v1_{now_tag}",
        "evidence_source": "File-Backed",
        "cases": results,
    }
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved report to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
