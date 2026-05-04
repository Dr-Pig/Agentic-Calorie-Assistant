from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_runtime_anchor_batch import (  # noqa: E402
    apply_internal_seed_runtime_anchor_batch_to_small_anchor_store,
    build_existing_anchor_promotion_plan,
    build_fooddb_runtime_coverage_matrix,
    build_fooddb_status_packet,
    build_internal_seed_runtime_anchor_batch,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_COVERAGE_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_runtime_coverage_matrix.json"
DEFAULT_PLAN_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_existing_anchor_promotion_plan.json"
DEFAULT_BATCH_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_internal_seed_runtime_anchor_batch.json"
DEFAULT_STATUS_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_status_packet.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build FoodDB runtime coverage, narrow promotion plan, batch, and status artifacts."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--coverage-output", default=str(DEFAULT_COVERAGE_OUTPUT))
    parser.add_argument("--promotion-plan-output", default=str(DEFAULT_PLAN_OUTPUT))
    parser.add_argument("--runtime-batch-output", default=str(DEFAULT_BATCH_OUTPUT))
    parser.add_argument("--status-output", default=str(DEFAULT_STATUS_OUTPUT))
    parser.add_argument(
        "--update-small-anchor-store",
        action="store_true",
        help="Apply internal-seed runtime metadata to selected existing small anchors.",
    )
    args = parser.parse_args(argv)

    small_anchor_path = Path(args.small_anchor_store)
    payload = read_json_artifact(small_anchor_path)
    coverage = build_fooddb_runtime_coverage_matrix(small_anchor_payload=payload)
    plan = build_existing_anchor_promotion_plan(small_anchor_payload=payload)
    batch = build_internal_seed_runtime_anchor_batch(small_anchor_payload=payload)
    updated_payload = apply_internal_seed_runtime_anchor_batch_to_small_anchor_store(payload, batch)
    post_update_payload = updated_payload if args.update_small_anchor_store else payload
    status = build_fooddb_status_packet(
        small_anchor_payload=post_update_payload,
        coverage_matrix=build_fooddb_runtime_coverage_matrix(small_anchor_payload=post_update_payload),
        runtime_batch=batch,
    )

    write_json_artifact(Path(args.coverage_output), coverage)
    write_json_artifact(Path(args.promotion_plan_output), plan)
    write_json_artifact(Path(args.runtime_batch_output), batch)
    write_json_artifact(Path(args.status_output), status)

    if args.update_small_anchor_store:
        _write_small_anchor_store_preserving_layout(small_anchor_path, updated_payload, batch)

    print(
        json.dumps(
            {
                "claim_scope": status["claim_scope"],
                "runtime_truth_changed": batch["runtime_truth_changed"],
                "runtime_visible_anchor_count": status["runtime_visible_anchor_count"],
                "product_loop_integration_claimed": status["product_loop_integration_claimed"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_small_anchor_store_preserving_layout(
    path: Path,
    updated_payload: dict,
    runtime_batch: dict,
) -> None:
    text = path.read_text(encoding="utf-8-sig")
    updated_by_id = {
        item["anchor_id"]: item
        for item in updated_payload.get("anchors") or []
        if isinstance(item, dict) and item.get("anchor_id")
    }
    for anchor in runtime_batch.get("anchors") or []:
        anchor_id = anchor.get("anchor_id")
        updated = updated_by_id.get(anchor_id)
        if not anchor_id or not updated:
            continue
        try:
            start, end = _find_anchor_object_span(text, str(anchor_id))
        except ValueError:
            write_json_artifact(path, updated_payload)
            return
        text = f"{text[:start]}{_format_anchor_object(updated)}{text[end:]}"
    path.write_text(text, encoding="utf-8")


def _find_anchor_object_span(text: str, anchor_id: str) -> tuple[int, int]:
    marker = f'"anchor_id": "{anchor_id}"'
    marker_index = text.index(marker)
    line_start = text.rfind("\n    {", 0, marker_index)
    if line_start == -1:
        raise ValueError(f"Could not find anchor object start for {anchor_id}")
    start = line_start + 1
    brace_start = text.index("{", start)
    depth = 0
    in_string = False
    escaped = False
    for index in range(brace_start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1
    raise ValueError(f"Could not find anchor object end for {anchor_id}")


def _format_anchor_object(anchor: dict) -> str:
    dumped = json.dumps(anchor, ensure_ascii=True, indent=2, default=str)
    return "\n".join(f"    {line}" for line in dumped.splitlines())


if __name__ == "__main__":
    raise SystemExit(main())
