from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.text_surface_guard import (
    GuardIssue,
    find_issues_in_json_payload,
    find_issues_in_text,
    iter_guarded_files,
    load_allowlist,
)
REGISTRY_PATH = ROOT / "docs" / "quality" / "OFFICIAL_TEXT_SURFACE_GUARD_REGISTRY.json"
ALLOWLIST_PATH = ROOT / "docs" / "quality" / "OFFICIAL_TEXT_SURFACE_GUARD_ALLOWLIST.json"


def _scan_path(path: Path) -> list[GuardIssue]:
    text = path.read_text(encoding="utf-8")
    issues = find_issues_in_text(path, text)
    if path.suffix == ".json":
        payload = json.loads(text)
        issues.extend(find_issues_in_json_payload(path, payload))
    return issues


def main() -> int:
    issues: list[GuardIssue] = []
    allowlist = load_allowlist(ALLOWLIST_PATH)
    for path in iter_guarded_files(registry_path=REGISTRY_PATH):
        rel_path = path.relative_to(ROOT).as_posix()
        if rel_path in allowlist:
            continue
        issues.extend(_scan_path(path))

    if issues:
        print("[FAIL] official text-surface mojibake guard found suspicious text:", file=sys.stderr)
        for issue in issues[:200]:
            rel_path = issue.path.relative_to(ROOT)
            location = issue.line_no if issue.line_no else "field"
            print(f"- {rel_path}:{location} [{issue.reason}] {issue.line.strip()}", file=sys.stderr)
        return 1

    print("[OK] official text-surface mojibake guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
