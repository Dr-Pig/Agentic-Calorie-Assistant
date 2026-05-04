from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.food_evidence_tfda_promotion import (  # noqa: E402
    apply_selected_anchor_metadata_to_small_anchor_store,
    build_tfda_batch_promotion_artifact,
    build_tfda_per100g_source_evidence_artifact,
    build_tfda_selected_anchor_artifact,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_CANDIDATES = ROOT / "artifacts" / "accurate_intake_food_evidence_candidates.json"
DEFAULT_AUTO_ELIGIBLE = ROOT / "artifacts" / "accurate_intake_food_auto_eligible_batch.json"
DEFAULT_SOURCE_OUTPUT = ROOT / "app" / "knowledge" / "tfda_per100g_source_evidence_tw.json"
DEFAULT_ANCHOR_OUTPUT = ROOT / "artifacts" / "accurate_intake_tfda_selected_common_serving_anchors.json"
DEFAULT_REPORT_OUTPUT = ROOT / "artifacts" / "accurate_intake_tfda_batch_promotion.json"
DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Promote TFDA per-100g source evidence and selected MVP portion anchors."
    )
    parser.add_argument("--candidate-json", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--auto-eligible-json", default=str(DEFAULT_AUTO_ELIGIBLE))
    parser.add_argument("--source-evidence-output", default=str(DEFAULT_SOURCE_OUTPUT))
    parser.add_argument("--anchor-output", default=str(DEFAULT_ANCHOR_OUTPUT))
    parser.add_argument("--report-output", default=str(DEFAULT_REPORT_OUTPUT))
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument(
        "--update-small-anchor-store",
        action="store_true",
        help="Apply selected common-serving metadata to the tracked small anchor store.",
    )
    args = parser.parse_args(argv)

    promotion = build_tfda_batch_promotion_artifact(
        candidate_artifact=read_json_artifact(Path(args.candidate_json)),
        auto_eligible_artifact=read_json_artifact(Path(args.auto_eligible_json)),
    )
    source_evidence = build_tfda_per100g_source_evidence_artifact(promotion)
    selected_anchors = build_tfda_selected_anchor_artifact(promotion)

    write_json_artifact(Path(args.source_evidence_output), source_evidence)
    write_json_artifact(Path(args.anchor_output), selected_anchors)
    write_json_artifact(Path(args.report_output), promotion)

    if args.update_small_anchor_store:
        path = Path(args.small_anchor_store)
        payload = read_json_artifact(path)
        updated = apply_selected_anchor_metadata_to_small_anchor_store(payload, selected_anchors)
        _write_small_anchor_store_preserving_layout(path, updated, selected_anchors)

    print(
        json.dumps(
            {
                "claim_scope": promotion["claim_scope"],
                "source_evidence_count": promotion["summary"]["source_evidence_count"],
                "selected_runtime_anchor_count": promotion["summary"]["selected_runtime_anchor_count"],
                "runtime_truth_changed": promotion["runtime_truth_changed"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_small_anchor_store_preserving_layout(
    path: Path,
    updated_payload: dict,
    selected_anchor_artifact: dict,
) -> None:
    """Patch selected anchor objects without reformatting the entire store."""
    text = path.read_text(encoding="utf-8-sig")
    updated_by_id = {
        item["anchor_id"]: item
        for item in updated_payload.get("anchors") or []
        if isinstance(item, dict) and item.get("anchor_id")
    }
    for anchor in selected_anchor_artifact.get("anchors") or []:
        anchor_id = anchor.get("anchor_id")
        updated = updated_by_id.get(anchor_id)
        if not anchor_id or not updated:
            continue
        start, end = _find_anchor_object_span(text, str(anchor_id))
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
