from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_pl_ce_reviewer_cockpit import (  # noqa: E402
    build_pl_ce_reviewer_cockpit_artifact,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def _parse_artifact_arg(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("artifact must be formatted as group=path")
    group, path = value.split("=", 1)
    return group, Path(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Accurate Intake PL+CE reviewer cockpit artifact."
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        type=_parse_artifact_arg,
        help="Input artifact mapping formatted as group=path.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_pl_ce_reviewer_cockpit.json",
        help="Output JSON artifact path.",
    )
    args = parser.parse_args(argv)

    payloads = {group: read_json_artifact(path) for group, path in args.artifact}
    artifact = build_pl_ce_reviewer_cockpit_artifact(payloads)
    write_json_artifact(Path(args.output), artifact)
    print(f"wrote {args.output} status={artifact['status']}")
    return 0 if artifact["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
