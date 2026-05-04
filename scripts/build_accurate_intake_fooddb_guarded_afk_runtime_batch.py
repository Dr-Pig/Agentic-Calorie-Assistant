from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_guarded_afk_runtime_batch import (  # noqa: E402
    apply_guarded_afk_runtime_anchor_batch_to_small_anchor_store,
    build_guarded_afk_runtime_anchor_batch,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_guarded_afk_runtime_anchor_batch.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build and optionally apply a Guarded AFK existing-anchor runtime batch."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--max-items", type=int, default=40)
    parser.add_argument("--update-small-anchor-store", action="store_true")
    args = parser.parse_args(argv)

    small_anchor_path = Path(args.small_anchor_store)
    payload = read_json_artifact(small_anchor_path)
    batch = build_guarded_afk_runtime_anchor_batch(
        small_anchor_payload=payload,
        max_items=args.max_items,
    )
    write_json_artifact(Path(args.output), batch)
    if args.update_small_anchor_store:
        updated = apply_guarded_afk_runtime_anchor_batch_to_small_anchor_store(payload, batch)
        _write_small_anchor_store(small_anchor_path, updated)

    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": batch["claim_scope"],
                "runtime_truth_changed": batch["runtime_truth_changed"],
                "selected_runtime_anchor_count": batch["summary"]["selected_runtime_anchor_count"],
                "source_policy": batch["source_policy"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_small_anchor_store(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
