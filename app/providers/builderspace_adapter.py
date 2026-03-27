from __future__ import annotations

import json
import os
from typing import Any

import httpx


class BuilderSpaceAdapter:
    def __init__(self) -> None:
        self.base_url = os.getenv("AI_BUILDER_BASE_URL", "").rstrip("/")
        self.token = os.getenv("AI_BUILDER_TOKEN", "")
        self.model = os.getenv("BUILDERSPACE_CHAT_MODEL", "supermind-agent-v1")

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "builderspace",
            "configured": bool(self.base_url and self.token and self.model),
            "model": self.model,
        }

    async def complete_with_trace(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        stage: str,
        max_tokens: int = 1800,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not (self.base_url and self.token):
            raise RuntimeError("BuilderSpace is not configured.")
        request_payload = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.token}"},
                json=request_payload,
            )
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        raw_content = str(content)
        parsed = self._extract_json_object(raw_content)
        trace = {
            "stage": stage,
            "provider": "builderspace",
            "model": self.model,
            "request_payload": request_payload,
            "raw_content": raw_content,
            "parsed_object": parsed,
        }
        return parsed, trace

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        max_tokens: int = 1800,
    ) -> dict[str, Any]:
        parsed, _trace = await self.complete_with_trace(
            system_prompt=system_prompt,
            user_payload=user_payload,
            stage="unspecified",
            max_tokens=max_tokens,
        )
        return parsed

    def _extract_json_object(self, content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        candidates = self._extract_json_candidates(text)
        if not candidates:
            raise RuntimeError("BuilderSpace did not return JSON.")
        expected_keys = {
            "meal_title",
            "meal_name",
            "meal_category",
            "decision",
            "components",
            "missing_modifiers",
            "estimated_kcal",
            "resolution",
            "component_estimates",
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
