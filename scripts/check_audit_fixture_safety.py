from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_io_guard import load_json_audit_fixture


REGISTRY_PATH = ROOT / "docs" / "quality" / "AUDIT_FIXTURE_REGISTRY.json"


def main() -> int:
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"[FAIL] missing audit fixture registry: {REGISTRY_PATH}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"[FAIL] invalid audit fixture registry JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(registry, list) or not registry:
        print("[FAIL] audit fixture registry must be a non-empty JSON list", file=sys.stderr)
        return 1

    for entry in registry:
        if not isinstance(entry, dict):
            print("[FAIL] audit fixture registry entries must be objects", file=sys.stderr)
            return 1
        rel_path = entry.get("path")
        fixture_type = entry.get("type")
        if not isinstance(rel_path, str) or not rel_path:
            print("[FAIL] audit fixture registry entry missing string field 'path'", file=sys.stderr)
            return 1
        if fixture_type != "json":
            print(f"[FAIL] unsupported audit fixture type for {rel_path}: {fixture_type}", file=sys.stderr)
            return 1

        path = ROOT / rel_path
        if not path.exists():
            print(f"[FAIL] missing audit fixture: {rel_path}", file=sys.stderr)
            return 1

        load_json_audit_fixture(path=path, audit_name="audit_fixture_safety")

    print("[OK] audit fixture safety check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
