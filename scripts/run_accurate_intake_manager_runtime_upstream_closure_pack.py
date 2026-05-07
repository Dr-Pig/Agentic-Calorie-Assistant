from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_manager_runtime_upstream_closure_pack import (  # noqa: E402
    build_manager_runtime_upstream_closure_pack,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402
from scripts.run_accurate_intake_free_text_manual_target_gate import (  # noqa: E402
    build_free_text_manual_target_gate_artifact,
)


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_manager_runtime_upstream_closure_pack.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Manager Runtime upstream closure pack for RT2-RT5."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    artifact = build_manager_runtime_upstream_closure_pack(
        manual_target_gate=build_free_text_manual_target_gate_artifact()
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "green_gate_count": artifact["summary"]["green_gate_count"],
                "target_gate_count": artifact["summary"]["target_gate_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
