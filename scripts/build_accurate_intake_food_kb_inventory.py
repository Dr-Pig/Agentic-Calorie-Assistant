from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SMALL_ANCHOR_PATH = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
EXACT_ITEM_PATH = ROOT / "app" / "knowledge" / "exact_item_cards_tw.json"
BASE_NUTRITION_DB_PATH = ROOT / "app" / "knowledge" / "base_nutrition_db.json"
TFDA_CANDIDATES_PATH = ROOT / ".logs" / "tfda_base_candidates_tmp.json"
TFDA_XLSX_PATH = ROOT / ".logs" / "FDA_food_nutrition_2024.xlsx"
DATA_BUILD_PATH = ROOT / "data_build"
DEFAULT_OUTPUT = ROOT / "docs" / "quality" / "accurate_intake_food_kb_v1_inventory.json"


def build_food_kb_inventory() -> dict[str, Any]:
    anchors = _load_json_list(SMALL_ANCHOR_PATH, "anchors")
    exact_cards = _load_json_list(EXACT_ITEM_PATH, "cards")
    semantic_only = [row for row in anchors if row.get("record_kind") == "generic_semantic_only"]
    generic_anchors = [row for row in anchors if row.get("record_kind") == "generic_anchor"]

    return {
        "artifact_type": "accurate_intake_food_kb_v1_inventory",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "scope": "local_evidence_support_inventory",
        "truth_owner": "none",
        "mutation_authority": "none",
        "food_seed_can_decide_logged_draft_or_no_mutation": False,
        "live_llm_required": False,
        "web_tavily_required": False,
        "production_db_required": False,
        "repo_contained_seed_counts": {
            "small_anchor_total": len(anchors),
            "generic_anchor": len(generic_anchors),
            "generic_semantic_only": len(semantic_only),
            "exact_item_cards": len(exact_cards),
        },
        "repo_contained_seed_paths": {
            "small_anchor_store": _rel(SMALL_ANCHOR_PATH),
            "exact_item_cards": _rel(EXACT_ITEM_PATH),
        },
        "tfda_base_pipeline": {
            "base_nutrition_db_present": BASE_NUTRITION_DB_PATH.exists(),
            "staging_inputs_present": TFDA_CANDIDATES_PATH.exists() and TFDA_XLSX_PATH.exists(),
            "data_build_package_present": DATA_BUILD_PATH.exists(),
            "base_nutrition_db_path": _rel(BASE_NUTRITION_DB_PATH),
            "staging_candidate_path": _rel(TFDA_CANDIDATES_PATH),
            "staging_xlsx_path": _rel(TFDA_XLSX_PATH),
        },
        "coverage_gaps": _coverage_gaps(),
        "recommended_pr_slices": _recommended_pr_slices(),
        "not_claiming": [
            "food_knowledge_is_product_truth",
            "food_knowledge_can_authorize_mutation",
            "food_knowledge_can_update_ledger",
            "food_knowledge_can_decide_logged_or_draft",
            "tfda_pipeline_active",
            "live_food_search_ready",
        ],
        "readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
    }


def write_food_kb_inventory(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    inventory = build_food_kb_inventory()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return inventory


def _load_json_list(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = data.get(key, []) if isinstance(data, dict) else data
    return [dict(row) for row in rows if isinstance(row, dict)]


def _coverage_gaps() -> list[dict[str, Any]]:
    return [
        _gap("taiwan_breakfast_staples", "generic_anchor"),
        _gap("taiwan_lunch_dinner_staples", "generic_anchor"),
        _gap("drink_modifiers_and_chain_drinks", "generic_anchor"),
        _gap("basket_components_common_items", "generic_anchor"),
        _gap("home_cooked_plate_components", "generic_anchor"),
        _gap("exact_item_card_corpus", "exact_item_card"),
        _gap("tfda_base_nutrition_pipeline", "pipeline_infra"),
    ]


def _gap(gap_id: str, recommended_role: str) -> dict[str, str]:
    return {
        "gap_id": gap_id,
        "recommended_role": recommended_role,
        "semantic_authority": "none",
        "source_posture": "candidate_evidence_only",
    }


def _recommended_pr_slices() -> list[dict[str, str]]:
    return [
        _slice("coverage_tests_first"),
        _slice("generic_anchor_seed_batches"),
        _slice("listed_basket_component_expansion"),
        _slice("exact_item_card_expansion"),
        _slice("tfda_pipeline_repair"),
    ]


def _slice(slice_id: str) -> dict[str, str]:
    return {
        "slice_id": slice_id,
        "must_preserve": "NutritionEvidenceStorePort",
        "forbidden": "food_seed_semantic_or_mutation_authority",
    }


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    write_food_kb_inventory(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
