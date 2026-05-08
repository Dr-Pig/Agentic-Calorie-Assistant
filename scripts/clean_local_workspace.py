from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

ROOT_DISPOSABLE_DIRS = {
    ".codex_tmp",
    ".import_linter_cache",
    ".pytest_cache",
    ".ruff_cache",
    "runtime",
}
ROOT_DISPOSABLE_PREFIXES = (
    ".pytest_tmp",
    "tmp_pytest",
)
OPTIONAL_LOCAL_TOOLING_DIRS = {
    ".devcontainer",
}
RECURSIVE_DISPOSABLE_DIR_NAMES = {
    "__pycache__",
}
PROTECTED_ROOT_DIRS = {
    ".git",
    "artifacts",
    "docs",
    "workspace_data",
}


def _is_inside_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _repo_relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _is_disposable_root_dir(path: Path, *, include_local_tooling: bool) -> bool:
    name = path.name
    if name in ROOT_DISPOSABLE_DIRS:
        return True
    if include_local_tooling and name in OPTIONAL_LOCAL_TOOLING_DIRS:
        return True
    return any(name.startswith(prefix) for prefix in ROOT_DISPOSABLE_PREFIXES)


def plan_cleanup(root: Path, *, include_local_tooling: bool = False) -> list[Path]:
    root = root.resolve()
    candidates: list[Path] = []

    for child in root.iterdir():
        if not child.is_dir() or child.is_symlink():
            continue
        if child.name in PROTECTED_ROOT_DIRS:
            continue
        if _is_disposable_root_dir(child, include_local_tooling=include_local_tooling):
            candidates.append(child)

    for child in root.rglob("*"):
        if not child.is_dir() or child.is_symlink():
            continue
        if child.name not in RECURSIVE_DISPOSABLE_DIR_NAMES:
            continue
        if not _is_inside_root(child, root):
            continue
        parts = child.resolve().relative_to(root).parts
        if parts and parts[0] in PROTECTED_ROOT_DIRS:
            continue
        candidates.append(child)

    deduped = sorted({candidate.resolve() for candidate in candidates}, key=lambda item: item.as_posix())
    return deduped


def clean_workspace(
    root: Path,
    *,
    dry_run: bool = False,
    include_local_tooling: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    removed: list[str] = []
    planned: list[str] = []
    skipped: list[dict[str, str]] = []

    for candidate in plan_cleanup(root, include_local_tooling=include_local_tooling):
        relative = _repo_relative(candidate, root)
        planned.append(relative)
        if not _is_inside_root(candidate, root):
            skipped.append({"path": str(candidate), "reason": "outside_repo_root"})
            continue
        if candidate.is_symlink():
            skipped.append({"path": relative, "reason": "symlink_not_removed"})
            continue
        if dry_run:
            continue
        shutil.rmtree(candidate)
        removed.append(relative)

    return {
        "root": str(root),
        "dry_run": dry_run,
        "include_local_tooling": include_local_tooling,
        "planned_count": len(planned),
        "removed_count": len(removed),
        "planned": planned,
        "removed": removed,
        "skipped": skipped,
        "protected_roots": sorted(PROTECTED_ROOT_DIRS),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean disposable local repo scratch directories.")
    parser.add_argument("--root", default=str(REPO_ROOT), help="Repo root to clean. Defaults to this checkout.")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be removed without deleting.")
    parser.add_argument(
        "--include-local-tooling",
        action="store_true",
        help="Also remove ignored local tooling directories such as .devcontainer.",
    )
    args = parser.parse_args(argv)

    report = clean_workspace(
        Path(args.root),
        dry_run=args.dry_run,
        include_local_tooling=args.include_local_tooling,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
