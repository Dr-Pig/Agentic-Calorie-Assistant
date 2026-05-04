from __future__ import annotations

P0_MODIFIERS = ("cup_size", "rice_portion", "sugar_level")
P1_STAGED_MODIFIERS = ("common add-ons",)
P2_STAGED_MODIFIERS = (
    "preparation method / fried-braised-grilled style metadata posture only",
)

CATALOG_SUPPORTED_REPORT_ONLY_POSTURE = "catalog_supported_report_only"
NON_P0_STAGED_POSTURE = "staged_not_treated_as_p0"
MODIFIER_ACTIVATION_POSTURE = "staged_modifier_priority_p0_p1_p2"


def build_modifier_limitation_labels() -> list[str]:
    return [
        *[f"P0:{modifier}" for modifier in P0_MODIFIERS],
        *[f"P1:{modifier}" for modifier in P1_STAGED_MODIFIERS],
        *[f"P2:{modifier}" for modifier in P2_STAGED_MODIFIERS],
    ]


def build_staged_policy_modifier_labels() -> list[str]:
    return [*P1_STAGED_MODIFIERS, *P2_STAGED_MODIFIERS]


def build_modifier_activation_posture() -> dict[str, object]:
    return {
        "P0_supported_modifiers": list(P0_MODIFIERS),
        "P1_staged_modifiers": list(P1_STAGED_MODIFIERS),
        "P2_staged_modifiers": list(P2_STAGED_MODIFIERS),
        "unsupported_or_not_yet_covered_modifiers": [],
        "runtime_truth_promoted": False,
        "posture": MODIFIER_ACTIVATION_POSTURE,
    }


__all__ = [
    "CATALOG_SUPPORTED_REPORT_ONLY_POSTURE",
    "MODIFIER_ACTIVATION_POSTURE",
    "NON_P0_STAGED_POSTURE",
    "P0_MODIFIERS",
    "P1_STAGED_MODIFIERS",
    "P2_STAGED_MODIFIERS",
    "build_modifier_activation_posture",
    "build_modifier_limitation_labels",
    "build_staged_policy_modifier_labels",
]
