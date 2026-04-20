from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

import httpx

from ..logger import logger


DEFAULT_BASE_URL = "https://space.ai-builders.com/backend/v1"
PLACEHOLDER_VALUES = {"", "replace-me", "https://api.example.com"}
DEFAULT_TRANSPORT_RETRY_COUNT = 2
DEFAULT_TRANSPORT_RETRY_BACKOFF_SECONDS = 0.75
DEFAULT_STAGE_TEMPERATURES = {
    "task_meal_link_pass": 0.0,
    "decision_pass": 0.0,
    "nutrition_resolution_pass": 0.1,
    "final_response_pass": 0.5,
}


class BuilderSpaceResponseError(RuntimeError):
    def __init__(self, message: str, *, trace: dict[str, Any]) -> None:
        super().__init__(message)
        self.trace = trace


class BuilderSpaceAdapter:
    def __init__(
        self,
        *,
        task_meal_link_model_override: str | None = None,
        decision_model_override: str | None = None,
        nutrition_model_override: str | None = None,
        final_response_model_override: str | None = None,
        planner_model_override: str | None = None,
        primary_model_override: str | None = None,
        role_label: str = "default",
    ) -> None:
        self.base_url = os.getenv("AI_BUILDER_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.token = os.getenv("AI_BUILDER_TOKEN", "")
        legacy_planner_model = planner_model_override or os.getenv("BUILDERSPACE_PLANNER_MODEL", "grok-4-fast")
        legacy_primary_model = primary_model_override or os.getenv("BUILDERSPACE_PRIMARY_MODEL", "grok-4-fast")
        self.task_meal_link_model = task_meal_link_model_override or os.getenv("BUILDERSPACE_TASK_MEAL_LINK_MODEL", legacy_planner_model)
        self.decision_model = decision_model_override or os.getenv("BUILDERSPACE_DECISION_MODEL", legacy_primary_model)
        self.nutrition_model = nutrition_model_override or os.getenv("BUILDERSPACE_NUTRITION_MODEL", legacy_primary_model)
        self.final_response_model = final_response_model_override or os.getenv("BUILDERSPACE_FINAL_RESPONSE_MODEL", self.nutrition_model)
        self.planner_model = self.task_meal_link_model
        self.primary_model = self.nutrition_model
        self.role_label = role_label
        self.timeout_seconds = int(os.getenv("AI_BUILDER_TIMEOUT_SECONDS", "120"))
        self.transport_retry_count = max(0, int(os.getenv("AI_BUILDER_TRANSPORT_RETRY_COUNT", str(DEFAULT_TRANSPORT_RETRY_COUNT))))
        self.transport_retry_backoff_seconds = float(
            os.getenv("AI_BUILDER_TRANSPORT_RETRY_BACKOFF_SECONDS", str(DEFAULT_TRANSPORT_RETRY_BACKOFF_SECONDS))
        )
        self.task_meal_link_temperature = float(
            os.getenv("BUILDERSPACE_TASK_MEAL_LINK_TEMPERATURE", str(DEFAULT_STAGE_TEMPERATURES["task_meal_link_pass"]))
        )
        self.decision_temperature = float(
            os.getenv("BUILDERSPACE_DECISION_TEMPERATURE", str(DEFAULT_STAGE_TEMPERATURES["decision_pass"]))
        )
        self.nutrition_temperature = float(
            os.getenv("BUILDERSPACE_NUTRITION_TEMPERATURE", str(DEFAULT_STAGE_TEMPERATURES["nutrition_resolution_pass"]))
        )
        self.final_response_temperature = float(
            os.getenv("BUILDERSPACE_FINAL_RESPONSE_TEMPERATURE", str(DEFAULT_STAGE_TEMPERATURES["final_response_pass"]))
        )

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "builderspace",
            "configured": self._is_configured(),
            "task_meal_link_model": self.task_meal_link_model,
            "decision_model": self.decision_model,
            "nutrition_model": self.nutrition_model,
            "final_response_model": self.final_response_model,
            "planner_model": self.planner_model,
            "primary_model": self.primary_model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "transport_retry_count": self.transport_retry_count,
            "transport_retry_backoff_seconds": self.transport_retry_backoff_seconds,
            "role": self.role_label,
            "stage_temperatures": {
                "task_meal_link_pass": self.task_meal_link_temperature,
                "decision_pass": self.decision_temperature,
                "nutrition_resolution_pass": self.nutrition_temperature,
                "final_response_pass": self.final_response_temperature,
            },
            "stage_models": {
                "task_meal_link_pass": self.task_meal_link_model,
                "decision_pass": self.decision_model,
                "nutrition_resolution_pass": self.nutrition_model,
                "nutrition_resolution_pass_initial": self.nutrition_model,
                "nutrition_resolution_pass_tool_round_2": self.nutrition_model,
                "planner_pass_initial": self.task_meal_link_model,
                "primary_answer_pass_initial": self.nutrition_model,
                "primary_answer_pass_tool_round_2": self.nutrition_model,
                "final_response_pass": self.final_response_model,
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
        }
        if max_tokens is not None:
            request_payload["max_tokens"] = max_tokens
        extra_body = self._extra_body_for_stage(stage, model=model)
        if extra_body:
            request_payload["extra_body"] = extra_body

        response: httpx.Response | None = None
        data: dict[str, Any] | None = None
        transport_attempts: list[dict[str, Any]] = []
        last_error: Exception | None = None
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
                        logger.debug(f"BuilderSpace request: stage={stage}, model={model}, URL={self.base_url}")
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
                        try:
                            response.raise_for_status()
                        except httpx.HTTPStatusError as exc:
                            attempt_trace["error_type"] = type(exc).__name__
                            attempt_trace["error"] = str(exc)
                            attempt_trace["response_excerpt"] = exc.response.text[:800]
                            transport_attempts.append(attempt_trace)
                            logger.error(f"BuilderSpace HTTPError stage={stage} status={exc.response.status_code}")
                            raise RuntimeError(
                                f"BuilderSpace request failed: status={exc.response.status_code}, body={exc.response.text[:800]}"
                            ) from exc
                        data = response.json()
                        attempt_trace["status"] = "success"
                        transport_attempts.append(attempt_trace)
                        logger.info(f"BuilderSpace success: stage={stage}, model={model}, tokens={data.get('usage', {}).get('total_tokens', 'unknown')}")
                        break
                    except httpx.ReadTimeout as exc:
                        last_error = exc
                        attempt_trace["error_type"] = type(exc).__name__
                        attempt_trace["error"] = str(exc)
                        attempt_trace["timeout_seconds"] = self.timeout_seconds
                        transport_attempts.append(attempt_trace)
                    except httpx.HTTPError as exc:
                        last_error = exc
                        attempt_trace["error_type"] = type(exc).__name__
                        attempt_trace["error"] = str(exc)
                        transport_attempts.append(attempt_trace)
                    except RuntimeError as exc:
                        last_error = exc
                        if attempt_trace not in transport_attempts:
                            attempt_trace["error_type"] = type(exc).__name__
                            attempt_trace["error"] = str(exc)
                            transport_attempts.append(attempt_trace)
                    if data is not None:
                        break
                    if attempt_index < self.transport_retry_count + 1:
                        logger.warning(f"BuilderSpace transport failure stage={stage}, attempt={attempt_index}. Retrying in {self.transport_retry_backoff_seconds * attempt_index}s...")
                        await asyncio.sleep(self.transport_retry_backoff_seconds * attempt_index)
                if data is None:
                    raise last_error or RuntimeError("BuilderSpace transport failed without a captured exception.")
        except Exception as exc:
            message = (
                f"BuilderSpace transport error at stage={stage}: {type(exc).__name__}: {exc}; "
                f"attempts={len(transport_attempts)}"
            )
            raise BuilderSpaceResponseError(
                message,
                trace={
                    "stage": stage,
                    "provider": "builderspace",
                    "model": model,
                    "request_payload": request_payload,
                    "transport_attempts": transport_attempts,
                    "base_url": self.base_url,
                    "timeout_seconds": self.timeout_seconds,
                },
            ) from exc

        assert response is not None
        assert data is not None
        raw_content = self._extract_text_content(data)
        trace = {
            "stage": stage,
            "provider": "builderspace",
            "model": model,
            "request_payload": request_payload,
            "raw_content": raw_content,
            "raw_response_excerpt": response.text[:1200],
            "parsed_object": None,
            "status": data.get("status"),
            "incomplete_details": data.get("incomplete_details"),
            "usage": data.get("usage"),
            "output_tokens_details": (data.get("usage") or {}).get("output_tokens_details")
            or (data.get("usage") or {}).get("completion_tokens_details"),
            "orchestrator_trace": data.get("orchestrator_trace"),
            "transport_attempts": transport_attempts,
            "finish_reason": data["choices"][0].get("finish_reason"),
            "completion_tokens": (data.get("usage") or {}).get("completion_tokens"),
            "prompt_tokens": (data.get("usage") or {}).get("prompt_tokens"),
            "response_message_keys": list(data["choices"][0].get("message", {}).keys()),
            "choice_keys": list(data["choices"][0].keys()),
        }
        try:
            parsed = self._extract_json_object(raw_content)
        except Exception as exc:
            if (
                stage.startswith("primary_answer_pass")
                or stage.startswith("nutrition_resolution_pass")
                or stage.startswith("decision_pass")
                or stage.startswith("cheap_llm_review_pass")
            ):
                parsed = {"_raw_text": raw_content}
                trace["parsed_object"] = parsed
                return parsed, trace
            raise BuilderSpaceResponseError(
                f"{_exception_name(exc)}: raw_content={raw_content[:1200]}",
                trace=trace,
            ) from exc
        trace["parsed_object"] = parsed
        return parsed, trace

    def _extract_text_content(self, data: dict[str, Any]) -> str:
        content = data["choices"][0].get("message", {}).get("content", "")
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        text = str(content or "")
        if text.strip():
            return text
        trace_text = self._extract_trace_message(data.get("orchestrator_trace"))
        return trace_text or text

    def _extract_trace_message(self, orchestrator_trace: Any) -> str:
        if not isinstance(orchestrator_trace, dict):
            return ""
        rounds = orchestrator_trace.get("rounds")
        if not isinstance(rounds, list):
            return ""
        for item in rounds:
            if not isinstance(item, dict):
                continue
            message = item.get("message")
            if isinstance(message, str) and message.strip():
                return message
        return ""

    def _extract_json_object(self, content: str) -> dict[str, Any]:
        text = self._sanitize_content(content)
        candidates = self._extract_json_candidates(text)
        if not candidates:
            raise RuntimeError("BuilderSpace did not return JSON.")
        expected_keys = {
            "title",
            "ingredients",
            "recommended_action",
            "protein_g",
            "carb_g",
            "fat_g",
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

    def _format_user_message(self, stage: str, user_payload: dict[str, Any]) -> str:
        return json.dumps(_jsonable(user_payload), ensure_ascii=False)

    def _check_encoding_safety(self, content: str) -> None:
        """Layer 1 Hard Governance: Prevent mangled text from reaching LLM."""
        if "????" in content or "\ufffd" in content:
            raise RuntimeError(
                f"Encoding Gate Failure (Layer 1): Mangled Chinese characters '????' or '\\ufffd' "
                f"detected in payload. This usually means the data was piped from PowerShell "
                f"without UTF-8 encoding. Aborting to prevent data pollution."
            )

    def _model_for_stage(self, stage: str) -> str:
        if stage.startswith("task_meal_link_pass") or stage.startswith("planner_pass"):
            return self.task_meal_link_model
        if stage.startswith("decision_pass"):
            return self.decision_model
        if stage.startswith("nutrition_resolution_pass") or stage.startswith("primary_answer_pass"):
            return self.nutrition_model
        if stage.startswith("final_response_pass"):
            return self.final_response_model
        return self.nutrition_model

    def _temperature_for_stage(self, stage: str) -> float:
        if stage.startswith("task_meal_link_pass") or stage.startswith("planner_pass"):
            return self.task_meal_link_temperature
        if stage.startswith("decision_pass"):
            return self.decision_temperature
        if stage.startswith("nutrition_resolution_pass") or stage.startswith("primary_answer_pass"):
            return self.nutrition_temperature
        if stage.startswith("final_response_pass"):
            return self.final_response_temperature
        return self.nutrition_temperature

    def _extra_body_for_stage(self, stage: str, *, model: str) -> dict[str, Any] | None:
        if not self._should_send_gemini_extra_body(model):
            return None
        schema = self._response_schema_for_stage(stage)
        if not schema:
            return None
        return {
            "gemini": {
                "response_mime_type": "application/json",
                "response_json_schema": schema,
            }
        }

    def _should_send_gemini_extra_body(self, model: str) -> bool:
        normalized = str(model or "").strip().lower()
        return normalized.startswith("gemini")

    def _response_schema_for_stage(self, stage: str) -> dict[str, Any] | None:
        if stage.startswith("task_meal_link_pass"):
            return self._task_meal_link_schema()
        if stage.startswith("planner_pass"):
            return self._planner_schema()
        if stage.startswith("decision_pass"):
            return self._decision_pass_schema()
        if stage.startswith("nutrition_resolution_pass"):
            return self._nutrition_resolution_schema()
        if stage.startswith("primary_answer_pass"):
            return self._primary_runtime_schema()
        if stage.startswith("final_response_pass"):
            return self._final_response_schema()
        return None

    def _task_meal_link_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": ["food_estimation", "new_intake", "clarification", "modification", "correction", "general_chat"],
                },
                "scope": {"type": "string", "enum": ["meal_specific", "food_general", "non_food"]},
                "meal_link_action": {
                    "type": "string",
                    "enum": ["attach_to_existing_meal", "create_new_meal", "boundary_ambiguous", "none"],
                },
                "target_meal_id": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                "link_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "boundary_reason": {"type": "string"},
                "clarification_blocking": {"type": "boolean"},
                "normalized_user_input": {"type": "string"},
            },
            "required": [
                "intent",
                "scope",
                "meal_link_action",
                "target_meal_id",
                "link_confidence",
                "boundary_reason",
                "clarification_blocking",
                "normalized_user_input",
            ],
        }

    def _decision_pass_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "next_action": {
                    "type": "string",
                    "enum": ["run_tool_lookup", "run_clarify", "run_nutrition_resolution"],
                },
                "tool_plan": {
                    "type": "string",
                    "enum": [
                        "none",
                        "resolve_exact_item",
                        "get_meal_calibration",
                        "resolve_ingredient_anchors",
                        "search_official_nutrition",
                        "read_official_doc_fragment",
                    ],
                },
                "decision_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "tool_goal": {"type": "string"},
                "missing_evidence_type": {"type": "string"},
                "expected_success_condition": {"type": "string"},
                "clarify_priority": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "unresolved_info": {"type": "array", "items": {"type": "string"}},
                "response_mode_hint": {"type": "string", "enum": ["exact_answer", "rough_estimate_ok", "clarify_first"]},
                "clarify_is_blocking": {"type": "boolean"},
                "can_proceed_without_clarify": {"type": "boolean"},
            },
            "required": [
                "next_action",
                "tool_plan",
                "decision_confidence",
                "tool_goal",
                "missing_evidence_type",
                "expected_success_condition",
                "clarify_priority",
                "unresolved_info",
                "response_mode_hint",
                "clarify_is_blocking",
                "can_proceed_without_clarify",
            ],
        }

    def _nutrition_resolution_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "resolution_mode": {
                    "type": "string",
                    "enum": [
                        "exact_label_finalize",
                        "near_exact_finalize",
                        "component_estimate",
                        "provisional_estimate",
                        "cannot_estimate_yet",
                    ],
                },
                "resolution_basis": {
                    "type": "string",
                    "enum": [
                        "exact_item_evidence",
                        "official_source_evidence",
                        "component_model",
                        "calibrated_component_model",
                    ],
                },
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "exactness": {
                    "type": "string",
                    "enum": ["exact_item", "near_exact", "calibrated_estimate", "component_grounded", "best_effort", "unknown"],
                },
                "answer_payload": {"type": "object"},
                "unresolved_info": {"type": "array", "items": {"type": "string"}},
                "current_evidence_sufficiency": {"type": "string"},
                "why_no_more_tools": {"type": "string"},
                "reason_for_not_requesting_tool": {"type": "string"},
                "state_transition_hint": {
                    "anyOf": [
                        {"type": "string", "enum": ["candidate_meal", "draft_unresolved", "completed_meal"]},
                        {"type": "null"},
                    ]
                },
            },
            "required": [
                "resolution_mode",
                "resolution_basis",
                "confidence",
                "exactness",
                "answer_payload",
                "unresolved_info",
                "current_evidence_sufficiency",
                "why_no_more_tools",
                "reason_for_not_requesting_tool",
                "state_transition_hint",
            ],
        }

    def _primary_runtime_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action_taken": {
                    "type": "string",
                    "enum": [
                        "direct_answer",
                        "clarify_before_estimate",
                        "answer_with_uncertainty",
                        "request_tool",
                    ],
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                },
                "exactness": {
                    "type": "string",
                    "enum": [
                        "exact_item",
                        "near_exact",
                        "calibrated_estimate",
                        "component_grounded",
                        "best_effort",
                        "unknown",
                    ],
                },
                "tool_request": {
                    "type": "string",
                    "enum": [
                        "none",
                        "resolve_exact_item",
                        "get_meal_calibration",
                        "resolve_ingredient_anchors",
                        "search_official_nutrition",
                        "read_official_doc_fragment",
                    ],
                },
                "tool_request_reason": {"type": "string"},
                "state_transition_hint": {
                    "anyOf": [
                        {"type": "string", "enum": ["candidate_meal", "draft_unresolved", "completed_meal"]},
                        {"type": "null"},
                    ]
                },
                "food_origin": {"type": "string"},
                "food_class": {"type": "string"},
                "dish_structure": {"type": "string"},
                "needs_external_data": {"type": "boolean"},
                "private_info_risk": {"type": "string"},
                "title": {"type": "string"},
                "components": {"type": "array", "items": {"type": "string"}},
                "protein_g": {"type": "integer"},
                "carb_g": {"type": "integer"},
                "fat_g": {"type": "integer"},
                "kcal_low": {"type": "integer"},
                "kcal_high": {"type": "integer"},
                "kcal_most_likely": {"type": "integer"},
                "uncertainty_factors": {"type": "array", "items": {"type": "string"}},
                "top_uncertainty_drivers": {"type": "array", "items": {"type": "object"}},
                "follow_up_reasoning": {"type": "string"},
                "unresolved_info": {"type": "array", "items": {"type": "string"}},
                "response_mode_hint": {
                    "type": "string",
                    "enum": ["exact_answer", "rough_estimate_ok", "clarify_first"],
                },
                "external_data_query": {"type": "string"},
                "answer_payload": {"type": "object"},
            },
            "required": [
                "action_taken",
                "confidence",
                "exactness",
                "tool_request",
                "tool_request_reason",
                "state_transition_hint",
                "food_origin",
                "food_class",
                "dish_structure",
                "needs_external_data",
                "private_info_risk",
                "title",
                "components",
                "protein_g",
                "carb_g",
                "fat_g",
                "kcal_low",
                "kcal_high",
                "kcal_most_likely",
                "uncertainty_factors",
                "top_uncertainty_drivers",
                "follow_up_reasoning",
                "unresolved_info",
                "response_mode_hint",
                "external_data_query",
                "answer_payload",
            ],
        }

    def _planner_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": ["new_intake", "clarification", "modification", "correction", "general_chat", "food_estimation"]
                },
                "meal_boundary": {
                    "type": "string",
                    "enum": ["continue_active_meal", "start_new_meal", "boundary_clarification"],
                },
                "active_meal_reference": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                "boundary_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "resolved_query": {"type": "string"},
                "resolution_mode": {"type": "string", "enum": ["exact_match", "delta_update", "component_rebuild", "clarify_first", "none"]},
                "normalized_user_input": {"type": "string"},
                "input_signals": {"type": "object"},
                "missing_info": {"type": "array", "items": {"type": "string"}},
                "route_hints": {"type": "object"},
                "planning_brief": {
                    "type": "object",
                    "properties": {
                        "intent": {"type": "string"},
                        "resolved_query": {"type": "string"},
                        "resolution_mode": {"type": "string"},
                        "entity_type": {"type": "string"},
                        "state_link": {"type": "string"},
                        "clarification_needed": {"type": "boolean"},
                        "clarification_targets": {"type": "array", "items": {"type": "string"}},
                        "risk_focus": {"type": "array", "items": {"type": "string"}},
                        "evidence_strategy": {"type": "string"},
                        "primary_prompt_hints": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                        "active_object": {"type": "string", "enum": ["new_meal", "active_meal", "general_chat"]},
                        "slot_state": {"type": "string", "enum": ["enough_to_estimate", "needs_clarification", "needs_external_evidence"]},
                        "candidate_tool_calls": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "intent",
                        "resolved_query",
                        "resolution_mode",
                        "entity_type",
                        "state_link",
                        "clarification_needed",
                        "clarification_targets",
                        "risk_focus",
                        "evidence_strategy",
                        "primary_prompt_hints",
                        "confidence",
                        "active_object",
                        "slot_state",
                        "candidate_tool_calls",
                    ],
                },
            },
            "required": [
                "intent",
                "meal_boundary",
                "active_meal_reference",
                "boundary_confidence",
                "resolved_query",
                "resolution_mode",
                "normalized_user_input",
                "planning_brief",
            ],
        }

    def _final_response_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reply_text": {"type": "string"},
                "asked_follow_up": {"type": "boolean"},
                "ui_hints": {"type": "object"},
            },
            "required": ["reply_text", "asked_follow_up", "ui_hints"],
        }

    def _is_configured(self) -> bool:
        return (
            self._has_real_value(self.base_url)
            and self._has_real_value(self.token)
            and self._has_real_value(self.task_meal_link_model)
            and self._has_real_value(self.decision_model)
            and self._has_real_value(self.nutrition_model)
            and self._has_real_value(self.final_response_model)
        )

    def _has_real_value(self, value: str) -> bool:
        normalized = value.strip()
        if not normalized:
            return False
        if normalized in PLACEHOLDER_VALUES:
            return False
        if normalized.endswith("example.com"):
            return False
        if normalized == DEFAULT_BASE_URL:
            return True
        return True


def _exception_name(exc: Exception) -> str:
    text = str(exc).strip()
    return text or exc.__class__.__name__


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
