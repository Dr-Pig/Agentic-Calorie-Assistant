from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx


DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
PLACEHOLDER_VALUES = {
    "",
    "replace-me",
}

COMPONENT_ESTIMATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "source": {"type": "string", "enum": ["explicit", "implicit"]},
        "quantity_hint": {"type": "string"},
        "estimated_kcal": {"type": "integer"},
        "protein_g": {"type": "integer"},
        "carb_g": {"type": "integer"},
        "fat_g": {"type": "integer"},
    },
    "required": [
        "name",
        "source",
        "quantity_hint",
        "estimated_kcal",
        "protein_g",
        "carb_g",
        "fat_g",
    ],
}


class GeminiAdapter:
    def __init__(self) -> None:
        self.base_url = os.getenv("GEMINI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.default_model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
        self.component_model = os.getenv("GEMINI_COMPONENT_MODEL", self.default_model)
        self.answer_model = os.getenv("GEMINI_ANSWER_MODEL", self.default_model)
        self.timeout_seconds = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "120"))

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "gemini",
            "configured": self._is_configured(),
            "model": self.default_model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "stage_models": {
                "planner_pass_initial": self.component_model,
                "main_pass": self.component_model,
                "answer_after_search": self.answer_model,
            },
        }

    async def complete_with_trace(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        stage: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self._is_configured():
            raise RuntimeError("Gemini is not configured.")
        model = self._model_for_stage(stage)
        generation_config: dict[str, Any] = {
            "temperature": 0.1,
            "maxOutputTokens": max_tokens,
        }
        schema = self._response_schema_for_stage(stage)
        if schema is not None:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseJsonSchema"] = schema

        request_payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": json.dumps(user_payload, ensure_ascii=False)}],
                }
            ],
            "generationConfig": generation_config,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/models/{model}:generateContent",
                params={"key": self.api_key},
                headers={"Content-Type": "application/json"},
                json=request_payload,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"Gemini request failed: status={exc.response.status_code}, body={exc.response.text[:800]}"
                ) from exc
            data = response.json()

        raw_content = self._extract_text(data)
        parsed = self._extract_json_object(raw_content)
        trace = {
            "stage": stage,
            "provider": "gemini",
            "model": model,
            "request_payload": request_payload,
            "raw_content": raw_content,
            "parsed_object": parsed,
            "usage": data.get("usageMetadata"),
        }
        return parsed, trace

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        max_tokens: int = 1800,
    ) -> dict[str, Any]:
        parsed, _ = await self.complete_with_trace(
            system_prompt=system_prompt,
            user_payload=user_payload,
            stage="unspecified",
            max_tokens=max_tokens,
        )
        return parsed

    def _extract_text(self, data: dict[str, Any]) -> str:
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {json.dumps(data)[:800]}")
        parts = ((candidates[0].get("content") or {}).get("parts")) or []
        texts: list[str] = []
        for part in parts:
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text)
        raw = "\n".join(texts).strip()
        if raw:
            return raw
        raise RuntimeError(f"Gemini returned empty text: {json.dumps(data)[:800]}")

    def _extract_json_object(self, content: str) -> dict[str, Any]:
        text = self._sanitize_content(content)
        candidates = self._extract_json_candidates(text)
        if not candidates:
            raise RuntimeError("Gemini did not return JSON.")
        expected_keys = {
            "route_target",
            "meal_title",
            "components",
            "quantity_hints",
            "component_estimates",
            "protein_g",
            "carb_g",
            "fat_g",
            "estimated_kcal",
            "uncertain_areas",
            "followup_question",
            "search_query",
            "reasoning_notes",
        }
        return max(candidates, key=lambda obj: len(expected_keys.intersection(set(obj.keys()))))

    def _extract_json_candidates(self, content: str) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        stack = 0
        start_index: int | None = None
        for index, char in enumerate(content):
            if char == "{":
                if stack == 0:
                    start_index = index
                stack += 1
            elif char == "}":
                if stack > 0:
                    stack -= 1
                    if stack == 0 and start_index is not None:
                        chunk = content[start_index : index + 1]
                        try:
                            parsed = json.loads(chunk)
                        except json.JSONDecodeError:
                            start_index = None
                            continue
                        if isinstance(parsed, dict):
                            candidates.append(parsed)
                        start_index = None
        return candidates

    def _sanitize_content(self, content: str) -> str:
        text = content.strip().replace("\ufeff", "")
        fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            text = "\n".join(chunk.strip() for chunk in fenced if chunk.strip())
        return text

    def _model_for_stage(self, stage: str) -> str:
        if stage.startswith("planner_pass"):
            return self.component_model
        if stage == "main_pass":
            return self.component_model
        if stage == "answer_after_search":
            return self.answer_model
        return self.default_model

    def _response_schema_for_stage(self, stage: str) -> dict[str, Any] | None:
        if stage.startswith("planner_pass"):
            return self._planner_schema()
        if stage == "main_pass":
            return self._main_pass_schema(
                route_targets=[
                    "direct_estimate",
                    "estimate_with_assumptions",
                    "search_then_answer",
                    "ask_user",
                ]
            )
        if stage == "answer_after_search":
            return self._main_pass_schema(
                route_targets=[
                    "direct_estimate",
                    "estimate_with_assumptions",
                    "ask_user",
                ]
            )
        return None

    def _main_pass_schema(self, *, route_targets: list[str]) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "route_target": {"type": "string", "enum": route_targets},
                "meal_title": {"type": "string"},
                "components": {"type": "array", "items": {"type": "string"}},
                "quantity_hints": {"type": "array", "items": {"type": "string"}},
                "component_estimates": {"type": "array", "items": COMPONENT_ESTIMATE_SCHEMA},
                "protein_g": {"type": "integer"},
                "carb_g": {"type": "integer"},
                "fat_g": {"type": "integer"},
                "estimated_kcal": {"type": "integer"},
                "uncertain_areas": {"type": "array", "items": {"type": "string"}},
                "followup_question": {"type": "string"},
                "search_query": {"type": "string"},
                "reasoning_notes": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "route_target",
                "meal_title",
                "components",
                "quantity_hints",
                "component_estimates",
                "protein_g",
                "carb_g",
                "fat_g",
                "estimated_kcal",
                "uncertain_areas",
                "followup_question",
                "search_query",
                "reasoning_notes",
            ],
        }

    def _planner_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": [
                        "food_estimation",
                        "food_recommendation",
                        "meal_planning",
                        "weight_log",
                        "log_edit",
                        "general_chat",
                    ],
                },
                "route": {
                    "type": "string",
                    "enum": ["estimation", "recommendation", "planning", "weight", "edit", "fallback"],
                },
                "normalized_user_input": {"type": "string"},
                "input_signals": {
                    "type": "object",
                    "properties": {
                        "modalities": {"type": "array", "items": {"type": "string"}},
                        "foods": {"type": "array", "items": {"type": "string"}},
                        "brands": {"type": "array", "items": {"type": "string"}},
                        "portion_clues": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["modalities", "foods", "brands", "portion_clues"],
                },
                "missing_info": {"type": "array", "items": {"type": "string"}},
                "route_hints": {"type": "object"},
            },
            "required": [
                "intent",
                "route",
                "normalized_user_input",
                "input_signals",
                "missing_info",
                "route_hints",
            ],
        }

    def _is_configured(self) -> bool:
        return (
            self._has_real_value(self.base_url)
            and self._has_real_value(self.api_key)
            and self._has_real_value(self.default_model)
        )

    def _has_real_value(self, value: str) -> bool:
        normalized = value.strip()
        if not normalized:
            return False
        return normalized not in PLACEHOLDER_VALUES
