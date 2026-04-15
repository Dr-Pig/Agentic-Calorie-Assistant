from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.text_surface_guard import GuardIssue, find_issues_in_text, iter_guarded_files, load_allowlist

REGISTRY_PATH = ROOT / "docs" / "quality" / "USER_FACING_STRING_GUARD_REGISTRY.json"
ALLOWLIST_PATH = ROOT / "docs" / "quality" / "USER_FACING_STRING_GUARD_ALLOWLIST.json"


def main() -> int:
    issues: list[GuardIssue] = []
    allowlist = load_allowlist(ALLOWLIST_PATH)
    for path in iter_guarded_files(registry_path=REGISTRY_PATH):
        rel_path = path.relative_to(ROOT).as_posix()
        if rel_path in allowlist:
            continue
        text = path.read_text(encoding="utf-8")
        issues.extend(find_issues_in_text(path, text))

    if issues:
        print("[FAIL] user-facing mojibake guard found suspicious text:", file=sys.stderr)
        for issue in issues:
            rel_path = issue.path.relative_to(ROOT)
            print(f"- {rel_path}:{issue.line_no} [{issue.reason}] {issue.line.strip()}", file=sys.stderr)
        return 1

    print("[OK] user-facing mojibake guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
