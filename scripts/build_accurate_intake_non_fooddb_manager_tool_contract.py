from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_non_fooddb_manager_tool_contract import (  # noqa: E402
    build_non_fooddb_manager_tool_contract_artifact,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the non-FoodDB manager tool contract artifact.")
    parser.add_argument("--output", default="artifacts/accurate_intake_non_fooddb_manager_tool_contract.json")
    args = parser.parse_args(argv)

    artifact = build_non_fooddb_manager_tool_contract_artifact()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact, ensure_ascii=False))
    return 0 if artifact["status"] == "non_fooddb_manager_tool_contract_ready_for_human_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
