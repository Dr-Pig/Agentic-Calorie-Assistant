from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExecutionGuardResult:
    ok: bool
    violations: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MacroDisplayGuardResult:
    display_status: str
    macro_kcal: int
    macro_kcal_delta: int
    guard_reason: str
    alignment_warning: bool


def validate_onboarding_seed(
    *,
    recommended_target_kcal: int,
    safety_floor_kcal: int,
) -> ExecutionGuardResult:
    violations: list[str] = []
    if recommended_target_kcal <= 0:
        violations.append("daily_target_missing")
    if recommended_target_kcal < safety_floor_kcal:
        violations.append("daily_target_below_safety_floor")
    return ExecutionGuardResult(ok=not violations, violations=tuple(violations))


def validate_intake_persistence(
    *,
    action: str,
    canonical_commit_present: bool,
) -> ExecutionGuardResult:
    violations: list[str] = []
    if action not in {"save_completed_log", "save_draft_log"}:
        violations.append("unexpected_persistence_action")
    if action == "save_completed_log" and not canonical_commit_present:
        violations.append("missing_canonical_commit")
    return ExecutionGuardResult(ok=not violations, violations=tuple(violations))


def validate_macro_alignment(
    *,
    estimated_kcal: int,
    protein_g: int,
    carb_g: int,
    fat_g: int,
) -> ExecutionGuardResult:
    """Validate that kcal ≈ (protein*4 + carbs*4 + fat*9) within 10% tolerance."""
    calculated = (protein_g * 4) + (carb_g * 4) + (fat_g * 9)
    if calculated <= 0:
        return ExecutionGuardResult(ok=True)
    
    divergence = abs(estimated_kcal - calculated) / calculated
    violations: list[str] = []
    if divergence > 0.10:
        violations.append("macro_divergence_too_high")
    
    return ExecutionGuardResult(ok=not violations, violations=tuple(violations))


def evaluate_macro_display(
    *,
    estimated_kcal: int,
    protein_g: int,
    carb_g: int,
    fat_g: int,
) -> MacroDisplayGuardResult:
    macro_kcal = (protein_g * 4) + (carb_g * 4) + (fat_g * 9)
    if macro_kcal <= 0:
        return MacroDisplayGuardResult(
            display_status="hide",
            macro_kcal=macro_kcal,
            macro_kcal_delta=0,
            guard_reason="macro_missing",
            alignment_warning=False,
        )
    delta = abs(int(estimated_kcal or 0) - macro_kcal)
    tolerance = max(60, int(max(int(estimated_kcal or 0), 0) * 0.15))
    if int(estimated_kcal or 0) >= 700:
        tolerance = max(80, int(max(int(estimated_kcal or 0), 0) * 0.12))
    show = delta <= tolerance
    return MacroDisplayGuardResult(
        display_status="show" if show else "hide",
        macro_kcal=macro_kcal,
        macro_kcal_delta=delta,
        guard_reason="aligned" if show else "macro_alignment_warning",
        alignment_warning=not show,
    )
