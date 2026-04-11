from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ObservationQualityPosture = Literal["insufficient_data", "ready"]
LoggingQualityPosture = Literal["insufficient_data", "logging_quality_first", "monitor_only"]
CalibrationPosture = Literal[
    "insufficient_data",
    "logging_quality_first",
    "monitor_only",
    "calibration_candidate",
    "high_confidence_mismatch",
]
IntakeEstimationBiasPosture = Literal[
    "neutral",
    "likely_underestimate",
    "likely_overestimate",
    "mixed_uncertainty",
]
MismatchAttribution = Literal[
    "likely_logging_gap",
    "likely_intake_underestimate",
    "likely_expenditure_shift",
    "likely_noise_only",
    "mixed_uncertainty",
]
DeficitRealityStatus = Literal["no_clear_deficit", "likely_deficit", "likely_maintenance", "likely_surplus"]
CalibrationConfidence = Literal["low", "medium", "high"]
DecisionMode = Literal["deterministic"]

MIN_OBSERVATION_WINDOW_DAYS = 14
MIN_BODY_OBSERVATION_COUNT = 5
MIN_INTAKE_COVERAGE = 0.80


@dataclass(frozen=True)
class CalibrationModelInputs:
    body_plan_estimated_tdee_kcal: int
    observation_window_days: int
    body_observation_count: int
    intake_coverage: float
    operating_expenditure_shift_kcal: int = 0
    trend_mismatch_consistency: float = 0.0
    trend_volatility: float = 0.0
    logging_gap_ratio: float = 0.0
    late_logged_meal_ratio: float = 0.0
    rough_meal_ratio: float = 0.0
    rescue_overlay_influence: float = 0.0


@dataclass(frozen=True)
class TrendWindowSummary:
    window_days: int
    observation_count: int
    intake_coverage: float
    rescue_overlay_influence: float
    trend_volatility: float
    is_valid: bool


@dataclass(frozen=True)
class CalibrationModelResult:
    decision_mode: DecisionMode
    decision_reason: str
    calibration_posture: CalibrationPosture
    observation_quality_posture: ObservationQualityPosture
    logging_quality_posture: LoggingQualityPosture
    trend_window_summary: TrendWindowSummary
    operating_expenditure_estimate_kcal: int
    intake_estimation_bias_posture: IntakeEstimationBiasPosture
    deficit_reality_status: DeficitRealityStatus
    mismatch_attribution: MismatchAttribution
    calibration_confidence: CalibrationConfidence
    proposal_eligibility: bool


