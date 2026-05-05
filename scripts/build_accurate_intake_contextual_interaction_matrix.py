from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_contextual_interaction_matrix import (  # noqa: E402
    build_contextual_interaction_matrix_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Accurate Intake PL+CE contextual interaction matrix artifact."
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_contextual_interaction_matrix.json",
        help="Output JSON artifact path.",
    )
    args = parser.parse_args(argv)

    artifact = build_contextual_interaction_matrix_artifact()
    write_json_artifact(Path(args.output), artifact)
    print(f"wrote {args.output} status={artifact['status']}")
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
