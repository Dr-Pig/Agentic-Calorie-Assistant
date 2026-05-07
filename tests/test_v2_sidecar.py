from __future__ import annotations

from types import SimpleNamespace

from app.runtime.application import build_deterministic_sidecar


def test_sidecar_macro_surface_follows_today_truth() -> None:
    sidecar = build_deterministic_sidecar(
        active_body_plan_view=SimpleNamespace(model_dump=lambda mode="json": {"body_plan_id": 1}),
        current_budget_view=SimpleNamespace(
            model_dump=lambda mode="json": {
                "budget_kcal": 1200,
                "remaining_kcal": 830,
                "adjustment_kcal": 0,
                "consumed_protein": 6,
                "consumed_carbs": 75,
                "consumed_fat": 8,
                "show_macro": False,
                "macro_guard_reason": "no_macro_data",
            }
        ),
        state_mutation_summary={},
        trace_summary={},
        macro_summary={"display_status": "show", "guard_reason": "committed_and_aligned", "macro_kcal_delta": 20},
    )

    assert sidecar["macro"]["display_status"] == "hide"
    assert sidecar["macro"]["guard_reason"] == "no_macro_data"
    assert sidecar["macro"]["protein_g"] == 6
    assert sidecar["macro"]["carbs_g"] == 75
    assert sidecar["macro"]["fat_g"] == 8
