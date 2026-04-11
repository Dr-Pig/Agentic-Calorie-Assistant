from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE_GROWTH_FILES = {
    "app/application/evidence_assembly.py",
    "app/application/context_assembly.py",
    "app/agent/knowledge_packets.py",
}
HIGH_RISK_TRUNCATION_FILES = FREEZE_GROWTH_FILES | {
    "app/usecases/text_meal.py",
    "app/routes.py",
    "app/schemas.py",
}
DEPENDENCY_FILES = {
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
}
CORE_APP_PREFIXES = ("app/",)
TEST_PREFIX = "tests/"
CORE_LOGIC_PREFIXES = (
    "app/application/",
    "app/domain/",
    "app/usecases/",
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
MAX_CHANGED_FILES = 5
FREEZE_GROWTH_MAX_ADDITIONS = 5
TEST_DELETE_LINES_THRESHOLD = 20
TEST_DELETE_RATIO_THRESHOLD = 0.40
ANTI_TRUNCATION_RATIO_THRESHOLD = 0.30


class CheckFailure(Exception):
    pass


@dataclass(frozen=True)
class FileStats:
    path: str
    additions: int
    deletions: int

    @property
    def touched_lines(self) -> int:
        return self.additions + self.deletions


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=check,
    )


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def parse_exception_labels(text: str) -> set[str]:
    labels: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.lower().startswith("scope-exception:"):
            continue
        _, value = line.split(":", 1)
        for token in value.split(","):
            label = token.strip()
            if label:
                labels.add(label)
    return labels


def get_env_exceptions() -> set[str]:
    labels = parse_exception_labels(os.getenv("LHC_SCOPE_EXCEPTIONS", ""))
    invalid = sorted(label for label in labels if label not in ALLOWED_SCOPE_EXCEPTIONS)
    if invalid:
        raise CheckFailure(
            f"unsupported scope exceptions in LHC_SCOPE_EXCEPTIONS: {', '.join(invalid)}"
        )
    return labels


def get_commit_range_exceptions(base: str, head: str) -> set[str]:
    if is_all_zero_sha(base):
        return set()
    try:
        result = run_git("log", "--format=%B%x00", f"{base}..{head}")
    except subprocess.CalledProcessError as exc:
        raise CheckFailure(f"failed to read commit messages for range {base}..{head}: {exc.stderr.strip()}") from exc
    labels = parse_exception_labels(result.stdout)
    invalid = sorted(label for label in labels if label not in ALLOWED_SCOPE_EXCEPTIONS)
    if invalid:
        raise CheckFailure(
            f"unsupported scope exceptions in commit range: {', '.join(invalid)}"
        )
    return labels


def is_all_zero_sha(value: str) -> bool:
    stripped = value.strip()
    return bool(stripped) and set(stripped) == {"0"}


def get_diff_name_only(mode: str, base: str | None = None, head: str | None = None) -> list[str]:
    if mode == "staged":
        result = run_git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    elif mode == "range":
        assert base is not None and head is not None
        if is_all_zero_sha(base):
            result = run_git("show", "--pretty=", "--name-only", "--diff-filter=ACMR", head)
        else:
            result = run_git("diff", "--name-only", "--diff-filter=ACMR", base, head)
    else:
        raise ValueError(f"unsupported mode {mode}")
    return [normalize_path(line) for line in result.stdout.splitlines() if line.strip()]


def get_diff_numstat(mode: str, base: str | None = None, head: str | None = None) -> dict[str, FileStats]:
    if mode == "staged":
        result = run_git("diff", "--cached", "--numstat", "--diff-filter=ACMR")
    elif mode == "range":
        assert base is not None and head is not None
        if is_all_zero_sha(base):
            result = run_git("show", "--numstat", "--format=", "--diff-filter=ACMR", head)
        else:
            result = run_git("diff", "--numstat", "--diff-filter=ACMR", base, head)
    else:
        raise ValueError(f"unsupported mode {mode}")

    stats: dict[str, FileStats] = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        add_raw, del_raw, path = parts
        if add_raw == "-" or del_raw == "-":
            additions = deletions = 0
        else:
            additions = int(add_raw)
            deletions = int(del_raw)
        norm_path = normalize_path(path)
        stats[norm_path] = FileStats(norm_path, additions, deletions)
    return stats


def get_files_from_stdin() -> list[str]:
    return [normalize_path(line) for line in sys.stdin.read().splitlines() if line.strip()]


def get_blob_line_count(rev: str, path: str) -> int | None:
    spec = f"{rev}:{path}" if rev else f":{path}"
    result = subprocess.run(
        ["git", "show", spec],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return len(result.stdout.splitlines())


def get_preimage_line_count(mode: str, path: str, base: str | None = None) -> int | None:
    if mode == "staged":
        return get_blob_line_count("HEAD", path)
    if mode == "range":
        if base and not is_all_zero_sha(base):
            return get_blob_line_count(base, path)
        return None
    return None


def has_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(prefix) for prefix in prefixes)


def path_is_core_logic(path: str) -> bool:
    return has_prefix(path, CORE_LOGIC_PREFIXES) or path in CORE_LOGIC_EXACT


def check_file_count(paths: list[str], exceptions: set[str]) -> list[str]:
    if len(paths) <= MAX_CHANGED_FILES or "wide-scope" in exceptions:
        return []
    return [f"changed tracked files = {len(paths)} exceeds max {MAX_CHANGED_FILES} without Scope-Exception: wide-scope"]


