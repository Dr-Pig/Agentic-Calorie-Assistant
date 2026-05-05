from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.exact_card_candidate_promotion_readiness import (  # noqa: E402
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (  # noqa: E402
    build_exact_evidence_lane_policy_artifact,
)
from app.nutrition.application.websearch_cache_rate_license_wall import (  # noqa: E402
    build_websearch_cache_rate_license_wall,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (  # noqa: E402
    build_websearch_selected_extract_packet_smoke,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_EXACT_CARD_READINESS = (
    ROOT / "artifacts" / "accurate_intake_exact_card_candidate_promotion_readiness.json"
)
DEFAULT_CACHE_RATE_LICENSE_WALL = (
    ROOT / "artifacts" / "accurate_intake_websearch_cache_rate_license_wall.json"
)
DEFAULT_OUTPUT = (
    ROOT / "artifacts" / "accurate_intake_websearch_selected_extract_packet_smoke.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic WebSearch selected-extract packet smoke artifact."
    )
    parser.add_argument("--exact-card-readiness-artifact", default=None)
    parser.add_argument("--cache-rate-license-artifact", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    exact_card_readiness = _load_exact_card_readiness(args.exact_card_readiness_artifact)
    cache_wall = _load_cache_wall(args.cache_rate_license_artifact)
    artifact = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=exact_card_readiness,
        cache_rate_license_artifact=cache_wall,
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "blockers": artifact["blockers"],
                "summary": artifact["summary"],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _load_exact_card_readiness(path: str | None) -> dict[str, object]:
    if path:
        return read_json_artifact(Path(path))
    if DEFAULT_EXACT_CARD_READINESS.exists():
        return read_json_artifact(DEFAULT_EXACT_CARD_READINESS)
    return build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )


def _load_cache_wall(path: str | None) -> dict[str, object]:
    if path:
        return read_json_artifact(Path(path))
    if DEFAULT_CACHE_RATE_LICENSE_WALL.exists():
        return read_json_artifact(DEFAULT_CACHE_RATE_LICENSE_WALL)
    return build_websearch_cache_rate_license_wall()


if __name__ == "__main__":
    raise SystemExit(main())
