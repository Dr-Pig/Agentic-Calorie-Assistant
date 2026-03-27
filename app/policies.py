from __future__ import annotations

HOME_COOKED_MARKERS = [
    "我媽煮",
    "媽媽煮",
    "我爸煮",
    "家裡煮",
    "自己煮",
    "朋友做",
    "朋友煮",
    "家常",
    "煎給我",
    "做給我",
]

MEAL_CATEGORY_POLICY: dict[str, dict[str, list[str] | dict[str, str]]] = {
    "drink": {
        "high_impact_modifiers": ["sugar_level", "cup_size", "toppings"],
        "implicit_components": ["糖", "飲料基底"],
        "default_assumptions": {"sugar_level": "微糖", "cup_size": "中杯"},
    },
    "breakfast_bread_wrap": {
        "high_impact_modifiers": ["portion_size", "extra_sauce", "drink_sugar_level"],
        "implicit_components": ["主食", "蛋白質", "抹醬或油脂"],
        "default_assumptions": {"portion_size": "一般份"},
    },
    "rice_bowl_bento": {
        "high_impact_modifiers": ["rice_portion", "portion_size", "fried_or_sauce"],
        "implicit_components": ["白飯", "主菜", "配菜油脂"],
        "default_assumptions": {"rice_portion": "一碗內"},
    },
    "noodle_soup": {
        "high_impact_modifiers": ["noodle_portion", "broth_consumption", "extra_toppings"],
        "implicit_components": ["麵", "湯底", "油脂", "肉類或配菜"],
        "default_assumptions": {"broth_consumption": "部分飲用"},
    },
    "fried_snack": {
        "high_impact_modifiers": ["portion_size", "sauce", "drink_pairing"],
        "implicit_components": ["油炸主體", "調味粉或醬"],
        "default_assumptions": {"portion_size": "一般份"},
    },
    "soup_side": {
        "high_impact_modifiers": ["serving_size"],
        "implicit_components": ["湯底"],
        "default_assumptions": {"serving_size": "一碗"},
    },
    "dessert": {
        "high_impact_modifiers": ["portion_size", "toppings"],
        "implicit_components": ["糖", "油脂或乳製品"],
        "default_assumptions": {"portion_size": "一般份"},
    },
    "packaged_item": {"high_impact_modifiers": [], "implicit_components": [], "default_assumptions": {}},
    "chain_menu_item": {"high_impact_modifiers": [], "implicit_components": [], "default_assumptions": {}},
    "homemade_or_private_meal": {
        "high_impact_modifiers": ["main_components", "portion_size"],
        "implicit_components": [],
        "default_assumptions": {},
    },
    "unknown": {"high_impact_modifiers": ["main_components"], "implicit_components": [], "default_assumptions": {}},
}


def is_home_cooked_signal(text: str) -> bool:
    normalized = text.strip()
    return any(marker in normalized for marker in HOME_COOKED_MARKERS)
