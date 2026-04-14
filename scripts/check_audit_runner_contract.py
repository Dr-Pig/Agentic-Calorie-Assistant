from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs" / "quality" / "AUDIT_RUNNER_REGISTRY.json"


def load_runner_registry() -> list[dict[str, str]]:
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"missing audit runner registry: {REGISTRY_PATH}")

    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("audit runner registry must be a non-empty JSON list")

    normalized: list[dict[str, str]] = []
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("audit runner registry entries must be objects")
        path = entry.get("path")
        audit_name = entry.get("audit_name")
        if not isinstance(path, str) or not path:
            raise ValueError("audit runner registry entry missing string field 'path'")
        if not isinstance(audit_name, str) or not audit_name:
            raise ValueError("audit runner registry entry missing string field 'audit_name'")
        normalized.append({"path": path, "audit_name": audit_name})
    return normalized


def main() -> int:
    violations: list[str] = []
    try:
        runner_registry = load_runner_registry()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"[FAIL] audit runner registry invalid: {exc}", file=sys.stderr)
        return 1

    for entry in runner_registry:
        relative_path = entry["path"]
        required_snippets = [
            "from scripts.audit_io_guard import enforce_file_backed_audit_input",
            f'enforce_file_backed_audit_input(audit_name="{entry["audit_name"]}")',
        ]
        path = ROOT / relative_path
        if not path.exists():
            violations.append(f"missing audit runner: {relative_path}")
            continue

        text = path.read_text(encoding="utf-8")
        for snippet in required_snippets:
            if snippet not in text:
                violations.append(f"{relative_path} missing required contract snippet: {snippet}")

    if violations:
        print("[FAIL] audit runner contract check failed", file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        print(
            "Formal audit runners listed in the audit runner registry must import the shared audit_io_guard and enforce file-backed input.",
            file=sys.stderr,
        )
        return 1

    print("[OK] audit runner contract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
