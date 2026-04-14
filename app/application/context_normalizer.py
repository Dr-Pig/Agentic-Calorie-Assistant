from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def canonicalize_lookup_text(text: str) -> str:
    normalized = normalize_text(text).lower()
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def lookup_key(text: str) -> str:
    return "".join(re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", canonicalize_lookup_text(text)))


def lookup_tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", canonicalize_lookup_text(text)) if len(token) > 1]


_PORTION_CLUE_PATTERNS = (
    "小杯",
    "中杯",
    "大杯",
    "特大杯",
    "超大杯",
    "tall",
    "grande",
    "venti",
)

_DRINK_LIKE_TOKENS = (
    "那堤",
    "拿鐵",
    "latte",
    "咖啡",
    "奶茶",
    "紅茶",
    "綠茶",
    "茶",
    "奶",
)

_PACKAGED_DRINK_IDENTITY_CUES = (
    "ml",
    "mL",
    "瓶",
    "罐",
    "寶特瓶",
    "鋁箔",
    "紙盒",
    "bottle",
    "can",
    "pack",
    "packaged",
    "7-11",
    "全家",
    "familymart",
    "city cafe",
)


def extract_portion_clues(text: str) -> list[str]:
    normalized = normalize_text(text).lower()
    matched: list[str] = []
    for pattern in _PORTION_CLUE_PATTERNS:
        if pattern.lower() in normalized:
            matched.append(pattern)
    return matched


def extract_drink_customization_clues(text: str) -> list[str]:
    normalized = normalize_text(text).lower()
    patterns = (
        "全糖",
        "半糖",
        "微糖",
        "少糖",
        "無糖",
        "去冰",
        "少冰",
        "微冰",
        "正常冰",
        "熱",
        "溫",
        "鮮奶",
        "奶精",
        "加珍珠",
    )
    matched: list[str] = []
    for pattern in patterns:
        if pattern.lower() in normalized:
            matched.append(pattern)
    return matched


def looks_like_standardized_drink(text: str, evidence_items: list[dict[str, Any]] | None = None) -> bool:
    haystacks = [normalize_text(text).lower()]
    for item in evidence_items or []:
        haystacks.append(normalize_text(str(item.get("title") or "")).lower())
        haystacks.extend(normalize_text(str(alias)).lower() for alias in item.get("aliases", []) if str(alias).strip())
    combined = " ".join(haystacks)
    return any(token.lower() in combined for token in _DRINK_LIKE_TOKENS)


def has_packaged_drink_identity_cue(text: str) -> bool:
    normalized = normalize_text(text).lower()
    return any(token.lower() in normalized for token in _PACKAGED_DRINK_IDENTITY_CUES)


def normalize_user_input_for_estimation(text: str) -> dict[str, Any]:
    raw = normalize_text(text)
    return {
        "raw_text": raw,
        "normalized_text": raw,
        "normalizer_applied": False,
        "notes": ["normalization_patches_removed", "raw_signal_preserved"],
    }
