from __future__ import annotations

import sys

from scripts.build_current_shell_compatibility_metadata_freshness_pack import (
    DEFAULT_EVIDENCE_PATHS,
    DEFAULT_OUTPUT_PATH,
    build_current_shell_compatibility_metadata_freshness_report,
    build_legacy_metadata_freshness_report,
    canonicalize_metadata_freshness_pack,
    main as _canonical_main,
)

LEGACY_DEFAULT_OUTPUT = "artifacts/accurate_intake_pl_ce_metadata_freshness_pack.json"


def build_pl_ce_metadata_freshness_report(*args, **kwargs):
    return build_current_shell_compatibility_metadata_freshness_report(*args, **kwargs)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not any(arg == "--output" or arg.startswith("--output=") for arg in args):
        args.extend(["--output", LEGACY_DEFAULT_OUTPUT])
    return _canonical_main(args)


__all__ = [
    "DEFAULT_EVIDENCE_PATHS",
    "DEFAULT_OUTPUT_PATH",
    "build_current_shell_compatibility_metadata_freshness_report",
    "build_legacy_metadata_freshness_report",
    "build_pl_ce_metadata_freshness_report",
    "canonicalize_metadata_freshness_pack",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
