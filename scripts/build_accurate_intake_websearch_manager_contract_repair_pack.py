from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_manager_contract_repair_pack import (  # noqa: E402
    build_websearch_manager_contract_repair_pack,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_PROBE = ROOT / "artifacts" / "accurate_intake_websearch_manager_contract_probe.json"
DEFAULT_OUTPUT = (
    ROOT / "artifacts" / "accurate_intake_websearch_manager_contract_repair_pack.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build WebSearch manager contract repair pack artifact."
    )
    parser.add_argument("--contract-probe-artifact", default=str(DEFAULT_PROBE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_websearch_manager_contract_repair_pack(
        contract_probe_artifact=read_json_artifact(Path(args.contract_probe_artifact)),
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "case_count": artifact["summary"]["case_count"],
                "alias_hint_counts": artifact["summary"]["alias_hint_counts"],
                "next_recommended_slice": artifact["next_recommended_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
