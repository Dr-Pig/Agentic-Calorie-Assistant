from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

import httpx

from ..logger import logger
from ..runtime.contracts.trace import MANAGER_LOOP_STAGE
from ..text_integrity import corruption_summary, find_text_corruption


DEFAULT_BASE_URL = "https://space.ai-builders.com/backend/v1"
PLACEHOLDER_VALUES = {"", "replace-me", "https://api.example.com"}
MAX_PARSE_RETRIES = 1

DEFAULT_STAGE_TEMPERATURES = {
    MANAGER_LOOP_STAGE: 0.0,
}


class BuilderSpaceResponseError(RuntimeError):
    def __init__(self, message: str, *, trace: dict[str, Any]) -> None:
        super().__init__(message)
        self.trace = trace


class BuilderSpaceAdapter:
    def __init__(self, *, manager_model_override: str | None = None, role_label: str = "manager") -> None:
        self.base_url = os.getenv("AI_BUILDER_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.token = os.getenv("AI_BUILDER_TOKEN", "")
        self.manager_model = manager_model_override or os.getenv("BUILDERSPACE_MANAGER_MODEL", "deepseek")
        self.role_label = role_label
        self.timeout_seconds = min(int(os.getenv("AI_BUILDER_TIMEOUT_SECONDS", "15")), 15)
        self.transport_retry_count = max(0, int(os.getenv("AI_BUILDER_TRANSPORT_RETRY_COUNT", "2")))
        self.transport_retry_backoff_seconds = float(os.getenv("AI_BUILDER_TRANSPORT_RETRY_BACKOFF_SECONDS", "0.75"))
        self.manager_temperature = float(
            os.getenv("BUILDERSPACE_MANAGER_TEMPERATURE", str(DEFAULT_STAGE_TEMPERATURES[MANAGER_LOOP_STAGE]))
        )

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "builderspace",
            "configured": self._is_configured(),
            "manager_model": self.manager_model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "transport_retry_count": self.transport_retry_count,
            "transport_retry_backoff_seconds": self.transport_retry_backoff_seconds,
            "role": self.role_label,
            "stage_temperatures": {
                MANAGER_LOOP_STAGE: self.manager_temperature,
            },
            "stage_models": {
                MANAGER_LOOP_STAGE: self.manager_model,
            },
        }

    async def complete_with_trace(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        stage: str,
        max_tokens: int | None = 1800,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self._is_configured():
            raise RuntimeError("BuilderSpace is not configured.")

        model = self._model_for_stage(stage)
        formatted_user_message = self._format_user_message(stage, user_payload)
        self._check_encoding_safety(formatted_user_message)

        request_payload: dict[str, Any] = {
            "model": model,
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
        response: httpx.Response | None = None
        data: dict[str, Any] | None = None

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                for attempt_index in range(1, self.transport_retry_count + 2):
                    attempt_trace = {
                        "attempt_index": attempt_index,
                        "base_url": self.base_url,
                        "endpoint": f"{self.base_url}/chat/completions",
                        "model": model,
                        "stage": stage,
                    }
                    try:
                        response = await client.post(
                            f"{self.base_url}/chat/completions",
                            params={"debug": "true"},
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
                        except Exception as exc:  # parse failure is retriable once
                            parse_attempt = {
                                "attempt_index": attempt_index,
                                "stage": stage,
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                                "raw_content_excerpt": raw_content[:600],
                                "failure_family": "malformed_json",
                            }
                            parse_attempts.append(parse_attempt)
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
                        attempt_trace["status"] = "success"
                        transport_attempts.append(attempt_trace)
                        trace = {
                            "stage": stage,
                            "provider": "builderspace",
                            "model": model,
                            "request_payload": request_payload,
                            "raw_content": raw_content,
                            "raw_response_excerpt": response.text[:1200],
                            "parsed_object": parsed,
                            "status": data.get("status"),
                            "incomplete_details": data.get("incomplete_details"),
                            "usage": data.get("usage"),
                            "transport_attempts": transport_attempts,
                            "parse_attempts": parse_attempts,
                            "finish_reason": data["choices"][0].get("finish_reason"),
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
                raise last_error or RuntimeError("BuilderSpace transport failed without a captured exception.")
        except Exception as exc:
            failure_family = "empty_content" if "empty" in str(exc).lower() else "malformed_json"
            message = f"BuilderSpace manager error at stage={stage}: {type(exc).__name__}: {exc}"
            raise BuilderSpaceResponseError(
                message,
                trace={
                    "stage": stage,
                    "provider": "builderspace",
                    "model": model,
                    "request_payload": request_payload,
                    "transport_attempts": transport_attempts,
                    "parse_attempts": parse_attempts,
                    "base_url": self.base_url,
                    "timeout_seconds": self.timeout_seconds,
                    "request_failure_family": failure_family,
                },
            ) from exc

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        stage: str,
        max_tokens: int | None = 1800,
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
            raise RuntimeError(f"BuilderSpace returned no choices: {json.dumps(data)[:800]}")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            texts = [str(item.get("text") or "") for item in content if isinstance(item, dict)]
            content = "\n".join(texts).strip()
        content = str(content or "").strip()
        if not content:
            raise RuntimeError(f"BuilderSpace returned empty content: {json.dumps(data)[:800]}")
        return content

    def _extract_json_object(self, content: str) -> dict[str, Any]:
        text = self._sanitize_content(content)
        candidates = self._extract_json_candidates(text)
        if not candidates:
            raise RuntimeError("BuilderSpace did not return JSON.")
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
        payload = _jsonable(user_payload)
        return json.dumps({"stage": stage, "payload": payload}, ensure_ascii=False)

    def _check_encoding_safety(self, content: str) -> None:
        findings = find_text_corruption(content)
        if findings:
            summary = corruption_summary(findings)
            raise RuntimeError(
                f"Encoding Gate Failure (Layer 1): text corruption detected before serialization: {summary}"
            )

    def _model_for_stage(self, stage: str) -> str:
        return self.manager_model

    def _temperature_for_stage(self, stage: str) -> float:
        return self.manager_temperature

    def _response_schema_for_stage(self, stage: str) -> dict[str, Any] | None:
        if stage == MANAGER_LOOP_STAGE:
            return self._manager_loop_schema()
        return None

    def _manager_loop_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "manager_action": {"type": "string", "enum": ["call_tools", "final"]},
                "intent": {"type": "string"},
                "intent_type": {"type": "string"},
                "workflow_effect": {"type": "string"},
                "target_attachment": {"type": "object"},
                "exactness": {"type": "string"},
                "confidence": {"type": "string"},
                "evidence_posture": {"type": "string"},
                "repair_ack": {"type": "boolean"},
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
                "final_action": {"type": "string"},
                "answer_contract": {"type": "object"},
                "uncertainty_posture": {"type": "string"},
                "evidence_honesty_posture": {"type": "string"},
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

    def _is_configured(self) -> bool:
        return (
            self._has_real_value(self.base_url)
            and self._has_real_value(self.token)
            and self._has_real_value(self.manager_model)
        )

    def _has_real_value(self, value: str) -> bool:
        normalized = value.strip()
        if not normalized:
            return False
        if normalized in PLACEHOLDER_VALUES:
            return False
        if normalized.endswith("example.com"):
            return False
        return True


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
