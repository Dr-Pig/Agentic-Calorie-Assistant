from __future__ import annotations

import sys

from scripts.build_current_shell_compatibility_serial_handoff import (
    DEFAULT_ACTIVATION_REVIEW_MANIFEST_PATH,
    DEFAULT_CURRENT_METADATA_FRESHNESS_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_QUEUE_JSON_PATH,
    main as _canonical_main,
)

LEGACY_DEFAULT_OUTPUT = "artifacts/accurate_intake_pl_ce_serial_handoff.json"
LEGACY_DEFAULT_QUEUE_JSON = "artifacts/accurate_intake_pl_ce_merge_queue_metadata.json"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not any(arg == "--output" or arg.startswith("--output=") for arg in args):
        args.extend(["--output", LEGACY_DEFAULT_OUTPUT])
    if not any(
        arg == "--queue-json" or arg.startswith("--queue-json=") or arg == "--stack-json"
        for arg in args
    ):
        args.extend(["--queue-json", LEGACY_DEFAULT_QUEUE_JSON])
    return _canonical_main(args)


__all__ = [
    "DEFAULT_ACTIVATION_REVIEW_MANIFEST_PATH",
    "DEFAULT_CURRENT_METADATA_FRESHNESS_PATH",
    "DEFAULT_OUTPUT_PATH",
    "DEFAULT_QUEUE_JSON_PATH",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
