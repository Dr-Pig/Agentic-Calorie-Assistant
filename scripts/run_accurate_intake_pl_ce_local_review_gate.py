from __future__ import annotations

import sys

from scripts.run_current_shell_compatibility_local_review_gate import (
    DEFAULT_DECISION_OUTPUT,
    DEFAULT_MANIFEST_OUTPUT,
    main as _canonical_main,
    run_current_shell_compatibility_local_review_gate,
    run_pl_ce_local_review_gate,
)

LEGACY_DEFAULT_MANIFEST_OUTPUT = (
    "artifacts/accurate_intake_pl_ce_local_review_evidence_manifest.json"
)
LEGACY_DEFAULT_DECISION_OUTPUT = (
    "artifacts/accurate_intake_pl_ce_local_review_decision_pack.json"
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not any(
        arg == "--manifest-output" or arg.startswith("--manifest-output=") for arg in args
    ):
        args.extend(["--manifest-output", LEGACY_DEFAULT_MANIFEST_OUTPUT])
    if not any(
        arg == "--decision-output" or arg.startswith("--decision-output=") for arg in args
    ):
        args.extend(["--decision-output", LEGACY_DEFAULT_DECISION_OUTPUT])
    return _canonical_main(args)

__all__ = [
    "DEFAULT_DECISION_OUTPUT",
    "DEFAULT_MANIFEST_OUTPUT",
    "main",
    "run_current_shell_compatibility_local_review_gate",
    "run_pl_ce_local_review_gate",
]


if __name__ == "__main__":
    raise SystemExit(main())
