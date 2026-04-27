from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "active_code_policy.jsonc"


def load_active_code_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def normalize_repo_path(path: Path | str) -> str:
    if isinstance(path, Path):
        try:
            path = path.relative_to(ROOT).as_posix()
        except ValueError:
            path = path.as_posix()
    return str(path).replace("\\", "/")


def iter_active_python_files(policy: dict[str, Any]) -> list[Path]:
    root = ROOT / policy["active_code"]["root"]
    excluded = tuple(policy["active_code"].get("excluded_globs", ()))
    files: list[Path] = []
    for path in root.rglob("*.py"):
        normalized = normalize_repo_path(path)
        if any(fnmatch.fnmatch(normalized, pattern) for pattern in excluded):
            continue
        files.append(path)
    return sorted(files)


def category_for_repo_path(repo_path: str, policy: dict[str, Any]) -> str | None:
    for rule in policy["category_rules"]:
        if fnmatch.fnmatch(repo_path, rule["pattern"]):
            return str(rule["category"])
    return None


def effective_cap_for_repo_path(repo_path: str, policy: dict[str, Any]) -> int | None:
    override = policy.get("transition_overrides", {}).get(repo_path)
    if override is not None:
        return int(override)
    category = category_for_repo_path(repo_path, policy)
    if category is None:
        return None
    return int(policy["category_caps"][category])


def target_cap_for_repo_path(repo_path: str, policy: dict[str, Any]) -> int | None:
    category = category_for_repo_path(repo_path, policy)
    if category is None:
        return None
    return int(policy["category_caps"][category])


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").split("\n"))


def focus_modules(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["path"]: entry for entry in policy.get("focus_modules", [])}


def top_level_domain(path: Path) -> str:
    rel = normalize_repo_path(path).split("/")
    return rel[1] if len(rel) > 1 else ""
