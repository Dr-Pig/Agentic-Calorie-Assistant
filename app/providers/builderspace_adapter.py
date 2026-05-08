from __future__ import annotations

import os
from typing import Any

import httpx

from .builderspace_config import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    check_encoding_safety,
    effective_timeout_seconds,
    format_user_message,
    is_configured,
)
from .builderspace_parsing import jsonable
from .builderspace_prompt_cache import apply_prompt_cache_key
from .builderspace_trace import build_failure_trace
from .builderspace_transport import (
    decision_transport_request_for_stage,
    response_format_request_for_stage,
)
from .builderspace_runtime_contract import (
    manager_loop_schema,
    response_schema_for_stage,
    validate_manager_payload,
)
from .builderspace_session import complete_builderspace_with_trace
from ..runtime.contracts.trace import MANAGER_LOOP_STAGE


DEFAULT_BASE_URL = "https://space.ai-builders.com/backend/v1"
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
        self.configured_timeout_env = os.getenv("AI_BUILDER_TIMEOUT_SECONDS")
        self.timeout_seconds, self.timeout_was_clamped = effective_timeout_seconds(self.configured_timeout_env)
        self.transport_retry_count = max(0, int(os.getenv("AI_BUILDER_TRANSPORT_RETRY_COUNT", "2")))
        self.transport_retry_backoff_seconds = float(os.getenv("AI_BUILDER_TRANSPORT_RETRY_BACKOFF_SECONDS", "0.75"))
        self.manager_temperature = float(
            os.getenv("BUILDERSPACE_MANAGER_TEMPERATURE", str(DEFAULT_STAGE_TEMPERATURES[MANAGER_LOOP_STAGE]))
        )

    def _model_for_stage(self, stage: str) -> str:
        return self.manager_model

    def _temperature_for_stage(self, stage: str) -> float:
        return self.manager_temperature

    def _format_user_message(self, stage: str, payload: dict[str, Any]) -> str:
        return format_user_message(stage, jsonable(payload))

    def _response_schema_for_stage(self, stage: str, constraints: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return response_schema_for_stage(stage, constraints)

    def _response_format_request_for_stage(
        self,
        stage: str,
        constraints: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return response_format_request_for_stage(
            stage,
            constraints=constraints,
            schema=response_schema_for_stage(stage, constraints),
        )

    def _decision_transport_request_for_stage(
        self,
        stage: str,
        constraints: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        return decision_transport_request_for_stage(
            stage,
            constraints=constraints,
            manager_loop_schema=manager_loop_schema(constraints),
        )

    def _validate_manager_payload(
        self,
        stage: str,
        payload: dict[str, Any],
        constraints: dict[str, Any] | None = None,
    ) -> None:
        validate_manager_payload(stage, payload, constraints=constraints)

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "builderspace",
            "configured": is_configured(
                base_url=self.base_url,
                token=self.token,
                manager_model=self.manager_model,
            ),
            "manager_model": self.manager_model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "configured_timeout_env": self.configured_timeout_env,
            "default_timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
            "max_timeout_seconds": MAX_TIMEOUT_SECONDS,
            "timeout_was_clamped": self.timeout_was_clamped,
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
        if not is_configured(base_url=self.base_url, token=self.token, manager_model=self.manager_model):
            raise RuntimeError("BuilderSpace is not configured.")

        model = self.manager_model
        formatted_user_message = format_user_message(stage, jsonable(user_payload))
        check_encoding_safety(formatted_user_message)
        constraints = dict(user_payload.get("constraints") or {})

        decision_transport_request, decision_transport_meta = self._decision_transport_request_for_stage(
            stage,
            constraints=constraints,
        )
        response_format, transport_meta = self._response_format_request_for_stage(
            stage,
            constraints=constraints,
        )
        base_request_payload: dict[str, Any] = {
            "model": model,
            "temperature": self.manager_temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": formatted_user_message},
            ],
        }
        if max_tokens is not None:
            base_request_payload["max_tokens"] = max_tokens
        base_request_payload = apply_prompt_cache_key(
            base_request_payload,
            model=model,
            stage=stage,
        )
        return await complete_builderspace_with_trace(
            base_url=self.base_url,
            token=self.token,
            timeout_seconds=self.timeout_seconds,
            transport_retry_count=self.transport_retry_count,
            transport_retry_backoff_seconds=self.transport_retry_backoff_seconds,
            model=model,
            stage=stage,
            manager_temperature=self.manager_temperature,
            base_request_payload=base_request_payload,
            constraints=constraints,
            response_format=response_format,
            transport_meta=transport_meta,
            decision_transport_request=decision_transport_request,
            decision_transport_meta=decision_transport_meta,
            validate_manager_payload=validate_manager_payload,
            async_client_factory=httpx.AsyncClient,
            build_error=lambda **kwargs: BuilderSpaceResponseError(
                f"BuilderSpace manager error at stage={stage}: {type(kwargs['exc']).__name__}: {kwargs['exc']}",
                trace=build_failure_trace(
                    exc=kwargs["exc"],
                    stage=stage,
                    provider="builderspace",
                    model=model,
                    request_payload=kwargs["request_payload"],
                    transport_attempts=kwargs["transport_attempts"],
                    parse_attempts=kwargs["parse_attempts"],
                    base_url=self.base_url,
                    timeout_seconds=self.timeout_seconds,
                    response_text=(
                        kwargs["response"].text
                        if kwargs["response"] is not None
                        else getattr(kwargs["exc"], "raw_response_excerpt", None)
                    ),
                    response_status=kwargs["response"].status_code if kwargs["response"] is not None else None,
                    data=kwargs["data"] if isinstance(kwargs["data"], dict) else None,
                    transport_meta={**kwargs["transport_meta"], "fallback_reason": kwargs["transport_meta"]["fallback_reason"] or kwargs["fallback_reason"]},
                    decision_transport_meta=kwargs["decision_transport_meta"],
                    effective_response_format_type=kwargs["effective_response_format_type"],
                ),
            ),
        )

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
