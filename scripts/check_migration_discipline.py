from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATHS = {
    "app/models.py",
}
MIGRATION_PREFIX = "alembic/versions/"


def run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def changed_paths_from_range(diff_range: str) -> list[str]:
    output = run_git("diff", "--name-only", "--diff-filter=ACMR", diff_range)
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def staged_paths() -> list[str]:
    output = run_git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def detect_changed_paths() -> tuple[list[str], str]:
    event_name = os.getenv("GITHUB_EVENT_NAME", "").strip()
    base_ref = os.getenv("GITHUB_BASE_REF", "").strip()
    before_sha = os.getenv("GITHUB_EVENT_BEFORE", "").strip()

    if event_name == "pull_request" and base_ref:
        merge_base = run_git("merge-base", "HEAD", f"origin/{base_ref}")
        return changed_paths_from_range(f"{merge_base}..HEAD"), f"merge-base origin/{base_ref}"

    if before_sha and before_sha != ("0" * 40):
        return changed_paths_from_range(f"{before_sha}..HEAD"), before_sha

    paths = staged_paths()
    if paths:
        return paths, "staged-index"

    return [], "none"


def main() -> int:
    changed_paths, source = detect_changed_paths()

    if not changed_paths:
        print("Migration discipline check passed. No tracked schema-sensitive changes detected.")
        return 0

    changed_schema_paths = sorted(path for path in changed_paths if path in SCHEMA_PATHS)
    changed_migration_paths = sorted(path for path in changed_paths if path.startswith(MIGRATION_PREFIX))

    print(f"Migration discipline diff source: {source}")
    if changed_schema_paths:
        print("Schema-sensitive changes:")
        for path in changed_schema_paths:
            print(f"- {path}")

    if changed_migration_paths:
        print("Migration files in diff:")
        for path in changed_migration_paths:
            print(f"- {path}")

    if changed_schema_paths and not changed_migration_paths:
        print(
            "Migration discipline violation: schema-sensitive ORM files changed without a matching Alembic migration under alembic/versions/."
        )
        print("Add a migration file before merging schema changes.")
        return 1

    print("Migration discipline check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
