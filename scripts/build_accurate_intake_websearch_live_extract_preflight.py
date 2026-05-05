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
from app.nutrition.application.websearch_exact_candidate_review_packet import (  # noqa: E402
    build_websearch_exact_candidate_review_packet,
)
from app.nutrition.application.websearch_extract_result_candidate_smoke import (  # noqa: E402
    build_websearch_extract_result_candidate_smoke,
)
from app.nutrition.application.websearch_live_extract_preflight import (  # noqa: E402
    build_websearch_live_extract_preflight,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (  # noqa: E402
    build_websearch_selected_extract_packet_smoke,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_REVIEW_PACKET = (
    ROOT / "artifacts" / "accurate_intake_websearch_exact_candidate_review_packet.json"
)
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_live_extract_preflight.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic WebSearch live extract preflight artifact."
    )
    parser.add_argument("--review-packet-artifact", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    review_packet = _load_review_packet(args.review_packet_artifact)
    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet,
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


def _load_review_packet(path: str | None) -> dict[str, object]:
    if path:
        return read_json_artifact(Path(path))
    if DEFAULT_REVIEW_PACKET.exists():
        return read_json_artifact(DEFAULT_REVIEW_PACKET)
    exact_card_readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    selected_extract = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=exact_card_readiness,
    )
    extract_result = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected_extract,
    )
    return build_websearch_exact_candidate_review_packet(
        extract_result_artifact=extract_result,
    )


if __name__ == "__main__":
    raise SystemExit(main())
