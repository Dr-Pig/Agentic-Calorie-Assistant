from __future__ import annotations

from typing import Any


EXTRA_BASE_NUTRITION_ALIASES: dict[str, list[str]] = {
    "barley-kernels": ["大麥", "麥仁"],
    "barley-flakes": ["大麥片", "燕麥片替代"],
    "sweet-corn": ["玉米"],
    "yam": ["山藥"],
    "soybeans-dry": ["黃豆", "大豆"],
    "wood-ear-mushroom": ["黑木耳", "木耳"],
    "white-fungus": ["白木耳", "銀耳"],
    "shiitake-mushroom": ["香菇"],
    "king-oyster-mushroom": ["杏鮑菇"],
    "daikon": ["白蘿蔔", "蘿蔔"],
    "cauliflower": ["花椰菜", "白花椰菜"],
    "napa-cabbage": ["白菜", "大白菜"],
    "tomato": ["番茄", "牛番茄"],
    "papaya": ["木瓜"],
    "kiwi": ["奇異果", "綠奇異果"],
    "banana": ["香蕉"],
    "guava": ["芭樂", "番石榴"],
    "apple": ["蘋果"],
    "avocado": ["酪梨", "牛油果"],
}


def merged_base_nutrition_aliases(record: dict[str, Any]) -> list[str]:
    record_id = str(record.get("id") or "").strip()
    aliases = [str(record.get("title") or "").strip()]
    aliases.extend(str(item).strip() for item in record.get("aliases", []) if str(item).strip())
    aliases.extend(EXTRA_BASE_NUTRITION_ALIASES.get(record_id, []))

    seen: set[str] = set()
    merged: list[str] = []
    for alias in aliases:
        lowered = alias.lower()
        if not alias or lowered in seen:
            continue
        seen.add(lowered)
        merged.append(alias)
    return merged