def check_freeze_growth(stats: dict[str, FileStats], exceptions: set[str]) -> list[str]:
    if "freeze-allow" in exceptions:
        return []
    issues: list[str] = []
    for path in sorted(FREEZE_GROWTH_FILES):
        stat = stats.get(path)
        if stat and stat.additions > FREEZE_GROWTH_MAX_ADDITIONS:
            issues.append(
                f"{path} adds {stat.additions} lines; freeze-growth cap is {FREEZE_GROWTH_MAX_ADDITIONS}"
            )
    return issues


def check_dependency_drift(paths: list[str], exceptions: set[str]) -> list[str]:
    if "dependency-update" in exceptions:
        return []
    touched = sorted(path for path in paths if path in DEPENDENCY_FILES)
    if not touched:
        return []
    return [f"dependency files changed without Scope-Exception: dependency-update ({', '.join(touched)})"]


def check_cross_layer(paths: list[str], exceptions: set[str]) -> list[str]:
    if "cross-layer" in exceptions:
        return []
    issues: list[str] = []
    has_routes = "app/routes.py" in paths
    has_app_application = any(path.startswith("app/application/") for path in paths)
    if has_routes and has_app_application:
        issues.append("app/routes.py and app/application/** changed together without Scope-Exception: cross-layer")

    has_web = any(path.startswith("app/web/") for path in paths)
    has_infra = any(path.startswith("app/infrastructure/") for path in paths)
    if has_web and has_infra:
        issues.append("app/web/** and app/infrastructure/** changed together without Scope-Exception: cross-layer")

    has_specs = any(path.startswith("docs/specs/") for path in paths)
    has_app_runtime = any(
        path.startswith("app/application/") or path.startswith("app/usecases/")
        for path in paths
    )
    if has_specs and has_app_runtime:
        issues.append("docs/specs/** and app/application/** or app/usecases/** changed together without Scope-Exception: cross-layer")
    return issues


def check_test_mutilation(stats: dict[str, FileStats], exceptions: set[str]) -> list[str]:
    if "test-refactor" in exceptions:
        return []
    touched_core = any(path.startswith(CORE_APP_PREFIXES) and not path.startswith(TEST_PREFIX) for path in stats)
    if not touched_core:
        return []
    issues: list[str] = []
    for path, stat in sorted(stats.items()):
        if not path.startswith(TEST_PREFIX):
            continue
        if stat.deletions <= 0:
            continue
        ratio = stat.deletions / max(stat.touched_lines, 1)
        if stat.deletions > TEST_DELETE_LINES_THRESHOLD or ratio > TEST_DELETE_RATIO_THRESHOLD:
            issues.append(
                f"{path} deletes {stat.deletions} test lines during core app changes; requires Scope-Exception: test-refactor"
            )
    return issues


def check_anti_truncation(
    mode: str,
    stats: dict[str, FileStats],
    exceptions: set[str],
    *,
    base: str | None = None,
) -> list[str]:
    if "large-refactor" in exceptions:
        return []
    issues: list[str] = []
    for path in sorted(HIGH_RISK_TRUNCATION_FILES):
        stat = stats.get(path)
        if not stat or stat.deletions <= 0:
            continue
        preimage_lines = get_preimage_line_count(mode, path, base=base)
        if not preimage_lines:
            continue
        ratio = stat.deletions / max(preimage_lines, 1)
        likely_refactor = stat.additions >= max(20, int(stat.deletions * 0.6))
        if ratio > ANTI_TRUNCATION_RATIO_THRESHOLD and not likely_refactor:
            issues.append(
                f"{path} deletes {stat.deletions}/{preimage_lines} lines (> {int(ANTI_TRUNCATION_RATIO_THRESHOLD * 100)}%) without Scope-Exception: large-refactor"
            )
    return issues


def run_ruff(paths: list[str]) -> int:
    py_paths = [path for path in paths if path.endswith(".py") and Path(path).exists()]
    if not py_paths:
        return 0
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--select",
            "F401,F821,F841",
            *py_paths,
        ],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true")
    group.add_argument("--range", nargs=2, metavar=("BASE", "HEAD"))
    group.add_argument("--files-from-stdin", action="store_true")
    parser.add_argument("--run-ruff", action="store_true")
    args = parser.parse_args()

    mode = "staged" if args.staged else "range" if args.range else "stdin"
    base = head = None
    exceptions = get_env_exceptions()

    if args.staged:
        paths = get_diff_name_only("staged")
        stats = get_diff_numstat("staged")
    elif args.range:
        base, head = args.range
        exceptions |= get_commit_range_exceptions(base, head)
        paths = get_diff_name_only("range", base=base, head=head)
        stats = get_diff_numstat("range", base=base, head=head)
    else:
        paths = get_files_from_stdin()
        stats = {path: FileStats(path, 0, 0) for path in paths}

    issues: list[str] = []
    issues.extend(check_file_count(paths, exceptions))
    issues.extend(check_freeze_growth(stats, exceptions))
    issues.extend(check_dependency_drift(paths, exceptions))
    issues.extend(check_cross_layer(paths, exceptions))
    issues.extend(check_test_mutilation(stats, exceptions))
    if mode in {"staged", "range"}:
        issues.extend(check_anti_truncation(mode, stats, exceptions, base=base))

    if issues:
        print("Diff scope check failed.")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if args.run_ruff:
        return run_ruff(paths)

    print("Diff scope check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
