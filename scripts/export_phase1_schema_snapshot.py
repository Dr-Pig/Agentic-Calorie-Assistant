from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.database import SessionLocal, init_db
from app.shared.infra.schema_reset_export import export_schema_reset_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a Phase 1 schema-reset snapshot before canonical schema changes.")
    parser.add_argument("--label", default="phase1", help="Optional label suffix for the export folder.")
    parser.add_argument("--sample-limit", type=int, default=50, help="Number of sample rows to export per tracked table.")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        export_dir = export_schema_reset_snapshot(
            db,
            sample_limit=max(1, args.sample_limit),
            label=args.label,
        )
    finally:
        db.close()

    print(str(export_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
