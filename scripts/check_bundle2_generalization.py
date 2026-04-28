from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "app" / "runtime" / "agent" / "manager.py",
    ROOT / "app" / "runtime" / "agent" / "manager_fallback_policy.py",
    ROOT / "app" / "intake" / "application" / "intake_execution_orchestrator.py",
    ROOT / "app" / "intake" / "application" / "manager_tools.py",
    ROOT / "scripts" / "run_v2_bundle2_live_eval.py",
]

BANNED_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"turn1_followup_guard", "case_specific_followup_guard"),
    (r"case[_-]?id\s*==", "runtime_case_id_branch"),
    (r"generic_milk_tea_followup_required", "legacy_case_specific_guard_family"),
)


def main() -> int:
    issues: list[str] = []
    for path in TARGETS:
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern, label in BANNED_PATTERNS:
            for match in re.finditer(pattern, text):
                line = text.count("\n", 0, match.start()) + 1
                issues.append(f"{path}:{line}:{label}")
    if issues:
        for issue in issues:
            print(issue)
        return 1
    print("bundle2_generalization: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
