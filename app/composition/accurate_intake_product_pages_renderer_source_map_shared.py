from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_PAGES = ("chat", "today", "body")

FORBIDDEN_SEMANTIC_FRAGMENTS = (
    "routeByKeyword",
    "rawTextRouting",
    "message.includes",
    "input.includes",
    "text.includes",
    "switch (text",
    "estimateKcal",
    "estimatedKcal",
    "calculateTdee",
    "calculateBmr",
    "activityMultiplier",
    "dailyDeficit =",
    "budget - consumed",
    "budget_kcal - consumed_kcal",
    "daily_target_kcal - consumed_kcal",
    "remaining =",
    "remainingKcal =",
    "workflow_effect =",
    "target_attachment =",
    "final_action =",
    "mutation_allowed =",
    "inferManagerContext",
    "inferEvidenceGap",
    "selectTarget",
    "localStorage",
    "sessionStorage",
)


__all__ = ["FORBIDDEN_SEMANTIC_FRAGMENTS", "REQUIRED_PAGES", "ROOT"]
