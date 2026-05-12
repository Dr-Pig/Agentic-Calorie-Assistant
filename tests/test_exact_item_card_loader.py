from __future__ import annotations

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)


def test_exact_item_card_loader_merges_batch_files_with_source_file_metadata() -> None:
    records = load_exact_item_card_seed_records()
    by_id = {str(record["item_id"]): record for record in records}

    record = by_id["exact_weichuan_prince_cup_noodle_pork_52g"]

    assert record["_fooddb_source_file"] == "app/knowledge/exact_item_cards_tw_batch_002.json"
    assert record["kcal"] == 262
    assert record["protein_g"] == 4.5
    assert record["carb_g"] == 30.8
    assert record["fat_g"] == 13.4
