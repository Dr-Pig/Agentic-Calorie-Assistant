from __future__ import annotations

import json
import re
from typing import Any


class BuilderSpaceParseError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        failure_family: str,
        failing_component: str,
        observed_value: Any = None,
        raw_content: str | None = None,
        parse_attempts: list[dict[str, Any]] | None = None,
        parse_contract_status: str | None = None,
        parse_recovery_used: bool = False,
        parse_recovery_strategy: str | None = None,
        parse_recovery_ambiguous: bool = False,
    ) -> None:
        super().__init__(message)
        self.failure_family = failure_family
        self.failing_component = failing_component
        self.observed_value = observed_value
        self.observed_type = observed_type_name(observed_value)
        self.value_excerpt, self.value_truncated = value_excerpt(observed_value)
        self.raw_content_excerpt, self.raw_content_truncated = value_excerpt(raw_content)
        self.parse_attempts = list(parse_attempts or [])
        self.parse_contract_status = parse_contract_status
        self.parse_recovery_used = parse_recovery_used
        self.parse_recovery_strategy = parse_recovery_strategy
        self.parse_recovery_ambiguous = parse_recovery_ambiguous


def extract_text_content(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise BuilderSpaceParseError(
            "BuilderSpace returned invalid choices envelope.",
            failure_family="choices_shape_error",
            failing_component="builderspace_adapter.extract_choices",
            observed_value=choices,
        )
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise BuilderSpaceParseError(
            "BuilderSpace first choice must be an object.",
            failure_family="choices_shape_error",
            failing_component="builderspace_adapter.extract_choices",
            observed_value=first_choice,
        )
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise BuilderSpaceParseError(
            "BuilderSpace message must be an object.",
            failure_family="message_shape_error",
            failing_component="builderspace_adapter.extract_message",
            observed_value=message,
        )
    content = message.get("content")
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                raise BuilderSpaceParseError(
                    "BuilderSpace content list must contain object parts only.",
                    failure_family="content_shape_error",
                    failing_component="builderspace_adapter.extract_text_content",
                    observed_value=item,
                )
            texts.append(str(item.get("text") or ""))
        content = "\n".join(texts).strip()
    elif content is not None and not isinstance(content, str):
        raise BuilderSpaceParseError(
            "BuilderSpace content must be a string or a list of text parts.",
            failure_family="content_shape_error",
            failing_component="builderspace_adapter.extract_text_content",
            observed_value=content,
        )
    content = str(content or "").strip()
    if not content:
        raise BuilderSpaceParseError(
            "BuilderSpace returned empty content.",
            failure_family="non_json_model_output",
            failing_component="builderspace_adapter.extract_text_content",
            observed_value=content,
            raw_content=content,
        )
    return content


def extract_finish_reason(data: dict[str, Any] | None) -> str | None:
    if not isinstance(data, dict):
        return None
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None
    finish_reason = first_choice.get("finish_reason")
    return finish_reason if isinstance(finish_reason, str) else None


def extract_json_object(content: str) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_text = content.strip().replace("\ufeff", "")
    parse_attempts: list[dict[str, Any]] = []
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        parse_attempts.append(
            {
                "parser": "strict_json",
                "status": "failed",
                "failure_family": "malformed_json",
                "error_type": type(exc).__name__,
            }
        )
    else:
        if isinstance(parsed, dict):
            parse_attempts.append(
                {
                    "parser": "strict_json",
                    "status": "success",
                    "parse_contract_status": "strict_json",
                }
            )
            return parsed, {
                "parse_contract_status": "strict_json",
                "parse_recovery_used": False,
                "parse_recovery_strategy": None,
                "parse_recovery_ambiguous": False,
                "parse_attempts": parse_attempts,
                "raw_content_excerpt": raw_text[:1200],
                "finish_reason": None,
            }
        raise BuilderSpaceParseError(
            "BuilderSpace strict JSON content must be an object.",
            failure_family="malformed_json",
            failing_component="builderspace_adapter.extract_json_object",
            observed_value=parsed,
            raw_content=raw_text,
            parse_attempts=parse_attempts,
        )

    fenced = re.findall(r"```(?:json)?\s*(.*?)```", raw_text, flags=re.DOTALL | re.IGNORECASE)
    fenced_candidates: list[dict[str, Any]] = []
    for chunk in fenced:
        chunk_text = chunk.strip()
        if not chunk_text:
            continue
        try:
            parsed = json.loads(chunk_text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            fenced_candidates.append(parsed)
    if len(fenced_candidates) == 1:
        parse_attempts.append(
            {
                "parser": "fenced_json",
                "status": "recovered",
                "parse_contract_status": "fenced_json_recovered",
            }
        )
        return fenced_candidates[0], {
            "parse_contract_status": "fenced_json_recovered",
            "parse_recovery_used": True,
            "parse_recovery_strategy": "fenced_json",
            "parse_recovery_ambiguous": False,
            "parse_attempts": parse_attempts,
            "raw_content_excerpt": raw_text[:1200],
            "finish_reason": None,
        }
    if len(fenced_candidates) > 1:
        raise BuilderSpaceParseError(
            "BuilderSpace fenced JSON recovery is ambiguous.",
            failure_family="malformed_json",
            failing_component="builderspace_adapter.extract_json_object",
            observed_value=raw_text,
            raw_content=raw_text,
            parse_attempts=parse_attempts,
            parse_recovery_used=True,
            parse_recovery_strategy="fenced_json",
            parse_recovery_ambiguous=True,
        )

    open_fenced_candidates = extract_open_fenced_json_candidates(raw_text)
    if len(open_fenced_candidates) == 1:
        parse_attempts.append(
            {
                "parser": "open_fenced_json_marker",
                "status": "recovered",
                "parse_contract_status": "open_fenced_json_recovered",
            }
        )
        return open_fenced_candidates[0], {
            "parse_contract_status": "open_fenced_json_recovered",
            "parse_recovery_used": True,
            "parse_recovery_strategy": "open_fenced_json_marker",
            "parse_recovery_ambiguous": False,
            "parse_attempts": parse_attempts,
            "raw_content_excerpt": raw_text[:1200],
            "finish_reason": None,
        }
    if len(open_fenced_candidates) > 1:
        raise BuilderSpaceParseError(
            "BuilderSpace open fenced JSON recovery is ambiguous.",
            failure_family="malformed_json",
            failing_component="builderspace_adapter.extract_json_object",
            observed_value=raw_text,
            raw_content=raw_text,
            parse_attempts=parse_attempts,
            parse_recovery_used=True,
            parse_recovery_strategy="open_fenced_json_marker",
            parse_recovery_ambiguous=True,
        )

    candidates = extract_json_candidates(raw_text)
    if len(candidates) == 1:
        parse_attempts.append(
            {
                "parser": "last_valid_json_object",
                "status": "recovered",
                "parse_contract_status": "prose_json_recovered",
            }
        )
        return candidates[0], {
            "parse_contract_status": "prose_json_recovered",
            "parse_recovery_used": True,
            "parse_recovery_strategy": "last_valid_json_object",
            "parse_recovery_ambiguous": False,
            "parse_attempts": parse_attempts,
            "raw_content_excerpt": raw_text[:1200],
            "finish_reason": None,
        }
    if len(candidates) > 1:
        raise BuilderSpaceParseError(
            "BuilderSpace prose JSON recovery is ambiguous.",
            failure_family="malformed_json",
            failing_component="builderspace_adapter.extract_json_object",
            observed_value=raw_text,
            raw_content=raw_text,
            parse_attempts=parse_attempts,
            parse_recovery_used=True,
            parse_recovery_strategy="last_valid_json_object",
            parse_recovery_ambiguous=True,
        )
    raise BuilderSpaceParseError(
        "BuilderSpace did not return JSON.",
        failure_family="non_json_model_output",
        failing_component="builderspace_adapter.extract_json_object",
        observed_value=raw_text,
        raw_content=raw_text,
        parse_attempts=parse_attempts,
    )


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


def extract_open_fenced_json_candidates(content: str) -> list[dict[str, Any]]:
    marker = re.compile(r"```(?:json)?\s*", flags=re.IGNORECASE)
    matches = list(marker.finditer(content))
    if len(matches) != 1:
        return []
    suffix = content[matches[0].end() :]
    if "```" in suffix:
        return []
    return extract_json_candidates(suffix)


def observed_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, tuple):
        return "tuple"
    return "unknown"


def value_excerpt(value: Any, *, max_chars: int = 1200) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    rendered = value if isinstance(value, str) else json.dumps(jsonable(value), ensure_ascii=False, default=str)
    if len(rendered) <= max_chars:
        return rendered, False
    return rendered[:max_chars], True


def jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value
