from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID  # noqa: E402
from app.recommendation.application.three_node_live_preflight import (  # noqa: E402
    build_recommendation_three_node_live_preflight,
)


def write_recommendation_three_node_live_preflight(
    output_path: Path,
    *,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
) -> Path:
    artifact = build_recommendation_three_node_live_preflight(
        provider_profile_id=provider_profile_id
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build dormant recommendation three-node live preflight artifact."
    )
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--provider-profile-id",
        default=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    )
    args = parser.parse_args(argv)
    write_recommendation_three_node_live_preflight(
        Path(args.output),
        provider_profile_id=args.provider_profile_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main", "write_recommendation_three_node_live_preflight"]
