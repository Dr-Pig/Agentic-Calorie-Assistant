from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.shadow_comparison import (  # noqa: E402
    build_advanced_shadow_comparison_artifact,
)


DEFAULT_OUTPUT = ROOT / "artifacts" / "advanced_shadow_comparison.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the advanced shadow comparison artifact from JSON inputs."
    )
    parser.add_argument("--fixture-chain", required=True)
    parser.add_argument("--dogfood-replay", required=True)
    parser.add_argument("--recommendation-live", required=True)
    parser.add_argument("--rescue-live")
    parser.add_argument("--baseline-cases")
    parser.add_argument("--advanced-cases")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_read_json(Path(args.fixture_chain)),
        dogfood_replay_artifact=_read_json(Path(args.dogfood_replay)),
        recommendation_copy_live_diagnostic_artifact=_read_json(
            Path(args.recommendation_live)
        ),
        rescue_copy_live_diagnostic_artifact=_optional_json(args.rescue_live),
        baseline_case_artifacts=_read_list(args.baseline_cases),
        advanced_case_artifacts=_read_list(args.advanced_cases),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"artifact": str(output), "status": artifact.get("status")}, ensure_ascii=False))
    return 0


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    return value if isinstance(value, dict) else {}


def _optional_json(path_text: str | None) -> dict[str, Any] | None:
    return _read_json(Path(path_text)) if path_text else None


def _read_list(path_text: str | None) -> list[dict[str, Any]]:
    if not path_text:
        return []
    value = json.loads(Path(path_text).read_text(encoding="utf-8-sig"))
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
