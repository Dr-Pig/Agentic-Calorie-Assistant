from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_live_diagnostic_stage_gate import (  # noqa: E402
    LIVE_STAGES,
    build_context_live_diagnostic_stage_gate_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_stage_gate.json"


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return dict(payload) if isinstance(payload, dict) else {"artifact_type": "invalid_json_shape"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the PL+CE context live diagnostic stage-order gate."
    )
    parser.add_argument("--live-stage", choices=LIVE_STAGES, required=True)
    parser.add_argument("--canary-json", required=True)
    parser.add_argument("--prior-single-case-stage-gate-json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    artifact = build_context_live_diagnostic_stage_gate_artifact(
        live_stage=str(args.live_stage),
        context_live_diagnostic_canary=_read_json(Path(args.canary_json)),
        prior_single_case_stage_gate=_read_json(
            Path(args.prior_single_case_stage_gate_json)
            if args.prior_single_case_stage_gate_json
            else None
        ),
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "status": artifact["status"],
                "live_stage": artifact["live_stage"],
                "live_provider_invoked": artifact["live_provider_invoked"],
                "product_readiness_claimed": artifact["product_readiness_claimed"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
