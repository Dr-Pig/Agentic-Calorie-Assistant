from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_non_fooddb_mutation_tool_guard_smoke import (  # noqa: E402
    build_non_fooddb_mutation_tool_guard_smoke_artifact,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the PLCE non-FoodDB mutation tool guard smoke.")
    parser.add_argument("--output", required=True, help="Path to write the artifact JSON.")
    args = parser.parse_args(argv)

    artifact = build_non_fooddb_mutation_tool_guard_smoke_artifact()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
