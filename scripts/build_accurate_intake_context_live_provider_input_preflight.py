from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_live_diagnostic_anti_overfit_guard import (  # noqa: E402
    build_context_live_diagnostic_anti_overfit_guard_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (  # noqa: E402
    build_context_live_diagnostic_case_matrix_artifact,
)
from app.composition.accurate_intake_context_live_provider_input_preflight import (  # noqa: E402
    build_context_live_provider_input_preflight_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_context_live_provider_input_preflight.json"


def _read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return dict(payload) if isinstance(payload, dict) else {"artifact_type": "invalid_json_shape"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the PL+CE context live provider input preflight without invoking a live provider."
        )
    )
    parser.add_argument("--matrix-json")
    parser.add_argument("--anti-overfit-json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    matrix = _read_json(Path(args.matrix_json)) if args.matrix_json else None
    if matrix is None:
        matrix = build_context_live_diagnostic_case_matrix_artifact()
    anti_overfit = _read_json(Path(args.anti_overfit_json)) if args.anti_overfit_json else None
    if anti_overfit is None:
        anti_overfit = build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)

    artifact = build_context_live_provider_input_preflight_artifact(
        context_live_diagnostic_case_matrix=matrix,
        context_live_diagnostic_anti_overfit_guard=anti_overfit,
    )
    write_json_artifact(Path(args.output), artifact)
    print(json.dumps({"artifact": args.output, "status": artifact["status"]}, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
