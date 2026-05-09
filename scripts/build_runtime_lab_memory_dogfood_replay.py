from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.memory.application.runtime_lab_dogfood_replay import (  # noqa: E402
    write_memory_dogfood_replay_review_artifact,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build reviewed dogfood replay expansion cases for memory runtime lab."
    )
    parser.add_argument("--reviewed-traces-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    reviewed_records = _read_reviewed_records(args.reviewed_traces_json)
    artifact = write_memory_dogfood_replay_review_artifact(
        args.output,
        reviewed_records,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "status": artifact["status"],
                "reviewed_case_count": artifact["reviewed_case_count"],
                "rejected_record_count": artifact["rejected_record_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] == "pass" else 1


def _read_reviewed_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return [record for record in payload if isinstance(record, dict)]
    if isinstance(payload, dict):
        records = payload.get("reviewed_traces") or []
        if isinstance(records, list):
            return [record for record in records if isinstance(record, dict)]
    raise ValueError("reviewed traces JSON must be a list or object.reviewed_traces")


if __name__ == "__main__":
    raise SystemExit(main())
