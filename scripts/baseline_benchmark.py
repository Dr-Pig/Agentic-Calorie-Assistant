from __future__ import annotations

import asyncio
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from app.providers.builderspace_adapter import BuilderSpaceAdapter
from app.schemas import EstimateRequest
from app.usecases.text_meal import run_text_meal_canary


GOLDEN_CASES = [
    {
        "id": "exact_item_01",
        "label": "exact item",
        "input": "我早餐吃鮪魚肉鬆雙手捲加一個茶葉蛋",
        "trajectory_expectation": {
            "meal_link_action": "create_new_meal",
            "resolution_basis": "exact_item_evidence",
        },
    },
    {
        "id": "luwei_01",
        "label": "luwei provisional",
        "input": "我吃了一碗滷味",
        "trajectory_expectation": {
            "meal_link_action": "create_new_meal",
            "response_mode_hint": "clarify_first",
        },
    },
    {
        "id": "bento_01",
        "label": "bento",
        "input": "我中午吃一個雞腿便當",
        "trajectory_expectation": {
            "meal_link_action": "create_new_meal",
        },
    },
    {
        "id": "ramen_01",
        "label": "ramen calibration",
        "input": "我晚餐吃日式豚骨拉麵",
        "trajectory_expectation": {
            "resolution_basis": "calibrated_component_model",
        },
    },
    {
        "id": "boundary_01",
        "label": "ambiguous boundary",
        "input": "這是早餐",
        "trajectory_expectation": {
            "meal_link_action": "boundary_ambiguous",
        },
    },
]


async def run_case(adapter: BuilderSpaceAdapter, case: dict[str, object]) -> dict[str, object]:
    started = perf_counter()
    payload = await run_text_meal_canary(
        EstimateRequest(
            text=str(case["input"]),
            allow_search=False,
            user_id=f"baseline-{uuid4().hex}",
        ),
        provider=adapter,
        planner_provider=adapter,
        primary_provider=adapter,
        request_id=f"baseline-{case['id']}-{uuid4().hex}",
        search_adapter=None,
    )
    elapsed_ms = round((perf_counter() - started) * 1000, 2)
    return {
        "case_id": case["id"],
        "label": case["label"],
        "input": case["input"],
        "reply_text": payload.reply_text,
        "estimated_kcal": payload.estimated_kcal,
        "action_taken": payload.action_taken,
        "trace_contract": payload.trace_contract,
        "boundary_trace": payload.boundary_trace,
        "latency_ms": elapsed_ms,
        "trajectory_expectation": case["trajectory_expectation"],
    }


async def main() -> None:
    adapter = BuilderSpaceAdapter()
    results: list[dict[str, object]] = []
    for case in GOLDEN_CASES:
        try:
            results.append(await run_case(adapter, case))
        except Exception as exc:
            results.append(
                {
                    "case_id": case["id"],
                    "label": case["label"],
                    "input": case["input"],
                    "trajectory_expectation": case["trajectory_expectation"],
                    "error": str(exc),
                }
            )

    output_path = Path("artifacts") / "baseline_benchmark.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"golden_cases": GOLDEN_CASES, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nWrote baseline results to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
