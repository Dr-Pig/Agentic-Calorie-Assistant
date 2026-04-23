"""Nutrition context formatting helpers for LLM system prompts."""
from __future__ import annotations

from typing import Any


def knowledge_context(snippets: list[dict[str, Any]]) -> str:
    if not snippets:
        return "- No supporting evidence was retrieved."
    lines = [
        "| ID | Item | Lane | Tier | Identity | Kcal | Note |",
        "|:---|:---|:---|:---|:---|:---|:---|",
    ]
    for item in snippets[:5]:
        evidence_id = str(item.get("evidence_id") or "")
        title = str(item.get("title") or item.get("name") or "")
        lane = str(item.get("retrieval_lane") or "support_lane")
        tier = str(item.get("source_tier") or "")
        identity = str(item.get("identity_confidence") or item.get("match_confidence") or "none")
        kcal = item.get("label_kcal") or item.get("kcal") or ""
        note = str(item.get("snippet") or item.get("summary") or item.get("note") or "").replace("\n", " ").strip()
        lines.append(f"| {evidence_id} | {title} | {lane} | {tier} | {identity} | {kcal} | {note} |")
    return "\n".join(lines)


def risk_context(packet: dict[str, Any]) -> str:
    lines: list[str] = []
    if packet.get("risk_flags"):
        lines.append(f"- risk_flags: {', '.join(str(item) for item in packet['risk_flags'])}")
    for item in packet.get("review_focus", []):
        lines.append(f"- review_focus: {item}")
    for item in packet.get("must_ask_if_uncertain", []):
        lines.append(f"- must_ask_if_uncertain: {item}")
    for item in packet.get("portion_clues", {}).get("review_focus", []):
        lines.append(f"- portion_review_focus: {item}")
    return "\n".join(lines) if lines else "- no additional risk context"


def calibration_context(packet: dict[str, Any]) -> str:
    """Format calibration packet for LLM context in system prompt."""
    if not packet:
        return "- No specific calibration context for this dish type."
    lines = []
    title = packet.get("title", "")
    if title:
        lines.append(f"[{title}]")
    bias_notes = packet.get("bias_notes", [])
    if bias_notes:
        for note in bias_notes:
            lines.append(f"- 注意: {note}")
    high_calorie = packet.get("high_calorie_sources", [])
    if high_calorie:
        lines.append(f"- 高熱量來源: {', '.join(str(item) for item in high_calorie)}")
    adjustment = packet.get("typical_adjustment_range", {})
    if adjustment:
        low = adjustment.get("kcal_delta_low", "")
        high = adjustment.get("kcal_delta_high", "")
        if low and high:
            lines.append(f"- 典型調整範圍: +{low} ~ +{high} kcal")
    return "\n".join(lines) if lines else "- No specific calibration context for this dish type."
