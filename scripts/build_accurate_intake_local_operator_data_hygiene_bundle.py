from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_local_operator_data_hygiene_bundle import (  # noqa: E402
    build_local_operator_data_hygiene_bundle,
)

DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_local_operator_data_hygiene_bundle.json"
DEFAULT_DB_PATH = ROOT / "workspace_data" / "local_dogfood" / "accurate_intake.sqlite3"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local-only operator data hygiene review bundle."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--backup-dir", default="workspace_data/local_dogfood_backups")
    parser.add_argument("--export-dir", default="workspace_data/local_dogfood_exports")
    parser.add_argument("--import-manifest")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    artifact = build_local_operator_data_hygiene_bundle(
        db_path=Path(args.db_path),
        backup_dir=Path(args.backup_dir),
        export_dir=Path(args.export_dir),
        import_manifest_path=Path(args.import_manifest) if args.import_manifest else None,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "local_operator_data_hygiene_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
