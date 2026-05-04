from __future__ import annotations
from importlib import import_module
from typing import Any

__all__ = [
    "BodyCalibrationDiagnosticRequest",
    "BodyCalibrationDiagnosticResult",
    "TargetCalculationInputs",
    "build_active_body_plan_view",
    "build_body_calibration_diagnostic",
    "calculate_recommended_target_kcal",
    "get_latest_weight_observation",
]

_EXPORT_MAP = {
    "BodyCalibrationDiagnosticRequest": (".body_calibration_service", "BodyCalibrationDiagnosticRequest"),
    "BodyCalibrationDiagnosticResult": (".body_calibration_service", "BodyCalibrationDiagnosticResult"),
    "TargetCalculationInputs": (".target_calculation", "TargetCalculationInputs"),
    "build_active_body_plan_view": (".active_body_plan_read_model", "build_active_body_plan_view"),
    "build_body_calibration_diagnostic": (".body_calibration_service", "build_body_calibration_diagnostic"),
    "calculate_recommended_target_kcal": (".target_calculation", "calculate_recommended_target_kcal"),
    "get_latest_weight_observation": (".body_observation_service", "get_latest_weight_observation"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORT_MAP[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
