from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from scripts.text_surface_guard import find_issues_in_json_payload

ROOT = Path(__file__).resolve().parents[1]


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

    violations = find_issues_in_json_payload(path, payload)
    if violations:
        print(f"[FAIL] {audit_name}: fixture contains mojibake-risk text: {path}", file=sys.stderr)
        for violation in violations[:20]:
            print(f"  - [{violation.reason}] {violation.line}", file=sys.stderr)
        print("Formal audit fixtures must be readable UTF-8 content, not shell-corrupted text.", file=sys.stderr)
        raise SystemExit(1)

    return payload
