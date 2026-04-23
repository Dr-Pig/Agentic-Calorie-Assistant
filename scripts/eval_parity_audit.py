from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "runtime" / "evals" / "parity_audits"


@dataclass(frozen=True)
class ClauseSpec:
    clause_id: str
    clause_type: str
    description: str
    severity: str
    expected_runner_checks: tuple[str, ...]


BUNDLE_AUDIT_REGISTRY: dict[str, dict[str, Any]] = {
    "1": {
        "bundle": 1,
        "spec_path": ROOT / "docs" / "quality" / "V2_EVAL_BUNDLE_1_CASES.md",
        "runner_path": ROOT / "scripts" / "run_v2_bundle1_live_eval.py",
        "clauses": (
            ClauseSpec(
                clause_id="B-001.chat_remaining_matches_ui",
                clause_type="hard_fail_conditions",
                description="Chat remaining must equal UI/today remaining for the meal logging turn.",
                severity="blocking",
                expected_runner_checks=("reply_remaining_matches_predicted", "sidecar_remaining_matches_predicted", "today_remaining_matches_predicted"),
            ),
            ClauseSpec(
                clause_id="B-001.same_turn_sync_family",
                clause_type="expected_ui_state",
                description="Same-turn chat, sidecar, today, and budget summary must agree after canonical commit.",
                severity="blocking",
                expected_runner_checks=("response_sidecar_today_budget_sync",),
            ),
            ClauseSpec(
                clause_id="B-002.remaining_from_ledger",
                clause_type="expected_chat_reply",
                description="Remaining budget answer must match current-budget view and not drift from ledger truth.",
                severity="blocking",
                expected_runner_checks=("remaining_in_reply", "no_llm_recalc_drift"),
            ),
        ),
    },
    "2": {
        "bundle": 2,
        "spec_path": ROOT / "docs" / "quality" / "V2_EVAL_BUNDLE_2_CASES.md",
        "runner_path": ROOT / "scripts" / "run_v2_bundle2_live_eval.py",
        "clauses": (
            ClauseSpec(
                clause_id="macro.rule1_draft_hidden",
                clause_type="expected_ui_state",
                description="Draft turns must not expose macro totals or show_macro.",
                severity="blocking",
                expected_runner_checks=("turn1_macro_hidden",),
            ),
            ClauseSpec(
                clause_id="macro.rule2_alignment_gate",
                clause_type="expected_ui_state",
                description="Macro visibility must follow the alignment gate.",
                severity="blocking",
                expected_runner_checks=("macro_alignment_contract",),
            ),
            ClauseSpec(
                clause_id="C-001.turn2_macro_totals_positive",
                clause_type="expected_ui_state",
                description="C-001 committed turn must carry non-zero protein/carbs/fat totals when the spec requires macro totals.",
                severity="blocking",
                expected_runner_checks=("turn2_macro_totals_positive",),
            ),
            ClauseSpec(
                clause_id="macro.rule3_uncertainty_hidden",
                clause_type="expected_ui_state",
                description="High-uncertainty or low-identity cases must not display macro values.",
                severity="non_blocking",
                expected_runner_checks=("macro_uncertainty_visibility",),
            ),
            ClauseSpec(
                clause_id="macro.rule4_correction_updates",
                clause_type="expected_ui_state",
                description="Correction cases must update macro totals alongside kcal.",
                severity="blocking",
                expected_runner_checks=("correction_macro_updated",),
            ),
            ClauseSpec(
                clause_id="macro.rule5_chat_visibility",
                clause_type="expected_chat_reply",
                description="Chat macro wording must obey show_macro and match today totals.",
                severity="blocking",
                expected_runner_checks=("chat_macro_visibility_contract",),
            ),
            ClauseSpec(
                clause_id="E-001.chat_ui_overshoot_sync",
                clause_type="hard_fail_conditions",
                description="Overshoot chat reply must align with today remaining state.",
                severity="blocking",
                expected_runner_checks=("reply_mentions_over", "sidecar_overshoot", "remaining_negative"),
            ),
            ClauseSpec(
                clause_id="E-002.chat_remaining_matches_today",
                clause_type="hard_fail_conditions",
                description="Chat overshoot amount must match abs(today.remaining_kcal).",
                severity="blocking",
                expected_runner_checks=("reply_matches_today_remaining",),
            ),
            ClauseSpec(
                clause_id="K-003.chat_macro_alignment",
                clause_type="hard_fail_conditions",
                description="K-003 chat values must align with corrected today kcal and macro state.",
                severity="blocking",
                expected_runner_checks=("reply_mentions_current_consumed", "chat_macro_visibility_contract"),
            ),
            ClauseSpec(
                clause_id="K-001.preserve_non_target_items",
                clause_type="expected_state_delta",
                description="K-001 correction must preserve non-target items and must not collapse the meal to the corrected item only.",
                severity="blocking",
                expected_runner_checks=(
                    "preserved_non_target_items",
                    "corrected_target_present",
                    "correction_total_not_collapsed_to_target_only",
                    "target_item_replaced_not_appended_duplicate",
                    "corrected_total_matches_preserved_plus_target",
                ),
            ),
            ClauseSpec(
                clause_id="K-002.removal_preserves_thread",
                clause_type="expected_state_delta",
                description="K-002 removal must preserve the meal thread, remove only the target item, and recompute totals from the preserved meal state.",
                severity="blocking",
                expected_runner_checks=(
                    "same_thread_preserved",
                    "target_item_removed_not_new_meal",
                    "corrected_total_matches_removed_target_delta",
                ),
            ),
            ClauseSpec(
                clause_id="same_turn.sync_family",
                clause_type="hard_fail_conditions",
                description="Committed turns must keep chat, sidecar, today, and budget summary synchronized.",
                severity="blocking",
                expected_runner_checks=("same_turn_budget_sync",),
            ),
        ),
    },
}


