from __future__ import annotations

import json
import re
from typing import Any


def extract_text_content(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"DeepSeek returned no choices: {json.dumps(data)[:800]}")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        texts = [str(item.get("text") or "") for item in content if isinstance(item, dict)]
        content = "\n".join(texts).strip()
    content = str(content or "").strip()
    if not content:
        raise RuntimeError(f"DeepSeek returned empty content: {json.dumps(data)[:800]}")
    return content


def extract_json_object(content: str) -> dict[str, Any]:
    text = sanitize_content(content)
    candidates = extract_json_candidates(text)
    if not candidates:
        raise RuntimeError("DeepSeek did not return JSON.")
    return candidates[-1]


def extract_json_candidates(content: str) -> list[dict[str, Any]]:
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


def sanitize_content(content: str) -> str:
    text = content.strip().replace("\ufeff", "")
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = "\n".join(chunk.strip() for chunk in fenced if chunk.strip())
    return text
