from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_manager_output_diagnostic import (  # noqa: E402
    build_fixture_websearch_manager_outputs,
    build_websearch_manager_output_diagnostic,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_INPUT = ROOT / "artifacts" / "accurate_intake_websearch_manager_packet_smoke.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_manager_output_diagnostic.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic WebSearch Manager-output boundary diagnostic artifact."
    )
    parser.add_argument("--manager-packet-artifact", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    input_path = Path(args.manager_packet_artifact)
    if input_path.exists():
        packet_artifact = read_json_artifact(input_path)
    else:
        from scripts.build_accurate_intake_websearch_manager_packet_smoke import (  # noqa: PLC0415
            main as build_manager_packet_smoke,
        )

        build_manager_packet_smoke(["--output", str(input_path)])
        packet_artifact = read_json_artifact(input_path)

    manager_outputs = build_fixture_websearch_manager_outputs(packet_artifact=packet_artifact)
    artifact = build_websearch_manager_output_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=manager_outputs,
        live_provider_used=False,
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "claim_scope": artifact["claim_scope"],
                "status": artifact["status"],
                "case_count": artifact["summary"]["case_count"],
                "pass_count": artifact["summary"]["pass_count"],
                "live_provider_used": artifact["live_provider_used"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
