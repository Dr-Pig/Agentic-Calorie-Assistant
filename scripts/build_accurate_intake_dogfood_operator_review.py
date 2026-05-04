from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.dogfood_operator_review import (  # noqa: E402
    build_dogfood_operator_review_surface,
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local-only Accurate Intake dogfood operator review surface."
    )
    parser.add_argument(
        "--dogfood-json",
        required=True,
        help="PR110 one-day realistic dogfood diagnostic artifact path.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_dogfood_operator_review.json",
        help="Output artifact path.",
    )
    args = parser.parse_args(argv)

    artifact = build_dogfood_operator_review_surface(_read_json(Path(args.dogfood_json)))
    _write_json(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": args.output,
                "status": artifact["status"],
                "source_status": artifact["source_status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
