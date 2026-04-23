from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal


ObservationAction = Literal["create_observation", "cannot_extract"]
ObservationType = Literal["weight", "body_fat_percentage", "other"]

_BODY_OBSERVATION_EXTRACTION_PROMPT = """
You extract body-observation create intents for a health assistant.

Return exactly one JSON object with:
- observation_action: "create_observation" or "cannot_extract"
- observation_type: "weight", "body_fat_percentage", or "other"
- value: number or null
- unit: string or null
- occurred_at_interpretation: short string or null

Rules:
- Use "weight" for weight logs such as "I am 58 kg today".
- Use "body_fat_percentage" for body-fat logs such as "body fat is 23%".
- If the user is asking a question instead of logging a new observation, return "cannot_extract".
- Do not invent values.
"""


@dataclass(frozen=True)
class BodyObservationExtractionResult:
    decision_mode: Literal["llm"] = "llm"
    decision_reason: str = "body observation extraction is a semantic interpretation task"
    observation_action: ObservationAction = "cannot_extract"
    observation_type: ObservationType = "other"
    value: float | None = None
    unit: str | None = None
    occurred_at_interpretation: str | None = None


def _normalize_type(value: str | None) -> ObservationType:
    normalized = str(value or "").strip().lower()
    if normalized == "weight":
        return "weight"
    if normalized == "body_fat_percentage":
        return "body_fat_percentage"
    return "other"


def _normalize_unit(*, observation_type: ObservationType, unit: str | None) -> str | None:
    normalized = str(unit or "").strip().lower()
    if normalized:
        if normalized in {"kg", "kgs", "kilogram", "kilograms"}:
            return "kg"
        if normalized in {"%", "percent", "percentage"}:
            return "%"
        return normalized
    if observation_type == "weight":
        return "kg"
    if observation_type == "body_fat_percentage":
        return "%"
    return None


def _cannot_extract() -> BodyObservationExtractionResult:
    return BodyObservationExtractionResult()


async def build_body_observation_extraction(
    llm: Any,
    *,
    raw_user_input: str,
) -> BodyObservationExtractionResult:
    try:
        raw = await llm.generate_structured(
            system_prompt=_BODY_OBSERVATION_EXTRACTION_PROMPT,
            user_prompt=raw_user_input,
            max_tokens=256,
        )
        payload = json.loads(raw)
    except Exception:
        return _cannot_extract()

    action = str(payload.get("observation_action") or "cannot_extract").strip()
    if action != "create_observation":
        return _cannot_extract()

    observation_type = _normalize_type(payload.get("observation_type"))
    try:
        value = float(payload.get("value")) if payload.get("value") is not None else None
    except (TypeError, ValueError):
        value = None

    unit = _normalize_unit(observation_type=observation_type, unit=payload.get("unit"))
    if value is None:
        return _cannot_extract()

    return BodyObservationExtractionResult(
        observation_action="create_observation",
        observation_type=observation_type,
        value=value,
        unit=unit,
        occurred_at_interpretation=str(payload.get("occurred_at_interpretation") or "").strip() or None,
    )
