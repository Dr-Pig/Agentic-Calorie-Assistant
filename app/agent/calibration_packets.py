from __future__ import annotations

from typing import Any


P0_CALIBRATION_PACKETS: dict[str, dict[str, Any]] = {
    "japanese_ramen": {
        "packet_id": "japanese_ramen",
        "title": "日式拉麵偏誤校正",
        "bias_notes": [
            "常被低估湯底油脂與背脂。",
            "喝湯與否會造成顯著熱量差距。",
        ],
        "high_calorie_sources": ["湯底油脂", "叉燒", "溏心蛋", "加麵"],
        "underestimated_factors": ["broth_consumption", "oil_rich_broth", "extra_noodles"],
        "useful_unresolved_info": ["broth_consumption", "extra_noodles", "richness_level"],
        "typical_adjustment_range": {"kcal_delta_low": 150, "kcal_delta_high": 350},
    },
    "taiwan_bento": {
        "packet_id": "taiwan_bento",
        "title": "台式便當偏誤校正",
        "bias_notes": [
            "炸主菜與配菜用油常被低估。",
            "白飯份量與滷汁額外熱量容易被忽略。",
        ],
        "high_calorie_sources": ["炸排", "白飯", "滷汁", "油炒配菜"],
        "underestimated_factors": ["main_protein_style", "rice_amount", "fried_side_count"],
        "useful_unresolved_info": ["main_protein_style", "rice_amount", "fried_side_count"],
        "typical_adjustment_range": {"kcal_delta_low": 120, "kcal_delta_high": 320},
    },
    "luwei_component_driven": {
        "packet_id": "luwei_component_driven",
        "title": "滷味/鹹水雞偏誤校正",
        "bias_notes": [
            "這類餐點熱量主要由夾了哪些料決定，不是固定份量。",
            "麵類、豆製品、丸餃類差異很大。",
        ],
        "high_calorie_sources": ["麵", "豆包", "丸餃類", "內臟類", "醬料"],
        "underestimated_factors": ["component_list", "component_count", "base_amount"],
        "useful_unresolved_info": ["component_list", "component_count", "base_amount"],
        "typical_adjustment_range": {"kcal_delta_low": 180, "kcal_delta_high": 450},
    },
    "poke_bowl": {
        "packet_id": "poke_bowl",
        "title": "Poke bowl 偏誤校正",
        "bias_notes": [
            "熱量常被 base 份量與醬料低估。",
            "酪梨、堅果、沙拉醬是主要變因。",
        ],
        "high_calorie_sources": ["base", "sauce", "avocado", "nuts"],
        "underestimated_factors": ["base_amount", "sauce_amount", "high_fat_toppings"],
        "useful_unresolved_info": ["base_amount", "sauce_amount", "high_fat_toppings"],
        "typical_adjustment_range": {"kcal_delta_low": 100, "kcal_delta_high": 280},
    },
    "banquet_shared_meal": {
        "packet_id": "banquet_shared_meal",
        "title": "喜酒/合菜偏誤校正",
        "bias_notes": [
            "關鍵不是整桌總量，而是一人實際分到多少。",
            "勾芡、炸物、湯品和甜點容易被忽略。",
        ],
        "high_calorie_sources": ["fried_shared_dishes", "sauced_dishes", "dessert", "soup"],
        "underestimated_factors": ["personal_share_portion", "dish_count", "dessert_taken"],
        "useful_unresolved_info": ["personal_share_portion", "dish_count", "dessert_taken"],
        "typical_adjustment_range": {"kcal_delta_low": 150, "kcal_delta_high": 500},
    },
    "donburi_rice_bowl": {
        "packet_id": "donburi_rice_bowl",
        "title": "日式/台式丼飯偏誤校正",
        "bias_notes": [
            "飯量常被低估（實際一碗約 220-280g 熟飯）。",
            "炸物吸油量容易被忽略。",
            "醬汁熱量常被忽略（約 30-50 kcal）。",
        ],
        "high_calorie_sources": ["炸蛋白質", "白飯", "醬汁", "油脂"],
        "underestimated_factors": ["rice_amount", "frying_oil", "sauce_amount", "protein_frying_style"],
        "useful_unresolved_info": ["rice_amount", "protein_size", "sauce_preference"],
        "typical_adjustment_range": {"kcal_delta_low": 100, "kcal_delta_high": 250},
    },
    "taiwan_noodle_dry": {
        "packet_id": "taiwan_noodle_dry",
        "title": "台式乾拌麵偏誤校正",
        "bias_notes": [
            "麵量常被低估（加大版本尤其容易被忽略）。",
            "炸醬/肉燥的油脂含量常被低估。",
            "拌麵的油脂容易被忽略（約 10-20 kcal）。",
        ],
        "high_calorie_sources": ["麵體", "炸醬", "肉燥", "拌油", "配料"],
        "underestimated_factors": ["noodle_amount", "sauce_oil", "meat_topping", "size_upgrade"],
        "useful_unresolved_info": ["noodle_size", "sauce_preference", "meat_amount"],
        "typical_adjustment_range": {"kcal_delta_low": 80, "kcal_delta_high": 200},
    },
    "chaoshou_dumplings": {
        "packet_id": "chaoshou_dumplings",
        "title": "抄手/水餃偏誤校正",
        "bias_notes": [
            "一顆抄手的熱量常被高估或低估（約 40-60 kcal/顆）。",
            "醬汁的熱量容易被忽略（約 15-30 kcal）。",
            "不辣版本不代表熱量低，可能只是少了辣油。",
        ],
        "high_calorie_sources": ["餡料", "皮", "醬汁", "香油"],
        "underestimated_factors": ["piece_count", "sauce_amount", "filling_ratio"],
        "useful_unresolved_info": ["piece_count", "sauce_preference"],
        "typical_adjustment_range": {"kcal_delta_low": 30, "kcal_delta_high": 80},
    },
}


def get_meal_calibration(packet_id: str) -> dict[str, Any] | None:
    return P0_CALIBRATION_PACKETS.get(str(packet_id or "").strip())


def suggest_calibration_packet(query: str) -> str | None:
    text = str(query or "").lower()
    rules = [
        (("拉麵", "豚骨", "味噌拉麵", "沾麵"), "japanese_ramen"),
        (("便當", "雞腿飯", "排骨飯"), "taiwan_bento"),
        (("滷味", "鹹水雞", "麻辣燙", "關東煮"), "luwei_component_driven"),
        (("poke", "波奇", "夏威夷拌飯"), "poke_bowl"),
        (("喜酒", "合菜", "桌菜"), "banquet_shared_meal"),
        (("丼", "丼飯", "炸雞", "豬排飯", "牛丼", "鰻魚飯"), "donburi_rice_bowl"),
        (("炸醬麵", "乾麵", "麻醬麵", "油麵", "板條"), "taiwan_noodle_dry"),
        (("抄手", "水餃", "餛飩", "雲吞", "水煎包"), "chaoshou_dumplings"),
    ]
    for keywords, packet_id in rules:
        if any(keyword.lower() in text for keyword in keywords):
            return packet_id
    return None
