from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UTF8_BOM = b"\xef\xbb\xbf"


@dataclass(frozen=True)
class EncodingIssue:
    path: Path
    reason: str
    detail: str


def verify_markdown_encoding(path: Path, *, require_bom: bool = False) -> list[EncodingIssue]:
    issues: list[EncodingIssue] = []
    data = path.read_bytes()
    if require_bom and not data.startswith(UTF8_BOM):
        issues.append(EncodingIssue(path, "missing_utf8_bom", "UTF-8 BOM is required for this markdown file"))
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        return [EncodingIssue(path, "utf8_decode_error", str(exc))]

    if "\ufffd" in text:
        issues.append(EncodingIssue(path, "replacement_character", "decoded text contains U+FFFD"))
    if any("\ue000" <= char <= "\uf8ff" for char in text):
        issues.append(EncodingIssue(path, "private_use_character", "decoded text contains private-use characters"))
    if "?????" in text:
        issues.append(EncodingIssue(path, "question_mark_corruption", "decoded text contains repeated question marks"))
    return issues


def policy_markdown_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    docs = root / "docs"
    if docs.exists():
        paths.extend(path for path in docs.rglob("*.md") if "archive" not in path.relative_to(root).parts)
    agents = root / "AGENTS.md"
    if agents.exists():
        paths.append(agents)
    return sorted(set(paths))


def main() -> int:
    parser = argparse.ArgumentParser(description="Byte-level markdown encoding verifier.")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--policy-docs", action="store_true", help="Scan AGENTS.md and non-archive docs/**/*.md.")
    parser.add_argument("--require-bom", action="store_true")
    args = parser.parse_args()

    raw_paths = [Path(raw_path) for raw_path in args.paths]
    if args.policy_docs:
        raw_paths.extend(policy_markdown_paths(ROOT))
    if not raw_paths:
        parser.error("paths are required unless --policy-docs is used")

    issues: list[EncodingIssue] = []
    for raw_path in sorted(set(raw_paths)):
        issues.extend(verify_markdown_encoding(raw_path, require_bom=args.require_bom))

    if issues:
        for issue in issues:
            print(f"{issue.path}: {issue.reason}: {issue.detail}", file=sys.stderr)
        return 1
    print("markdown encoding check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
