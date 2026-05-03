from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.local_dogfood_data_hygiene import (  # noqa: E402
    backup_local_dogfood_db,
    build_local_dogfood_data_manifest,
)


def _write_output(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect or back up local-only Accurate Intake dogfood SQLite data."
    )
    parser.add_argument("--operation", choices=["inspect", "backup", "reset"], default="inspect")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--backup-dir", default="workspace_data/local_dogfood_backups")
    parser.add_argument("--label", default="manual-backup")
    parser.add_argument("--output", default="artifacts/accurate_intake_local_dogfood_data_hygiene.json")
    args = parser.parse_args(argv)

    db_path = Path(args.db_path)
    if args.operation == "backup":
        payload = backup_local_dogfood_db(
            db_path=db_path,
            backup_dir=Path(args.backup_dir),
            label=args.label,
        )
    else:
        payload = build_local_dogfood_data_manifest(db_path=db_path, operation=args.operation)

    _write_output(Path(args.output), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("allowed", True) is True or args.operation == "inspect" else 1


if __name__ == "__main__":
    raise SystemExit(main())
