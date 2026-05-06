from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_source_adapter_guard import (  # noqa: E402
    build_websearch_source_adapter_guard,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_source_adapter_guard.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic WebSearch source adapter guard artifact."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_websearch_source_adapter_guard()
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "blockers": artifact["blockers"],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