def run_parity_audit(bundle: str | int) -> dict[str, Any]:
    bundle_id = str(bundle)
    if bundle_id not in BUNDLE_AUDIT_REGISTRY:
        raise ValueError(f"unsupported bundle parity audit: {bundle}")
    config = BUNDLE_AUDIT_REGISTRY[bundle_id]
    runner_text = config["runner_path"].read_text(encoding="utf-8")
    spec_clauses: list[dict[str, Any]] = []
    implemented_checks: list[str] = []
    coverage_gaps: list[dict[str, Any]] = []
    blocking_gaps: list[dict[str, Any]] = []

    for clause in config["clauses"]:
        missing_checks = [check for check in clause.expected_runner_checks if f'"{check}"' not in runner_text and f"'{check}'" not in runner_text]
        spec_clauses.append(
            {
                "clause_id": clause.clause_id,
                "clause_type": clause.clause_type,
                "description": clause.description,
                "severity": clause.severity,
                "expected_runner_checks": list(clause.expected_runner_checks),
                "implemented": not missing_checks,
            }
        )
        if not missing_checks:
            implemented_checks.extend(clause.expected_runner_checks)
            continue
        gap = {
            "clause_id": clause.clause_id,
            "clause_type": clause.clause_type,
            "description": clause.description,
            "severity": clause.severity,
            "missing_checks": missing_checks,
        }
        coverage_gaps.append(gap)
        if clause.severity == "blocking":
            blocking_gaps.append(gap)

    coverage_status = "blocked" if blocking_gaps else ("incomplete" if coverage_gaps else "complete")
    return {
        "bundle": config["bundle"],
        "spec_path": str(config["spec_path"]),
        "runner_path": str(config["runner_path"]),
        "spec_clauses": spec_clauses,
        "implemented_checks": sorted(set(implemented_checks)),
        "coverage_gaps": coverage_gaps,
        "blocking_gaps": blocking_gaps,
        "coverage_status": coverage_status,
        "coverage_blocking_gaps": len(blocking_gaps),
        "parity_audit_completed": True,
    }


def _default_output_path(bundle: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / f"bundle{bundle}_parity_audit.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic eval spec-to-runner parity audit.")
    parser.add_argument("--bundle", required=True, choices=sorted(BUNDLE_AUDIT_REGISTRY.keys()))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    report = run_parity_audit(args.bundle)
    out_path = Path(args.out) if args.out else _default_output_path(args.bundle)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"bundle": report["bundle"], "coverage_status": report["coverage_status"], "blocking_gaps": report["coverage_blocking_gaps"], "out": str(out_path)}, ensure_ascii=False))
    return 0 if report["coverage_status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
