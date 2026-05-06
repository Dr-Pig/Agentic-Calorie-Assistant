from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_manager_tool_surface_inventory import (
    build_manager_tool_surface_inventory_artifact,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the PLCE non-FoodDB Manager tool surface inventory.")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    artifact = build_manager_tool_surface_inventory_artifact()
    payload = json.dumps(artifact, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if artifact["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
