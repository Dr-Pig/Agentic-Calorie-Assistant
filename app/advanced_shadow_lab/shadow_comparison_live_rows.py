from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.shadow_comparison_live_rows"
)


def live_copy_row(surface: str, live: Mapping[str, Any]) -> dict[str, str]:
    live_status = str(live.get("status") or "missing")
    guard_status = str(_mapping(live.get("output_guard")).get("status") or "")
    if live_status == "pass":
        finding = "live_diagnostic_passed"
    elif live_status == "not_run":
        finding = "live_diagnostic_not_run"
    elif guard_status == "blocked":
        finding = "live_diagnostic_model_output_blocked"
    else:
        finding = "live_diagnostic_unavailable"
    return {
        "surface": surface,
        "fixture_status": "not_applicable",
        "dogfood_status": "not_applicable",
        "live_status": live_status,
        "finding": finding,
    }


def live_diagnostic_signal(live: Mapping[str, Any]) -> dict[str, Any]:
    if live.get("status") == "not_run":
        return _signal(False, False, "not_run", "not_run")
    return _signal(
        bool(live.get("live_invoked")),
        bool(live.get("live_provider_used")),
        str(live.get("provider_mode") or ""),
        str(_mapping(live.get("output_guard")).get("status") or ""),
    )


def _signal(invoked: bool, used: bool, mode: str, guard: str) -> dict[str, Any]:
    return {
        "live_invoked": invoked,
        "live_provider_used": used,
        "provider_mode": mode,
        "output_guard_status": guard,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
