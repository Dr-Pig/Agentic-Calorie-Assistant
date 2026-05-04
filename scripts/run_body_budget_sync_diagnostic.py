from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.body_budget_sync_diagnostic import (  # noqa: E402
    build_body_budget_sync_diagnostic_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


def _parse_summary_payload(raw_summary: str) -> dict[str, object]:
    payload = json.loads(raw_summary)
    if not isinstance(payload, dict):
        raise ValueError("--summary-json must be a JSON object")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a local BodyBudget sync diagnostic artifact.")
    parser.add_argument(
        "--output",
        default="artifacts/body_budget_sync_diagnostic.json",
    )
    parser.add_argument("--summary-json", required=True)
    args = parser.parse_args(argv)

    artifact = build_body_budget_sync_diagnostic_artifact(_parse_summary_payload(args.summary_json))
    write_json_artifact(Path(args.output), artifact)
    print(json.dumps({"artifact": args.output, "status": artifact["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
