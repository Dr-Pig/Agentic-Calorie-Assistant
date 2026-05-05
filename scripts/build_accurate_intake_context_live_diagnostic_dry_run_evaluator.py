from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (  # noqa: E402
    build_context_live_diagnostic_case_matrix_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_dry_run_evaluator import (  # noqa: E402
    build_context_live_diagnostic_dry_run_evaluator_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _read_outputs(path: Path | None) -> list[dict[str, Any]] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("fixture_outputs"), list):
        return [dict(item) for item in payload["fixture_outputs"] if isinstance(item, dict)]
    raise ValueError("fixture output JSON must be a list or an object with fixture_outputs list")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a fixture-only dry-run evaluator for context live diagnostic cases."
    )
    parser.add_argument(
        "--matrix-json",
        help="Existing context live diagnostic case matrix JSON. Defaults to generated matrix.",
    )
    parser.add_argument(
        "--fixture-outputs-json",
        help="Optional fixture manager outputs for negative or custom dry-run checks.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_context_live_diagnostic_dry_run_evaluator.json",
    )
    args = parser.parse_args(argv)

    matrix = (
        _read_json(Path(args.matrix_json))
        if args.matrix_json
        else build_context_live_diagnostic_case_matrix_artifact()
    )
    artifact = build_context_live_diagnostic_dry_run_evaluator_artifact(
        matrix,
        fixture_outputs=_read_outputs(Path(args.fixture_outputs_json))
        if args.fixture_outputs_json
        else None,
    )
    write_json_artifact(Path(args.output), artifact)
    print(json.dumps({"artifact": args.output, "status": artifact["status"]}, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
