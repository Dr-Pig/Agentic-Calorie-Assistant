from __future__ import annotations

HOME_COOKED_MARKERS = [
    "我媽煮",
    "我爸煮",
    "家裡煮",
    "自己煮",
    "朋友做",
    "女朋友做",
    "男朋友做",
    "煮給我的",
    "做給我的",
    "家常",
]


def is_home_cooked_signal(text: str) -> bool:
    normalized = text.strip()
    return any(marker in normalized for marker in HOME_COOKED_MARKERS)
