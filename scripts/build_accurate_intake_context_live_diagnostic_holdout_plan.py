from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_live_diagnostic_anti_overfit_guard import (  # noqa: E402
    build_context_live_diagnostic_anti_overfit_guard_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (  # noqa: E402
    build_context_live_diagnostic_case_matrix_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_holdout_plan import (  # noqa: E402
    build_context_live_diagnostic_holdout_plan_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_MATRIX_PATH = ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_case_matrix.json"
DEFAULT_ANTI_OVERFIT_PATH = (
    ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_anti_overfit_guard.json"
)
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_holdout_plan.json"


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"artifact_type": "missing", "status": "missing"}
    return dict(payload) if isinstance(payload, dict) else {"artifact_type": "invalid", "status": "invalid"}


def _matrix_payload(path: Path) -> dict:
    payload = _read_json(path)
    if payload.get("artifact_type") == "missing":
        return build_context_live_diagnostic_case_matrix_artifact()
    return payload


def _anti_overfit_payload(path: Path, matrix: dict) -> dict:
    payload = _read_json(path)
    if payload.get("artifact_type") == "missing":
        return build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the PL+CE context live diagnostic holdout plan without provider calls."
    )
    parser.add_argument("--matrix-json", default=str(DEFAULT_MATRIX_PATH))
    parser.add_argument("--anti-overfit-json", default=str(DEFAULT_ANTI_OVERFIT_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    matrix = _matrix_payload(Path(args.matrix_json))
    anti_overfit = _anti_overfit_payload(Path(args.anti_overfit_json), matrix)
    artifact = build_context_live_diagnostic_holdout_plan_artifact(
        context_live_diagnostic_case_matrix=matrix,
        context_live_diagnostic_anti_overfit_guard=anti_overfit,
    )
    write_json_artifact(Path(args.output), artifact)
    print(json.dumps({"status": artifact["status"], "artifact": args.output}, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
