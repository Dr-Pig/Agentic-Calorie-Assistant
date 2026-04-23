from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

import httpx

from ..runtime.contracts.trace import MANAGER_LOOP_STAGE
from ..text_integrity import corruption_summary, find_text_corruption


DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
MAX_PARSE_RETRIES = 1


class DeepSeekResponseError(RuntimeError):
    def __init__(self, message: str, *, trace: dict[str, Any]) -> None:
        super().__init__(message)
        self.trace = trace


class DeepSeekAdapter:
    """Single-manager adapter for DeepSeek chat completions."""

    def __init__(self) -> None:
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.token = os.getenv("DEEPSEEK_API_KEY", "")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.timeout_seconds = min(int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "15")), 15)
        self.transport_retry_count = max(0, int(os.getenv("DEEPSEEK_TRANSPORT_RETRY_COUNT", "2")))
        self.transport_retry_backoff_seconds = float(os.getenv("DEEPSEEK_TRANSPORT_RETRY_BACKOFF_SECONDS", "1.0"))
        self.temperature = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.0"))

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "deepseek",
            "configured": bool(self.token),
            "manager_model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "transport_retry_count": self.transport_retry_count,
            "transport_retry_backoff_seconds": self.transport_retry_backoff_seconds,
            "stage_models": {
                MANAGER_LOOP_STAGE: self.model,
            },
            "stage_temperatures": {
                MANAGER_LOOP_STAGE: self.temperature,
            },
        }

    async def complete_with_trace(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        stage: str,
        max_tokens: int | None = 2000,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.token:
            raise RuntimeError("DeepSeek API Key is missing. Please set DEEPSEEK_API_KEY.")

        formatted_user_message = self._format_user_message(stage, user_payload)
        self._check_encoding_safety(formatted_user_message)

        request_payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self._temperature_for_stage(stage),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": formatted_user_message},
            ],
            "response_format": {"type": "json_object"},
        }
        if max_tokens is not None:
            request_payload["max_tokens"] = max_tokens

        transport_attempts: list[dict[str, Any]] = []
        parse_attempts: list[dict[str, Any]] = []
        last_error: Exception | None = None
        parse_retry_budget = MAX_PARSE_RETRIES

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                for attempt_index in range(1, self.transport_retry_count + 2):
                    attempt_trace = {
                        "attempt_index": attempt_index,
                        "model": self.model,
                        "stage": stage,
                        "endpoint": f"{self.base_url}/chat/completions",
                    }
                    try:
                        response = await client.post(
                            f"{self.base_url}/chat/completions",
                            headers={
                                "Authorization": f"Bearer {self.token}",
                                "Content-Type": "application/json",
                            },
                            json=request_payload,
                        )
                        attempt_trace["http_status"] = response.status_code
                        response.raise_for_status()
                        data = response.json()
                        raw_content = self._extract_text_content(data)
                        try:
                            parsed = self._extract_json_object(raw_content)
                        except Exception as exc:
                            parse_attempts.append(
                                {
                                    "attempt_index": attempt_index,
                                    "stage": stage,
                                    "error_type": type(exc).__name__,
                                    "error": str(exc),
                                    "raw_content_excerpt": raw_content[:600],
                                    "failure_family": "malformed_json",
                                }
                            )
                            last_error = exc
                            if parse_retry_budget > 0:
                                parse_retry_budget -= 1
                                continue
                            raise
                        if not parsed:
                            exc = RuntimeError("empty parsed manager payload")
                            parse_attempts.append(
                                {
                                    "attempt_index": attempt_index,
                                    "stage": stage,
                                    "error_type": type(exc).__name__,
                                    "error": str(exc),
                                    "failure_family": "empty_content",
                                }
                            )
                            last_error = exc
                            if parse_retry_budget > 0:
                                parse_retry_budget -= 1
                                continue
                            raise exc
                        try:
                            self._validate_manager_payload(stage, parsed)
                        except Exception as exc:
                            parse_attempts.append(
                                {
                                    "attempt_index": attempt_index,
                                    "stage": stage,
                                    "error_type": type(exc).__name__,
                                    "error": str(exc),
                                    "failure_family": "malformed_json",
                                }
                            )
                            last_error = exc
                            if parse_retry_budget > 0:
                                parse_retry_budget -= 1
                                continue
                            raise

                        attempt_trace["status"] = "success"
                        transport_attempts.append(attempt_trace)
                        trace = {
                            "stage": stage,
                            "provider": "deepseek",
                            "model": self.model,
                            "request_payload": request_payload,
                            "raw_content": raw_content,
                            "parsed_object": parsed,
                            "usage": data.get("usage"),
                            "transport_attempts": transport_attempts,
                            "parse_attempts": parse_attempts,
                            "finish_reason": (data.get("choices") or [{}])[0].get("finish_reason"),
                            "request_failure_family": None,
                        }
                        return parsed, trace
                    except Exception as exc:
                        last_error = exc
                        attempt_trace["error_type"] = type(exc).__name__
                        attempt_trace["error"] = str(exc)
                        transport_attempts.append(attempt_trace)
                        if attempt_index < self.transport_retry_count + 1:
                            await asyncio.sleep(self.transport_retry_backoff_seconds * attempt_index)
                raise last_error or RuntimeError("DeepSeek transport failed without a captured exception.")
        except Exception as exc:
            failure_family = "empty_content" if "empty" in str(exc).lower() else "malformed_json"
            raise DeepSeekResponseError(
                f"DeepSeek manager error at stage={stage}: {type(exc).__name__}: {exc}",
                trace={
                    "stage": stage,
                    "provider": "deepseek",
                    "model": self.model,
                    "request_payload": request_payload,
                    "transport_attempts": transport_attempts,
                    "parse_attempts": parse_attempts,
                    "request_failure_family": failure_family,
                },
            ) from exc

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        stage: str,
        max_tokens: int | None = 2000,
    ) -> dict[str, Any]:
        parsed, _ = await self.complete_with_trace(
            system_prompt=system_prompt,
            user_payload=user_payload,
            stage=stage,
            max_tokens=max_tokens,
        )
        return parsed

    def _extract_text_content(self, data: dict[str, Any]) -> str:
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

    def _extract_json_object(self, content: str) -> dict[str, Any]:
        text = self._sanitize_content(content)
        candidates = self._extract_json_candidates(text)
        if not candidates:
            raise RuntimeError("DeepSeek did not return JSON.")
        return candidates[-1]

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

    def _format_user_message(self, stage: str, user_payload: dict[str, Any]) -> str:
        return json.dumps({"stage": stage, "payload": self._jsonable(user_payload)}, ensure_ascii=False)

    def _check_encoding_safety(self, content: str) -> None:
        findings = find_text_corruption(content)
        if findings:
            summary = corruption_summary(findings)
            raise RuntimeError(
                f"Encoding Gate Failure (Layer 1): text corruption detected before serialization: {summary}"
            )

    def _temperature_for_stage(self, stage: str) -> float:
        return self.temperature

    def _response_schema_for_stage(self, stage: str) -> dict[str, Any] | None:
        if stage == MANAGER_LOOP_STAGE:
            return {
                "type": "object",
                "properties": {
                    "manager_action": {"type": "string"},
                    "intent": {"type": "string"},
                    "intent_type": {"type": "string"},
                    "final_action": {"type": "string"},
                    "workflow_effect": {"type": "string"},
                    "target_attachment": {"type": "object"},
                    "exactness": {"type": "string"},
                    "confidence": {"type": "string"},
                    "evidence_posture": {"type": "string"},
                    "repair_ack": {"type": "boolean"},
                    "answer_contract": {"type": "object"},
                    "uncertainty_posture": {"type": "string"},
                    "evidence_honesty_posture": {"type": "string"},
                    "response_summary": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "pending_followup": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "tool_calls": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "arguments": {"type": "object"},
                            },
                            "required": ["name"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "manager_action",
                    "intent",
                    "workflow_effect",
                    "target_attachment",
                    "exactness",
                    "confidence",
                    "evidence_posture",
                    "repair_ack",
                ],
                "additionalProperties": False,
            }
        return None

    def _validate_manager_payload(self, stage: str, payload: dict[str, Any]) -> None:
        schema = self._response_schema_for_stage(stage)
        if schema is None:
            return
        required = set(schema.get("required") or [])
        missing = sorted(key for key in required if key not in payload)
        if missing:
            raise RuntimeError(f"manager payload missing required fields for {stage}: {missing}")
        if schema.get("additionalProperties") is False:
            allowed = set((schema.get("properties") or {}).keys())
            unknown = sorted(key for key in payload.keys() if key not in allowed)
            if unknown:
                raise RuntimeError(f"manager payload has unknown fields for {stage}: {unknown}")

    def _jsonable(self, value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, dict):
            return {str(k): self._jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._jsonable(v) for v in value]
        return value
