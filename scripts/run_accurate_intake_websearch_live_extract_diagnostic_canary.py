from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_live_extract_diagnostic_canary import (  # noqa: E402
    build_websearch_live_extract_diagnostic_canary,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_live_extract_diagnostic_canary.json"


class _FixtureExtractPort:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fixture", "configured": True}

    async def extract_rows(self, *, urls: list[str], query: str) -> list[dict[str, Any]]:
        source_url = urls[0] if urls else "https://example.test/menu"
        return [
            {
                "source_url": source_url,
                "canonical_name": query,
                "matched_name": query,
                "serving_basis_candidate": "per_serving",
                "kcal_value_candidate": 400,
                "kcal_text_present": True,
                "identity_text_present": True,
                "raw_extract_ref": f"fixture_extract:{source_url}",
            }
        ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run WebSearch live extract diagnostic canary with injected fixture port."
    )
    parser.add_argument("--diagnostic-gate", required=True)
    parser.add_argument("--live-permission-granted", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = asyncio.run(
        build_websearch_live_extract_diagnostic_canary(
            diagnostic_gate_artifact=read_json_artifact(Path(args.diagnostic_gate)),
            live_permission_granted=args.live_permission_granted,
            extract_port=_FixtureExtractPort(),
        )
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "extract_port_used": artifact["extract_port_used"],
                "live_extract_used": artifact["live_extract_used"],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
