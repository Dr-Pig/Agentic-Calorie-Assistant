from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MOJIBAKE_CHARS = set("?賹??餌?Ｘ???砲撖?")


def enforce_file_backed_audit_input(*, audit_name: str) -> None:
    """Block unsafe Windows piped stdin for formal audit runners."""
    if not sys.stdin.isatty() and os.name == "nt":
        print(
            f"[FAIL] {audit_name}: piped stdin detected in Windows environment.",
            file=sys.stderr,
        )
        print(
            "Formal audits must use checked-in file-backed fixtures, not inline PowerShell pipe input.",
            file=sys.stderr,
        )
        print(
            "Keep Chinese inputs in UTF-8 files and use the runner's fixture/case arguments.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _looks_mojibake(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    cjk_chars = sum(1 for ch in value if "\u4e00" <= ch <= "\u9fff")
    ascii_letters = sum(1 for ch in value if ("a" <= ch.lower() <= "z"))
    suspicious = sum(1 for ch in value if ch in MOJIBAKE_CHARS)
    pua_chars = sum(1 for ch in value if "\ue000" <= ch <= "\uf8ff")
    question_marks = value.count("?")
    if cjk_chars >= 2:
        return pua_chars > 0 or question_marks >= 2
    if ascii_letters >= 4 and suspicious == 0:
        return pua_chars > 0 or question_marks >= 2
    if pua_chars > 0:
        return True
    if question_marks >= 2:
        return True
    return suspicious >= max(1, len(value) // 8)


def _iter_strings(node: Any, *, path: str = "$") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(node, str):
        found.append((path, node))
        return found
    if isinstance(node, list):
        for idx, item in enumerate(node):
            found.extend(_iter_strings(item, path=f"{path}[{idx}]"))
        return found
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(_iter_strings(value, path=f"{path}.{key}"))
    return found


def load_json_audit_fixture(*, path: Path, audit_name: str) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        print(f"[FAIL] {audit_name}: fixture is not valid UTF-8: {path}", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"[FAIL] {audit_name}: fixture is not valid JSON: {path}", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

    violations: list[str] = []
    for json_path, value in _iter_strings(payload):
        if _looks_mojibake(value):
            violations.append(f"{json_path}: {value}")

    if violations:
        print(f"[FAIL] {audit_name}: fixture contains mojibake-risk text: {path}", file=sys.stderr)
        for violation in violations[:20]:
            print(f"  - {violation}", file=sys.stderr)
        print("Formal audit fixtures must be readable UTF-8 content, not shell-corrupted text.", file=sys.stderr)
        raise SystemExit(1)

    return payload
