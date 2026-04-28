from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BANNED_SUBJECTS = {
    "fix",
    "update",
    "misc",
    "wip",
    "tmp",
    "fix typo",
}
CORE_LOGIC_PREFIXES = (
    "app/intake/",
    "app/nutrition/",
    "app/budget/",
    "app/body/",
    "app/runtime/",
)
CORE_LOGIC_EXACT = {
    "app/routes.py",
    "app/schemas.py",
}
ALLOWED_SCOPE_EXCEPTIONS = {
    "freeze-allow",
    "cross-layer",
    "dependency-update",
    "test-refactor",
    "large-refactor",
    "wide-scope",
}


@dataclass(frozen=True)
class CommitRecord:
    revision: str
    message: str
    changed_paths: tuple[str, ...]


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def subject_of(message: str) -> str:
    for line in message.splitlines():
        if line.strip():
            return line.strip()
    return ""


def body_of(message: str) -> str:
    lines = message.splitlines()
    if not lines:
        return ""
    return "\n".join(lines[1:]).strip()


def parse_scope_exceptions(message: str) -> set[str]:
    labels: set[str] = set()
    for raw_line in message.splitlines():
        line = raw_line.strip()
        if not line.lower().startswith("scope-exception:"):
            continue
        _, value = line.split(":", 1)
        for token in value.split(","):
            label = token.strip()
            if label:
                labels.add(label)
    return labels


def touched_core_logic(paths: tuple[str, ...]) -> bool:
    for path in paths:
        if path in CORE_LOGIC_EXACT or path.startswith(CORE_LOGIC_PREFIXES):
            return True
    return False


def get_staged_paths() -> tuple[str, ...]:
    result = run_git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return tuple(normalize_path(line) for line in result.stdout.splitlines() if line.strip())


def get_changed_paths_for_commit(revision: str) -> tuple[str, ...]:
    result = run_git("diff-tree", "--no-commit-id", "--name-only", "-r", revision)
    return tuple(normalize_path(line) for line in result.stdout.splitlines() if line.strip())


def is_all_zero_sha(value: str) -> bool:
    stripped = value.strip()
    return bool(stripped) and set(stripped) == {"0"}


def get_commit_records_for_range(base: str, head: str) -> list[CommitRecord]:
    if is_all_zero_sha(base):
        revisions = [head]
    else:
        rev_result = run_git("rev-list", "--no-merges", "--reverse", f"{base}..{head}")
        revisions = [line.strip() for line in rev_result.stdout.splitlines() if line.strip()]
        if not revisions:
            revisions = [head]
    records: list[CommitRecord] = []
    for revision in revisions:
        message = run_git("log", "-1", "--format=%B", revision).stdout
        changed_paths = get_changed_paths_for_commit(revision)
        records.append(CommitRecord(revision, message, changed_paths))
    return records


def validate_message(record: CommitRecord) -> list[str]:
    issues: list[str] = []
    subject = subject_of(record.message)
    subject_lower = subject.strip().lower()
    body = body_of(record.message)
    exceptions = parse_scope_exceptions(record.message)

    invalid = sorted(label for label in exceptions if label not in ALLOWED_SCOPE_EXCEPTIONS)
    if invalid:
        issues.append(f"{record.revision}: unsupported Scope-Exception label(s): {', '.join(invalid)}")

    if not subject:
        issues.append(f"{record.revision}: missing commit subject")
    elif subject_lower in BANNED_SUBJECTS:
        issues.append(f"{record.revision}: banned vague subject '{subject}'")
    elif len(subject.split()) < 3:
        issues.append(f"{record.revision}: subject should express slice intent, not a generic action")

    if not re.search(r"(?im)^Test Run:\s+.+$", body):
        issues.append(f"{record.revision}: missing 'Test Run:' line")

    if touched_core_logic(record.changed_paths):
        if not re.search(r"(?im)^(Reality|Drift):\s+.+$", body):
            issues.append(f"{record.revision}: core logic commit is missing 'Reality:' or 'Drift:'")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("commit_msg_file", nargs="?")
    group.add_argument("--range", nargs=2, metavar=("BASE", "HEAD"))
    args = parser.parse_args()

    if args.range:
        records = get_commit_records_for_range(args.range[0], args.range[1])
    else:
        message = Path(args.commit_msg_file).read_text(encoding="utf-8")
        records = [
            CommitRecord(
                revision="STAGED",
                message=message,
                changed_paths=get_staged_paths(),
            )
        ]

    issues: list[str] = []
    for record in records:
        issues.extend(validate_message(record))

    if issues:
        print("Commit format check failed.")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Commit format check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
