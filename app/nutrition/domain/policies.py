from __future__ import annotations


HOME_COOKED_MARKERS = [
    "我媽煮",
    "媽媽煮",
    "家裡煮",
    "自己煮",
    "我煮的",
    "朋友煮",
    "家常菜",
    "晚餐",
]


def is_home_cooked_signal(text: str) -> bool:
    normalized = text.strip()
    return any(marker in normalized for marker in HOME_COOKED_MARKERS)
