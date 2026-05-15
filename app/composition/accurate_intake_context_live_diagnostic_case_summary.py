from __future__ import annotations

from typing import Any


def build_context_live_diagnostic_case_summary(cases: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "case_count": len(cases),
        "holdout_utterance_variant_count": sum(
            len(case.get("holdout_utterance_variants") or [])
            for case in cases
            if isinstance(case.get("holdout_utterance_variants"), list)
        ),
        "target_candidate_cases": sum(1 for case in cases if case["target_candidates_expected"]),
        "pending_pin_cases": sum(1 for case in cases if case["pending_pin_expected"]),
        "ambiguity_cases": sum(1 for case in cases if case["ambiguity_expected"]),
        "compound_cases": sum(
            1 for case in cases if case["case_id"] == "context_live_009_simultaneous_log_and_modify"
        ),
    }
