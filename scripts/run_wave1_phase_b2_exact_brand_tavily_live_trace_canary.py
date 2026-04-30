from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.exact_brand_web_canary import run_exact_brand_web_canary

DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
DEFAULT_CASE_IDS = ("starbucks_latte_positive", "starbucks_latte_sibling_negative")

_CASES: dict[str, dict[str, str]] = {
    "starbucks_latte_positive": {
        "raw_user_input": "我喝了星巴克大杯那堤",
        "web_query": "星巴克大杯那堤",
        "case_kind": "exact_brand_positive",
    },
    "starbucks_latte_sibling_negative": {
        "raw_user_input": "我喝了星巴克大杯那堤",
        "web_query": "星巴克大杯摩卡",
        "case_kind": "sibling_wrong_variant_negative",
    },
}


def build_missing_token_report(*, case_ids: tuple[str, ...]) -> dict[str, Any]:
    return {
        "artifact_type": "b2_exact_brand_tavily_live_trace_canary",
        "created_at": _utc_stamp(),
        "provider_mode": "not_invoked",
        "live_invoked": False,
        "failure_family": "missing_tavily_api_key",
        "readiness_claimed": False,
        "trace_only": True,
        "case_ids": list(case_ids),
        "cases": [],
    }


async def run_tavily_live_trace_canary(
    *,
    case_ids: tuple[str, ...],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    search_port: Any | None = None,
    extract_port: Any | None = None,
) -> Path:
    if not os.getenv("TAVILY_API_KEY"):
        return _write_report(output_dir, build_missing_token_report(case_ids=case_ids))

    active_search_port = search_port or _tavily_search_port()
    active_extract_port = extract_port or _tavily_extract_port()
    cases: list[dict[str, Any]] = []
    for case_id in case_ids:
        case = _case(case_id)
        outcome = await run_exact_brand_web_canary(
            raw_user_input=case["raw_user_input"],
            contextualized_query=case["web_query"],
            search_port=active_search_port,
            extract_port=active_extract_port,
            allow_search=True,
            exact_db_hit_present=False,
        )
        cases.append(
            {
                "case_id": case_id,
                "case_kind": case["case_kind"],
                "raw_user_input": case["raw_user_input"],
                "web_query": case["web_query"],
                "trace": _json_safe(outcome.trace),
                "product_decision_required": _product_decision_required(outcome.trace),
            }
        )

    report = {
        "artifact_type": "b2_exact_brand_tavily_live_trace_canary",
        "created_at": _utc_stamp(),
        "provider_mode": "live",
        "live_invoked": True,
        "readiness_claimed": False,
        "trace_only": True,
        "case_ids": list(case_ids),
        "cases": cases,
    }
    return _write_report(output_dir, report)


def _case(case_id: str) -> dict[str, str]:
    if case_id not in _CASES:
        supported = ", ".join(sorted(_CASES))
        raise ValueError(f"Unsupported Tavily exact-brand canary case: {case_id}. Supported: {supported}")
    return dict(_CASES[case_id])


def _tavily_search_port() -> Any:
    from app.nutrition.infrastructure.web_search.tavily_search_port import TavilySearchPort

    return TavilySearchPort()


def _tavily_extract_port() -> Any:
    from app.nutrition.infrastructure.web_search.tavily_extract_port import TavilyExtractPort

    return TavilyExtractPort()


def _product_decision_required(trace: dict[str, Any]) -> bool:
    if trace.get("failure_reason") != "selected_extract_policy_blocked":
        return False
    for candidate in trace.get("candidate_traces", []):
        if not isinstance(candidate, dict):
            continue
        if candidate.get("rejected_risk") is None and str(candidate.get("source_url") or ""):
            return True
    return False


def _write_report(output_dir: Path, report: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"wave1_phase_b2_exact_brand_tavily_live_trace_canary_{_utc_stamp()}.json"
    path.write_text(json.dumps(_json_safe(report), ensure_ascii=False, indent=2), encoding="utf-8")
    latest = output_dir / "wave1_phase_b2_exact_brand_tavily_live_trace_canary.json"
    latest.write_text(json.dumps(_json_safe(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


async def _main_async(args: argparse.Namespace) -> int:
    path = await run_tavily_live_trace_canary(
        case_ids=tuple(args.cases),
        output_dir=Path(args.output_dir),
    )
    print(path)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run B2 exact-brand Tavily live trace-only canary.")
    parser.add_argument("--cases", nargs="+", default=list(DEFAULT_CASE_IDS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
