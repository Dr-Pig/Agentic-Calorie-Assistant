from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

HIGH_RISK_TEXT_KEYS = {
    "title",
    "utterance",
    "pending_question",
    "followup_question",
    "note",
    "reply_text",
    "label",
    "reason",
    "summary",
    "question",
}

COMMON_MOJIBAKE_MARKERS = (
    "??",
    "銝",
    "撠",
    "暺",
    "瘝",
    "蝛",
    "瑚",
    "皛",
    "麾",
    "臬",
    "拚",
    "",
    "",
    "",
    "",
)


@dataclass(frozen=True)
class GuardIssue:
    path: Path
    line_no: int
    reason: str
    line: str


def load_registry(path: Path) -> list[dict[str, object]]:
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing guard registry: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid guard registry JSON: {exc}") from exc
    if not isinstance(registry, list) or not registry:
        raise RuntimeError("guard registry must be a non-empty JSON list")
    return registry


def load_allowlist(path: Path) -> set[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid guard allowlist JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise RuntimeError("guard allowlist must be a JSON list")
    return {str(entry) for entry in payload if isinstance(entry, str)}


def iter_guarded_files(*, registry_path: Path) -> list[Path]:
    files: list[Path] = []
    for entry in load_registry(registry_path):
        if not isinstance(entry, dict):
            raise RuntimeError("guard registry entries must be objects")
        explicit_paths = entry.get("paths")
        if explicit_paths is not None:
            if not isinstance(explicit_paths, list) or not explicit_paths:
                raise RuntimeError("guard registry field 'paths' must be a non-empty list when present")
            for rel_path in explicit_paths:
                if not isinstance(rel_path, str) or not rel_path:
                    raise RuntimeError("guard registry explicit paths must be non-empty strings")
                candidate = ROOT / rel_path
                if not candidate.exists() or not candidate.is_file():
                    raise RuntimeError(f"guard registry explicit path not found: {candidate}")
                files.append(candidate)
            continue
        rel_root = entry.get("root")
        suffixes = entry.get("suffixes")
        if not isinstance(rel_root, str) or not rel_root:
            raise RuntimeError("guard registry entry missing string field 'root'")
        if not isinstance(suffixes, list) or not suffixes:
            raise RuntimeError(f"guard registry entry {rel_root} missing non-empty 'suffixes'")
        root = ROOT / rel_root
        if not root.exists():
            raise RuntimeError(f"guard registry root not found: {root}")
        allowed_suffixes = {str(value) for value in suffixes if isinstance(value, str)}
        for candidate in root.rglob("*"):
            if candidate.is_file() and candidate.suffix in allowed_suffixes:
                files.append(candidate)
    return sorted(set(files))


def _contains_private_use(text: str) -> bool:
    for char in text:
        code = ord(char)
        if 0xE000 <= code <= 0xF8FF or 0xF0000 <= code <= 0xFFFFD or 0x100000 <= code <= 0x10FFFD:
            return True
    return False


def _contains_forbidden_control(text: str) -> bool:
    for char in text:
        code = ord(char)
        if code in (0x09, 0x0A, 0x0D):
            continue
        if code < 0x20 or 0x7F <= code <= 0x9F:
            return True
    return False


def looks_like_mojibake(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    if "\uFFFD" in value or _contains_private_use(value) or _contains_forbidden_control(value):
        return True
    has_non_ascii = any(ord(ch) > 127 for ch in value)
    if value.count("?") >= 2 and has_non_ascii:
        return True
    marker_hits = sum(1 for marker in COMMON_MOJIBAKE_MARKERS if marker in value)
    if marker_hits >= 2:
        return True
    if marker_hits >= 1 and len(value) <= 40 and has_non_ascii:
        return True
    return False


def find_issues_in_text(path: Path, text: str) -> list[GuardIssue]:
    issues: list[GuardIssue] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "\uFFFD" in line:
            issues.append(GuardIssue(path=path, line_no=line_no, reason="replacement_character", line=line))
        if _contains_private_use(line):
            issues.append(GuardIssue(path=path, line_no=line_no, reason="private_use_character", line=line))
        if _contains_forbidden_control(line):
            issues.append(GuardIssue(path=path, line_no=line_no, reason="forbidden_control_character", line=line))
        if looks_like_mojibake(line):
            issues.append(GuardIssue(path=path, line_no=line_no, reason="mojibake_pattern", line=line))
    return issues


def _iter_json_strings(node: Any, *, path: str = "$", parent_key: str | None = None) -> list[tuple[str, str, str | None]]:
    found: list[tuple[str, str, str | None]] = []
    if isinstance(node, str):
        found.append((path, node, parent_key))
        return found
    if isinstance(node, list):
        for idx, item in enumerate(node):
            found.extend(_iter_json_strings(item, path=f"{path}[{idx}]", parent_key=parent_key))
        return found
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(_iter_json_strings(value, path=f"{path}.{key}", parent_key=str(key)))
    return found


def find_issues_in_json_payload(path: Path, payload: Any) -> list[GuardIssue]:
    issues: list[GuardIssue] = []
    for json_path, value, parent_key in _iter_json_strings(payload):
        if not isinstance(value, str):
            continue
        if parent_key in HIGH_RISK_TEXT_KEYS and looks_like_mojibake(value):
            issues.append(GuardIssue(path=path, line_no=0, reason="fixture_text_corruption", line=f"{json_path}: {value}"))
        elif "\uFFFD" in value:
            issues.append(GuardIssue(path=path, line_no=0, reason="replacement_character", line=f"{json_path}: {value}"))
        elif _contains_private_use(value):
            issues.append(GuardIssue(path=path, line_no=0, reason="private_use_character", line=f"{json_path}: {value}"))
        elif _contains_forbidden_control(value):
            issues.append(GuardIssue(path=path, line_no=0, reason="forbidden_control_character", line=f"{json_path}: {value}"))
    return issues
