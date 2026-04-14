from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs" / "quality" / "USER_FACING_STRING_GUARD_REGISTRY.json"
ALLOWLIST_PATH = ROOT / "docs" / "quality" / "USER_FACING_STRING_GUARD_ALLOWLIST.json"

COMMON_MOJIBAKE_SHARDS = (
    "銝",
    "嚗",
    "憭",
    "瘥",
    "蝛",
    "雿",
    "撠",
    "餈",
    "瑚",
    "寞",
    "嗾",
    "桀",
    "喳",
)


@dataclass(frozen=True)
class GuardIssue:
    path: Path
    line_no: int
    reason: str
    line: str


def _load_registry() -> list[dict[str, object]]:
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing guard registry: {REGISTRY_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid guard registry JSON: {exc}") from exc
    if not isinstance(registry, list) or not registry:
        raise RuntimeError("user-facing string guard registry must be a non-empty JSON list")
    return registry


def _load_allowlist() -> set[str]:
    try:
        payload = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid guard allowlist JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise RuntimeError("user-facing string guard allowlist must be a JSON list")
    return {str(entry) for entry in payload if isinstance(entry, str)}


def _iter_guarded_files() -> list[Path]:
    files: list[Path] = []
    for entry in _load_registry():
        if not isinstance(entry, dict):
            raise RuntimeError("guard registry entries must be objects")
        rel_root = entry.get("root")
        suffixes = entry.get("suffixes")
        if not isinstance(rel_root, str) or not rel_root:
            raise RuntimeError("guard registry entry missing string field 'root'")
        if not isinstance(suffixes, list) or not suffixes:
            raise RuntimeError(f"guard registry entry {rel_root} missing non-empty 'suffixes'")
        root = ROOT / rel_root
        if not root.exists():
            raise RuntimeError(f"guard registry root not found: {root}")
        allowed_suffixes = {str(value) for value in suffixes if isinstance(value, str)}
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in allowed_suffixes:
                files.append(path)
    return sorted(set(files))


def _contains_private_use(text: str) -> bool:
    for char in text:
        code = ord(char)
        if 0xE000 <= code <= 0xF8FF or 0xF0000 <= code <= 0xFFFFD or 0x100000 <= code <= 0x10FFFD:
            return True
    return False


def _contains_forbidden_control(text: str) -> bool:
    for char in text:
        code = ord(char)
        if code in (0x09, 0x0A, 0x0D):
            continue
        if code < 0x20 or 0x7F <= code <= 0x9F:
            return True
    return False


def _looks_like_mojibake_shard_cluster(text: str) -> bool:
    shard_hits = sum(1 for shard in COMMON_MOJIBAKE_SHARDS if shard in text)
    return shard_hits >= 3 and any(token in text for token in ('"', "'", "reply_text", "label", "reason", "summary"))


def find_issues_in_text(path: Path, text: str) -> list[GuardIssue]:
    issues: list[GuardIssue] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "\uFFFD" in line:
            issues.append(GuardIssue(path=path, line_no=line_no, reason="replacement_character", line=line))
        if _contains_private_use(line):
            issues.append(GuardIssue(path=path, line_no=line_no, reason="private_use_character", line=line))
        if _contains_forbidden_control(line):
            issues.append(GuardIssue(path=path, line_no=line_no, reason="forbidden_control_character", line=line))
        if _looks_like_mojibake_shard_cluster(line):
            issues.append(GuardIssue(path=path, line_no=line_no, reason="mojibake_shard_cluster", line=line))
    return issues


def main() -> int:
    issues: list[GuardIssue] = []
    allowlist = _load_allowlist()
    for path in _iter_guarded_files():
        rel_path = path.relative_to(ROOT).as_posix()
        if rel_path in allowlist:
            continue
        text = path.read_text(encoding="utf-8")
        issues.extend(find_issues_in_text(path, text))

    if issues:
        print("[FAIL] user-facing mojibake guard found suspicious text:", file=sys.stderr)
        for issue in issues:
            rel_path = issue.path.relative_to(ROOT)
            print(
                f"- {rel_path}:{issue.line_no} [{issue.reason}] {issue.line.strip()}",
                file=sys.stderr,
            )
        return 1

    print("[OK] user-facing mojibake guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
