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
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_MATRIX_PATH = ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_case_matrix.json"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_anti_overfit_guard.json"


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"artifact_type": "missing", "status": "missing"}
    return dict(payload) if isinstance(payload, dict) else {"artifact_type": "invalid", "status": "invalid"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the PL+CE context live diagnostic anti-overfit guard without invoking providers."
    )
    parser.add_argument("--matrix-json", default=str(DEFAULT_MATRIX_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    artifact = build_context_live_diagnostic_anti_overfit_guard_artifact(
        _read_json(Path(args.matrix_json))
    )
    write_json_artifact(Path(args.output), artifact)
    print(json.dumps({"status": artifact["status"], "artifact": args.output}, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
