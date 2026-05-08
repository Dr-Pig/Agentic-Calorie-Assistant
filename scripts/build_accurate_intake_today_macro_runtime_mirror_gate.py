from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_today_macro_mirror_gate import (  # noqa: E402
    build_today_macro_runtime_mirror_gate_artifact,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def _read_yaml_artifact(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manager-gate-ledger-yaml",
        default="docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml",
    )
    parser.add_argument("--current-budget-json", required=True)
    parser.add_argument(
        "--renderer-source-map-json",
        default="artifacts/accurate_intake_product_pages_renderer_source_map.json",
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_today_macro_runtime_mirror_gate.json",
    )
    args = parser.parse_args(argv)

    renderer_source_map_path = Path(args.renderer_source_map_json)
    renderer_source_map_artifact = (
        read_json_artifact(renderer_source_map_path)
        if renderer_source_map_path.exists()
        else None
    )
    artifact = build_today_macro_runtime_mirror_gate_artifact(
        manager_gate_ledger_artifact=_read_yaml_artifact(Path(args.manager_gate_ledger_yaml)),
        current_budget_payload=read_json_artifact(Path(args.current_budget_json)),
        renderer_source_map_artifact=renderer_source_map_artifact,
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(json.dumps(artifact, ensure_ascii=False))
    return 0 if artifact["status"] == "today_macro_runtime_mirror_gate_ready_for_browser" else 1


if __name__ == "__main__":
    raise SystemExit(main())
