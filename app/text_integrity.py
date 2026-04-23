from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import unicodedata


CORRUPTION_MARKERS = ("????", "\ufffd")
SHELL_FAILURE_MARKERS = ("shell timeout", "command timed out")


@dataclass(frozen=True)
class TextCorruptionFinding:
    path: str
    reason: str
    sample: str


def is_corrupted_text(value: str | None) -> bool:
    text = str(value or "")
    if not text:
        return False
    lowered = text.lower()
    return (
        any(marker in text for marker in CORRUPTION_MARKERS)
        or any(marker in lowered for marker in SHELL_FAILURE_MARKERS)
        or _contains_private_use_character(text)
    )


def _contains_private_use_character(text: str) -> bool:
    return any(unicodedata.category(char) == "Co" for char in text)


def find_text_corruption(value: Any, *, path: str = "$") -> list[TextCorruptionFinding]:
    findings: list[TextCorruptionFinding] = []
    if isinstance(value, dict):
        for key, item in value.items():
            findings.extend(find_text_corruption(item, path=f"{path}.{key}"))
        return findings
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            findings.extend(find_text_corruption(item, path=f"{path}[{index}]"))
        return findings
    if isinstance(value, str) and is_corrupted_text(value):
        lowered = value.lower()
        reason = "mangled_text_marker"
        if any(marker in lowered for marker in SHELL_FAILURE_MARKERS):
            reason = "shell_timeout_marker"
        elif _contains_private_use_character(value):
            reason = "private_use_mojibake_marker"
        findings.append(
            TextCorruptionFinding(
                path=path,
                reason=reason,
                sample=value[:160],
            )
        )
    return findings


def sanitize_text_value(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text or is_corrupted_text(text):
        return None
    return text


def sanitize_text_structure(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            sanitized = sanitize_text_structure(item)
            if sanitized is None:
                continue
            if sanitized == [] or sanitized == {}:
                cleaned[str(key)] = sanitized
                continue
            cleaned[str(key)] = sanitized
        return cleaned
    if isinstance(value, list):
        cleaned_list = [sanitize_text_structure(item) for item in value]
        return [item for item in cleaned_list if item is not None]
    if isinstance(value, tuple):
        cleaned_list = [sanitize_text_structure(item) for item in value]
        return tuple(item for item in cleaned_list if item is not None)
    if isinstance(value, str):
        return sanitize_text_value(value)
    return value


def corruption_summary(findings: list[TextCorruptionFinding]) -> list[dict[str, str]]:
    return [
        {
            "path": finding.path,
            "reason": finding.reason,
            "sample": finding.sample,
        }
        for finding in findings
    ]
