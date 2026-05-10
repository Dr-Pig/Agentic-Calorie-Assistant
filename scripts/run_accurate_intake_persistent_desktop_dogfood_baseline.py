from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.persistent_desktop_dogfood_baseline import (  # noqa: E402
    DEFAULT_DB_PATH,
    build_persistent_desktop_dogfood_baseline_report,
)

DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_persistent_desktop_dogfood_baseline.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the persistent desktop dogfood baseline.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--local-date", required=True)
    parser.add_argument("--user-id", default="local-self-use-001")
    parser.add_argument("--local-debug-token", required=True)
    parser.add_argument("--reset-db", action="store_true")
    parser.add_argument("--feedback-dir")
    parser.add_argument("--backup-dir")
    parser.add_argument("--export-dir")
    parser.add_argument("--review-queue-artifact-path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)
    report = build_persistent_desktop_dogfood_baseline_report(
        db_path=Path(args.db_path),
        local_date=args.local_date,
        user_external_id=args.user_id,
        local_debug_token=args.local_debug_token,
        reset_db=args.reset_db,
        **{
            key: Path(value)
            for key, value in {
                "feedback_dir": args.feedback_dir,
                "backup_dir": args.backup_dir,
                "export_dir": args.export_dir,
                "review_queue_artifact_path": args.review_queue_artifact_path,
            }.items()
            if value is not None
        },
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
