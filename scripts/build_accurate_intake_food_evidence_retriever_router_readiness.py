from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.food_evidence_retriever_router import (  # noqa: E402
    RetrieverBackendAvailability,
)
from app.nutrition.application.food_evidence_retriever_router_readiness import (  # noqa: E402
    build_food_evidence_retriever_router_readiness,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402

DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_food_evidence_retriever_router_readiness.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--websearch-status-packet", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    artifact = build_food_evidence_retriever_router_readiness(
        base_availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=True,
            supabase_index=True,
        ),
        websearch_status_packet=_read_optional(args.websearch_status_packet),
    )
    write_json_artifact(args.output, artifact)
    return 0


def _read_optional(path: Path | None) -> dict | None:
    if path is None:
        return None
    return read_json_artifact(path)


if __name__ == "__main__":
    raise SystemExit(main())
