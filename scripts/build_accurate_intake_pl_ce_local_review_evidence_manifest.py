from __future__ import annotations

import sys

from scripts.build_current_shell_compatibility_local_review_evidence_manifest import (
    DEFAULT_EVIDENCE_PATHS,
    DEFAULT_OUTPUT_PATH,
    build_current_shell_compatibility_local_review_evidence_manifest,
    build_pl_ce_local_review_evidence_manifest,
    main as _canonical_main,
)

LEGACY_DEFAULT_OUTPUT = "artifacts/accurate_intake_pl_ce_local_review_evidence_manifest.json"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not any(arg == "--output" or arg.startswith("--output=") for arg in args):
        args.extend(["--output", LEGACY_DEFAULT_OUTPUT])
    return _canonical_main(args)

__all__ = [
    "DEFAULT_EVIDENCE_PATHS",
    "DEFAULT_OUTPUT_PATH",
    "build_current_shell_compatibility_local_review_evidence_manifest",
    "build_pl_ce_local_review_evidence_manifest",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
