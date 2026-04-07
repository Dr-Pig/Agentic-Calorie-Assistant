# -*- coding: utf-8 -*-
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from app.usecases.text_meal import run_text_meal_canary
from app.schemas import EstimateRequest
from app.providers.builderspace_adapter import BuilderSpaceAdapter

async def run():
    provider = BuilderSpaceAdapter()
    results = []
    cases = ["五十嵐四季春珍波椰", "五十嵐珍珠奶茶"]
    for i, text in enumerate(cases):
        req = EstimateRequest(text=text, allow_search=True)
        res = await run_text_meal_canary(req, provider=provider, request_id=f"val_{i}")
        results.append(res.model_dump())
    
    Path(".logs/planner_off_branded_drink_validation_20260331_post_tfda.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Validation done")

if __name__ == "__main__":
    asyncio.run(run())
