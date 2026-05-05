from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_live_provider_input_preflight import (  # noqa: E402
    build_context_live_provider_input_preflight_artifact,
)
from app.composition.accurate_intake_context_live_response_contract_dry_run import (  # noqa: E402
    build_context_live_response_contract_dry_run_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_context_live_response_contract_dry_run.json"


def _read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return dict(payload) if isinstance(payload, dict) else {"artifact_type": "invalid_json_shape"}


def _read_json_list(path: Path | None) -> list[dict[str, Any]] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [dict(row) for row in payload] if isinstance(payload, list) else [{"case_id": "invalid_json_shape"}]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the PL+CE context live response contract dry-run without invoking a live provider."
        )
    )
    parser.add_argument("--provider-input-preflight-json")
    parser.add_argument("--fixture-responses-json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    preflight = _read_json(Path(args.provider_input_preflight_json)) if args.provider_input_preflight_json else None
    if preflight is None:
        preflight = build_context_live_provider_input_preflight_artifact()
    fixture_responses = _read_json_list(Path(args.fixture_responses_json)) if args.fixture_responses_json else None

    artifact = build_context_live_response_contract_dry_run_artifact(
        context_live_provider_input_preflight=preflight,
        fixture_responses=fixture_responses,
    )
    write_json_artifact(Path(args.output), artifact)
    print(json.dumps({"artifact": args.output, "status": artifact["status"]}, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
