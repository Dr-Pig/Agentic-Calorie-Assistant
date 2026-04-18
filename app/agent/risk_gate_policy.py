from __future__ import annotations

import re
from typing import Any

from .knowledge_loader import _meal_templates, _risk_profiles
from .knowledge_lookup_normalizer import _normalize, _normalize_lower


def _match_exact_keywords(profile: dict[str, Any], lowered: str) -> list[str]:
    hits: list[str] = []
    for keyword in profile.get("keywords", []):
        normalized = _normalize_lower(str(keyword))
        if normalized and normalized in lowered:
            hits.append(f"keyword:{keyword}")
    return hits


def _match_patterns(profile: dict[str, Any], text: str) -> list[str]:
    hits: list[str] = []
    for pattern in profile.get("patterns", []):
        raw = str(pattern).strip()
        if not raw:
            continue
        try:
            if re.search(raw, text, flags=re.IGNORECASE):
                hits.append(f"pattern:{raw}")
        except re.error:
            continue
    return hits


def _match_shop_aliases(profile: dict[str, Any], lowered: str) -> list[str]:
    hits: list[str] = []
    for alias in profile.get("shop_aliases", []):
        normalized = _normalize_lower(str(alias))
        if normalized and normalized in lowered:
            hits.append(f"shop:{alias}")
    return hits


def _extract_portion_clues(user_input: str, profiles: list[dict[str, Any]]) -> dict[str, Any]:
    matched: list[str] = []
    review_focus: list[str] = []
    lowered = _normalize_lower(user_input)
    for profile in profiles:
        for clue in profile.get("portion_clues", []):
            normalized = _normalize_lower(str(clue))
            if normalized and normalized in lowered:
                matched.append(str(clue))
                review_focus.append(f"注意份量詞：{clue}")
    return {
        "matched": list(dict.fromkeys(matched)),
        "review_focus": list(dict.fromkeys(review_focus)),
    }


def build_gate_packet(user_input: str, *, components: list[str] | None = None) -> dict[str, Any]:
    text = _normalize(user_input)
    lowered = text.lower()
    risk_flags: list[str] = []
    review_focus: list[str] = []
    must_ask_if_uncertain: list[str] = []
    required_checks: dict[str, list[dict[str, Any]]] = {}
    private_only = False
    risk_match_reasons: dict[str, list[str]] = {}

    profiles = _risk_profiles()
    for profile in profiles:
        reasons = (
            _match_exact_keywords(profile, lowered)
            + _match_patterns(profile, text)
            + _match_shop_aliases(profile, lowered)
        )
        if not reasons:
            continue
        risk_key = str(profile["risk_key"])
        risk_flags.append(risk_key)
        risk_match_reasons[risk_key] = reasons
        review_focus.extend(str(item) for item in profile.get("review_focus", []))
        must_ask_if_uncertain.extend(str(item) for item in profile.get("must_ask_if_uncertain", []))
        required_checks[risk_key] = list(profile.get("required_checks", []))
        private_only = private_only or bool(profile.get("private_only"))

    portion_clues = _extract_portion_clues(text, profiles)
    review_focus.extend(portion_clues["review_focus"])

    return {
        "risk_flags": list(dict.fromkeys(risk_flags)),
        "review_focus": list(dict.fromkeys(review_focus)),
        "must_ask_if_uncertain": list(dict.fromkeys(must_ask_if_uncertain)),
        "portion_clues": portion_clues,
        "required_checks": required_checks,
        "components_seen": [item.strip() for item in (components or []) if isinstance(item, str) and item.strip()],
        "private_only": private_only,
        "risk_match_reasons": risk_match_reasons,
        "schema_version": "v10.1-risk-gate.v2",
    }


def match_meal_template(user_input: str, risk_packet: dict[str, Any] | None = None) -> dict[str, Any] | None:
    text = _normalize(user_input)
    lowered = text.lower()
    risk_flags = set((risk_packet or {}).get("risk_flags", []))
    best: tuple[int, dict[str, Any]] | None = None
    for template in _meal_templates():
        score = 0
        category = str(template.get("category", "")).strip()
        if category and category in risk_flags:
            score += 6
        for keyword in template.get("trigger_keywords", []):
            normalized = _normalize_lower(str(keyword))
            if normalized and normalized in lowered:
                score += 5
        for alias in template.get("aliases", []):
            normalized = _normalize_lower(str(alias))
            if normalized and normalized in lowered:
                score += 6
        for pattern in template.get("trigger_patterns", []):
            raw = str(pattern).strip()
            if not raw:
                continue
            try:
                if re.search(raw, text, flags=re.IGNORECASE):
                    score += 4
            except re.error:
                continue
        if score <= 0:
            continue
        if best is None or score > best[0]:
            best = (score, template)
    if best is None:
        return None
    return dict(best[1])
