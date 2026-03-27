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

    async def complete_structured(self, *, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        if not (self.base_url and self.token):
            raise RuntimeError("BuilderSpace is not configured.")
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "max_tokens": 1800,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.token}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return self._extract_json_object(str(content))

    def _extract_json_object(self, content: str) -> dict[str, Any]:
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end < 0 or end <= start:
            raise RuntimeError("BuilderSpace did not return JSON.")
        return json.loads(content[start : end + 1])