def _validate_ratio(name: str, value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0")
    return float(value)


def _validate_inputs(inputs: CalibrationModelInputs) -> CalibrationModelInputs:
    if inputs.body_plan_estimated_tdee_kcal <= 0:
        raise ValueError("body_plan_estimated_tdee_kcal must be positive")
    if inputs.observation_window_days <= 0:
        raise ValueError("observation_window_days must be positive")
    if inputs.body_observation_count < 0:
        raise ValueError("body_observation_count must be non-negative")
    return CalibrationModelInputs(
        body_plan_estimated_tdee_kcal=int(inputs.body_plan_estimated_tdee_kcal),
        observation_window_days=int(inputs.observation_window_days),
        body_observation_count=int(inputs.body_observation_count),
        intake_coverage=_validate_ratio("intake_coverage", float(inputs.intake_coverage)),
        operating_expenditure_shift_kcal=int(inputs.operating_expenditure_shift_kcal),
        trend_mismatch_consistency=_validate_ratio("trend_mismatch_consistency", float(inputs.trend_mismatch_consistency)),
        trend_volatility=_validate_ratio("trend_volatility", float(inputs.trend_volatility)),
        logging_gap_ratio=_validate_ratio("logging_gap_ratio", float(inputs.logging_gap_ratio)),
        late_logged_meal_ratio=_validate_ratio("late_logged_meal_ratio", float(inputs.late_logged_meal_ratio)),
        rough_meal_ratio=_validate_ratio("rough_meal_ratio", float(inputs.rough_meal_ratio)),
        rescue_overlay_influence=_validate_ratio("rescue_overlay_influence", float(inputs.rescue_overlay_influence)),
    )


def _classify_observation_quality(inputs: CalibrationModelInputs) -> ObservationQualityPosture:
    if inputs.observation_window_days < MIN_OBSERVATION_WINDOW_DAYS or inputs.body_observation_count < MIN_BODY_OBSERVATION_COUNT:
        return "insufficient_data"
    return "ready"


def _classify_logging_quality(inputs: CalibrationModelInputs, observation_quality: ObservationQualityPosture) -> LoggingQualityPosture:
    if observation_quality == "insufficient_data":
        return "insufficient_data"
    if inputs.intake_coverage < MIN_INTAKE_COVERAGE:
        return "logging_quality_first"
    if inputs.logging_gap_ratio >= 0.20 or inputs.late_logged_meal_ratio >= 0.25 or inputs.rough_meal_ratio >= 0.30:
        return "logging_quality_first"
    return "monitor_only"


def _signal_strength(inputs: CalibrationModelInputs) -> int:
    return abs(int(inputs.operating_expenditure_shift_kcal))


def _classify_mismatch_attribution(inputs: CalibrationModelInputs, logging_quality: LoggingQualityPosture) -> MismatchAttribution:
    strength = _signal_strength(inputs)
    if strength < 120 or inputs.trend_volatility >= 0.65:
        return "likely_noise_only"
    if logging_quality == "logging_quality_first":
        return "likely_logging_gap" if inputs.operating_expenditure_shift_kcal >= 0 else "mixed_uncertainty"
    if inputs.logging_gap_ratio >= 0.15 or inputs.late_logged_meal_ratio >= 0.20 or inputs.rough_meal_ratio >= 0.25:
        return "likely_intake_underestimate" if inputs.operating_expenditure_shift_kcal >= 0 else "likely_logging_gap"
    return "likely_expenditure_shift"


def _classify_bias_posture(inputs: CalibrationModelInputs, logging_quality: LoggingQualityPosture) -> IntakeEstimationBiasPosture:
    strength = _signal_strength(inputs)
    if logging_quality == "insufficient_data":
        return "neutral"
    if logging_quality == "logging_quality_first":
        if inputs.operating_expenditure_shift_kcal > 0:
            return "likely_underestimate"
        if inputs.operating_expenditure_shift_kcal < 0:
            return "likely_overestimate"
        return "mixed_uncertainty"
    if strength < 120:
        return "neutral"
    if inputs.logging_gap_ratio >= 0.15 or inputs.late_logged_meal_ratio >= 0.20 or inputs.rough_meal_ratio >= 0.25:
        return "likely_underestimate" if inputs.operating_expenditure_shift_kcal >= 0 else "likely_overestimate"
    if inputs.trend_volatility >= 0.50:
        return "mixed_uncertainty"
    return "neutral"


def _classify_posture(inputs: CalibrationModelInputs, observation_quality: ObservationQualityPosture, logging_quality: LoggingQualityPosture) -> CalibrationPosture:
    if observation_quality == "insufficient_data":
        return "insufficient_data"
    if logging_quality == "logging_quality_first":
        return "logging_quality_first"

    strength = _signal_strength(inputs)
    if inputs.trend_volatility >= 0.65 or strength < 120:
        return "monitor_only"
    if strength >= 300 and inputs.trend_mismatch_consistency >= 0.75 and inputs.trend_volatility <= 0.30:
        return "high_confidence_mismatch"
    if strength >= 180 and inputs.trend_mismatch_consistency >= 0.60 and inputs.trend_volatility <= 0.45:
        return "calibration_candidate"
    return "monitor_only"


def _classify_deficit_reality_status(
    inputs: CalibrationModelInputs,
    posture: CalibrationPosture,
) -> DeficitRealityStatus:
    strength = _signal_strength(inputs)
    if posture in {"insufficient_data", "logging_quality_first"}:
        return "no_clear_deficit"
    if posture == "monitor_only":
        if strength < 120 or inputs.trend_volatility >= 0.65:
            return "no_clear_deficit"
        return "likely_maintenance"
    if inputs.operating_expenditure_shift_kcal >= 0:
        return "likely_deficit"
    if inputs.operating_expenditure_shift_kcal < 0:
        return "likely_surplus"
    return "likely_maintenance"


def _calibration_confidence(posture: CalibrationPosture) -> CalibrationConfidence:
    if posture == "high_confidence_mismatch":
        return "high"
    if posture == "calibration_candidate":
        return "medium"
    return "low"


def _operating_expenditure_estimate(inputs: CalibrationModelInputs, posture: CalibrationPosture) -> int:
    if posture in {"insufficient_data", "logging_quality_first", "monitor_only"}:
        return inputs.body_plan_estimated_tdee_kcal

    scale = 1.0 if posture == "high_confidence_mismatch" else 0.5
    adjusted_shift = int(round(inputs.operating_expenditure_shift_kcal * inputs.trend_mismatch_consistency * scale))
    return max(0, inputs.body_plan_estimated_tdee_kcal + adjusted_shift)


def build_calibration_model(inputs: CalibrationModelInputs) -> CalibrationModelResult:
    normalized = _validate_inputs(inputs)
    observation_quality = _classify_observation_quality(normalized)
    logging_quality = _classify_logging_quality(normalized, observation_quality)
    posture = _classify_posture(normalized, observation_quality, logging_quality)
    operating_expenditure_estimate_kcal = _operating_expenditure_estimate(normalized, posture)
    bias_posture = _classify_bias_posture(normalized, logging_quality)
    mismatch_attribution = _classify_mismatch_attribution(normalized, logging_quality)
    deficit_reality_status = _classify_deficit_reality_status(normalized, posture)
    confidence = _calibration_confidence(posture)
    proposal_eligibility = posture in {"calibration_candidate", "high_confidence_mismatch"}

    return CalibrationModelResult(
        decision_mode="deterministic",
        decision_reason="sequential deterministic gate over observation quality, logging quality, and mismatch signal",
        calibration_posture=posture,
        observation_quality_posture=observation_quality,
        logging_quality_posture=logging_quality,
        trend_window_summary=TrendWindowSummary(
            window_days=normalized.observation_window_days,
            observation_count=normalized.body_observation_count,
            intake_coverage=normalized.intake_coverage,
            rescue_overlay_influence=normalized.rescue_overlay_influence,
            trend_volatility=normalized.trend_volatility,
            is_valid=observation_quality == "ready" and logging_quality != "insufficient_data",
        ),
        operating_expenditure_estimate_kcal=operating_expenditure_estimate_kcal,
        intake_estimation_bias_posture=bias_posture,
        deficit_reality_status=deficit_reality_status,
        mismatch_attribution=mismatch_attribution,
        calibration_confidence=confidence,
        proposal_eligibility=proposal_eligibility,
    )
