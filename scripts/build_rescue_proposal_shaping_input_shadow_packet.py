from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rescue.application.proposal_shaping_input_shadow import (  # noqa: E402
    build_rescue_proposal_shaping_input_shadow_packet,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the rescue proposal-shaping input shadow packet artifact."
    )
    parser.add_argument("--option-generation-shadow-packet", required=True, type=Path)
    parser.add_argument("--budget-context-json", type=Path)
    parser.add_argument("--body-plan-context-json", type=Path)
    parser.add_argument("--rescue-history-context-json", type=Path)
    parser.add_argument("--suppression-context-json", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    packet = build_rescue_proposal_shaping_input_shadow_packet(
        option_generation_shadow_packet=read_json_artifact(args.option_generation_shadow_packet),
        budget_context=_optional_object(args.budget_context_json),
        body_plan_context=_optional_object(args.body_plan_context_json),
        rescue_history_context=_optional_object(args.rescue_history_context_json),
        suppression_context=_optional_object_list(args.suppression_context_json),
    )
    write_json_artifact(args.output, packet)
    print(json.dumps(packet, ensure_ascii=False))
    return 0 if packet["status"] == "pass" else 1


def _optional_object(path: Path | None) -> dict[str, Any] | None:
    return read_json_artifact(path) if path else None


def _optional_object_list(path: Path | None) -> list[dict[str, Any]] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError(f"JSON artifact must be a list: {path}")
    return [item for item in payload if isinstance(item, dict)]


if __name__ == "__main__":
    raise SystemExit(main())
