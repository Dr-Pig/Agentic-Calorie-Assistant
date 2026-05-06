from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_index_backend_parity import (  # noqa: E402
    build_fooddb_index_backend_parity,
)
from app.nutrition.infrastructure.local_food_evidence_index import (  # noqa: E402
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.nutrition.infrastructure.sqlite_food_evidence_index import (  # noqa: E402
    SQLiteFtsFoodEvidenceIndex,
)
from app.nutrition.infrastructure.supabase_food_evidence_index import (  # noqa: E402
    SupabaseRowsFoodEvidenceIndex,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_SQLITE_DB = ROOT / "artifacts" / "tmp" / "accurate_intake_fooddb_backend_parity.sqlite"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_index_backend_parity.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic FoodDB index backend parity artifact."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--sqlite-db", default=str(DEFAULT_SQLITE_DB))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    local_index = LocalSmallAnchorFoodEvidenceIndex.from_path(Path(args.small_anchor_store))
    sqlite_index = SQLiteFtsFoodEvidenceIndex.rebuild_from_records(
        Path(args.sqlite_db),
        local_index.load_records(),
    )
    supabase_index = SupabaseRowsFoodEvidenceIndex.from_rows(
        _supabase_rows_from_records(local_index.load_records())
    )
    artifact = build_fooddb_index_backend_parity(
        local_index=local_index,
        sqlite_index=sqlite_index,
        supabase_index=supabase_index,
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


def _supabase_rows_from_records(records: object) -> tuple[dict[str, object], ...]:
    return tuple(asdict(record) for record in records)


if __name__ == "__main__":
    raise SystemExit(main())
