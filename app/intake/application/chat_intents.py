from __future__ import annotations

import json
from typing import Any


PARSE_INTENT_PROMPT = """
You are a precise intent parser for a health tracking assistant.
The user is either reporting their current body weight or adjusting their daily calorie budget.

Your task is to extract the values from the user's input.
Rules:
1. If the user reports body weight, extract "weight_kg" as a float. E.g., "72kg" -> 72.0.
2. If the user asks to increase their budget, extract "delta_kcal" as a positive integer. E.g., "add 300 kcal" -> 300.
3. If the user asks to decrease their budget, extract "delta_kcal" as a negative integer. E.g., "reduce by 150 kcal" -> -150.
4. Set the fields to null if not applicable.

Output exactly a JSON object in this format:
{
    "weight_kg": float | null,
    "delta_kcal": int | null
}
"""


async def parse_weight_or_budget_intent(llm: Any, text: str) -> dict:
    try:
        raw = await llm.generate_structured(
            system_prompt=PARSE_INTENT_PROMPT,
            user_prompt=text,
            max_tokens=256,
        )
        return json.loads(raw)
    except Exception:
        return {"weight_kg": None, "delta_kcal": None}
