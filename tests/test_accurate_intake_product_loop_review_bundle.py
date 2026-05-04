from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_product_loop_review_bundle import (
    build_product_loop_review_bundle_artifact,
)
from app.composition.dogfood_review_queue import (
    build_review_candidate_from_product_loop_diagnostic,
)


def _browser_shell() -> dict:
    return {
        "artifact_type": "accurate_intake_browser_shell_smoke",
        "status": "pass",
        "browser_executed": True,
        "web_readiness_claimed": False,
    }


def _fixture_dogfood() -> dict:
    return {
        "artifact_type": "accurate_intake_browser_one_day_fixture_dogfood",
        "status": "browser_fixture_pass",
        "fixture_evidence_used": True,
        "fooddb_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
    }


def _realistic_v2() -> dict:
    return {
        "artifact_type": "accurate_intake_browser_realistic_web_dogfood_v2",
        "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
        "fixture_evidence_used": True,
        "fooddb_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }


def _context_review() -> dict:
    return {
        "artifact_type": "accurate_intake_context_review_artifact",
        "status": "generated",
        "summary": {"forbidden_context_trace_count": 0},
        "context_engineering_fault_claimed": False,
    }


def _target_eval() -> dict:
    return {
        "artifact_type": "accurate_intake_context_target_candidate_eval",
        "status": "generated",
        "summary": {"ambiguous_scenarios": 2},
        "deterministic_selected_target": False,
    }


def _window_diagnostic() -> dict:
    return {
        "artifact_type": "accurate_intake_context_window_diagnostic",
        "status": "generated",
        "long_term_memory_used": False,
        "proactive_or_rescue_used": False,
    }


def test_review_candidate_from_product_loop_diagnostic_is_review_only() -> None:
    candidate = build_review_candidate_from_product_loop_diagnostic(_target_eval())

    assert candidate["status"] == "review_candidate"
    assert candidate["raw_trace_is_truth"] is False
    assert candidate["auto_flags"] == ["target_ambiguity"]
    assert candidate["canonical_eval_promotion"]["allowed"] is False
    assert candidate["review_candidate"]["reviewer_agent_can_approve"] is False
    assert candidate["truth_owner"]["canonical_eval_case"] == "human_reviewer"


def test_product_loop_review_bundle_combines_diagnostics_without_readiness_or_fooddb_claims() -> None:
    bundle = build_product_loop_review_bundle_artifact(
        browser_shell_smoke=_browser_shell(),
        browser_fixture_dogfood=_fixture_dogfood(),
        browser_realistic_dogfood=_realistic_v2(),
        context_review=_context_review(),
        context_target_candidate_eval=_target_eval(),
        context_window_diagnostic=_window_diagnostic(),
    )

    assert bundle["artifact_type"] == "accurate_intake_product_loop_review_bundle_v1"
    assert bundle["status"] == "product_loop_context_diagnostic_ready_for_human_review"
    assert bundle["ready_for_fdb_integration"] is False
    assert bundle["fixture_evidence_used"] is True
    assert bundle["fooddb_evidence_used"] is False
    assert bundle["real_fooddb_pass_claimed"] is False
    assert bundle["dogfood_pass"] is False
    assert bundle["web_readiness_claimed"] is False
    assert bundle["product_readiness_claimed"] is False
    assert bundle["private_self_use_approved"] is False
    assert bundle["local_only"] is True
    assert bundle["contains_personal_diet_logs"] is True
    assert bundle["do_not_commit"] is True
    assert bundle["input_claim_boundary_ok"] is True
    assert bundle["input_claim_boundary_blockers"] == []
    assert bundle["review_queue"]["promotion_policy"]["human_approval_required_for_canonical_eval"] is True
    assert bundle["review_queue"]["promotion_policy"]["food_kb_truth_update_from_correction_allowed"] is False
    assert bundle["review_queue"]["review_candidate_count"] >= 1


def test_product_loop_review_bundle_blocks_input_overclaims_without_promoting_them() -> None:
    realistic = _realistic_v2()
    realistic["real_fooddb_pass_claimed"] = True
    realistic["dogfood_pass"] = True

    bundle = build_product_loop_review_bundle_artifact(
        browser_shell_smoke=_browser_shell(),
        browser_fixture_dogfood=_fixture_dogfood(),
        browser_realistic_dogfood=realistic,
        context_review=_context_review(),
        context_target_candidate_eval=_target_eval(),
        context_window_diagnostic=_window_diagnostic(),
    )

    assert bundle["status"] == "blocked_input_overclaim"
    assert bundle["input_claim_boundary_ok"] is False
    assert "browser_realistic_dogfood.real_fooddb_pass_claimed" in bundle[
        "input_claim_boundary_blockers"
    ]
    assert "browser_realistic_dogfood.dogfood_pass" in bundle[
        "input_claim_boundary_blockers"
    ]
    assert bundle["real_fooddb_pass_claimed"] is False
    assert bundle["dogfood_pass"] is False
    assert bundle["included_artifacts"]["browser_realistic_dogfood"]["claim_flags"][
        "real_fooddb_pass_claimed"
    ] is True


def test_product_loop_review_bundle_builder_script_writes_artifact(tmp_path: Path) -> None:
    paths: dict[str, Path] = {}
    for name, payload in {
        "browser_shell": _browser_shell(),
        "fixture_dogfood": _fixture_dogfood(),
        "realistic_v2": _realistic_v2(),
        "context_review": _context_review(),
        "target_eval": _target_eval(),
        "window": _window_diagnostic(),
    }.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        paths[name] = path
    output_path = tmp_path / "bundle.json"

    from scripts.build_accurate_intake_product_loop_review_bundle import main

    exit_code = main(
        [
            "--browser-shell-smoke",
            str(paths["browser_shell"]),
            "--browser-fixture-dogfood",
            str(paths["fixture_dogfood"]),
            "--browser-realistic-dogfood",
            str(paths["realistic_v2"]),
            "--context-review",
            str(paths["context_review"]),
            "--context-target-candidate-eval",
            str(paths["target_eval"]),
            "--context-window-diagnostic",
            str(paths["window"]),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    bundle = json.loads(output_path.read_text(encoding="utf-8"))
    assert bundle["status"] == "product_loop_context_diagnostic_ready_for_human_review"


def test_plce_followup_sources_do_not_import_forbidden_truth_or_live_search() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_context_review.py"),
        Path("app/composition/accurate_intake_context_target_candidate_eval.py"),
        Path("app/composition/accurate_intake_context_window_diagnostic.py"),
        Path("app/composition/accurate_intake_product_loop_review_bundle.py"),
    ]
    forbidden_fragments = (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "evidence_candidate_packetizer",
        "promotion_policy",
        "app.providers.tavily",
        "tavily_adapter",
        "web_search",
        "requests.",
        "httpx.",
    )

    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in source
