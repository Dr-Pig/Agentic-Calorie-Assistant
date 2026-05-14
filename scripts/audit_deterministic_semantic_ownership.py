from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "deterministic_semantic_ownership_audit.json"
GATE_STAGES = ("report", "new-high-risk", "active-runtime", "active-runtime-zero", "zero-high-risk")
LEGACY_RESOLUTION_TOKEN = "nutrition" + "_resolution"


@dataclass(frozen=True)
class RiskRule:
    risk_id: str
    severity: str
    markers: tuple[str, ...]
    paths: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class AllowlistEntry:
    path: str
    markers: tuple[str, ...]
    reason: str


RULES: tuple[RiskRule, ...] = (
    RiskRule(
        risk_id="deterministic_keyword_intent_or_workflow_router",
        severity="high",
        markers=("_looks_like_intake_request", "looks_like_correction", "looks_like_budget_query", "keywords", "_INTAKE_TOKENS"),
        paths=("app/intake", "app/runtime/agent"),
        rationale="Keyword routing may become semantic ownership if not limited to guard/prior behavior.",
    ),
    RiskRule(
        risk_id="legacy_resolution_semantic_pipeline",
        severity="high",
        markers=(
            f"__path_contains__:{LEGACY_RESOLUTION_TOKEN}_",
            f"build_{LEGACY_RESOLUTION_TOKEN}_payload",
            f"run_{LEGACY_RESOLUTION_TOKEN}",
        ),
        paths=("app/nutrition/agent", "app/nutrition/application", "app/shared/contracts"),
        rationale="The old nutrition resolution parser/normalizer/prompt pipeline defaulted semantic fields outside the manager-owned contract.",
    ),
    RiskRule(
        risk_id="post_llm_semantic_field_rewrite",
        severity="high",
        markers=(
            "payload.route_target =",
            "payload.action_taken =",
            "payload.follow_up_needed =",
            "payload.followup_question =",
            'updated["follow_up_needed"] =',
            'updated["action_taken"] =',
            'updated["response_mode_hint"] =',
            "trace_contract[\"followup_question\"]",
            "trace_contract[\"unresolved_info\"]",
        ),
        paths=("app/intake", "app/runtime", "app/nutrition"),
        rationale="Semantic payload fields should not be rewritten after an LLM/manager pass except by explicit validation, downgrade, or bounded repair.",
    ),
    RiskRule(
        risk_id="pre_manager_estimability_or_followup_shortcut",
        severity="high",
        markers=(
            "initial_guard_feedback",
            "entry_handoff_seed_commit_boundary_validation",
            "pre_manager_followup",
        ),
        paths=("app/composition", "app/runtime/agent"),
        rationale="Composition sufficiency, estimability, and follow-up necessity must be Manager decisions before deterministic guard repair.",
    ),
    RiskRule(
        risk_id="active_shadow_or_fallback_estimate_path",
        severity="high",
        markers=(
            "build_shadow_stub_artifact",
            "shadow_stub_estimate_enabled",
            "classify_query_family(",
            "is_high_variance_family(",
        ),
        paths=("app/composition", "app/runtime/agent"),
        rationale="Active runtime must not use deterministic raw-text fallback estimates or food-family rules to supply kcal, macro, estimability, or follow-up semantics.",
    ),
    RiskRule(
        risk_id="followup_or_clarify_as_commit_gate",
        severity="high",
        markers=(
            "route_target == \"clarify_user_private\"",
            "payload_route_target == \"clarify_user_private\"",
            "action_taken == \"answer_with_uncertainty\"",
            "followup_question or unresolved",
        ),
        paths=("app/intake", "app/runtime", "app/nutrition"),
        rationale="Follow-up and uncertainty may be precision/refinement signals, not automatic draft/no-commit gates.",
    ),
    RiskRule(
        risk_id="acceptable_deterministic_legality_guard",
        severity="info",
        markers=("TransitionGuardResult", "blocked_mutation", "schema validation", "canonical_write_allowed", "ledger_mutation_allowed"),
        paths=("app/intake", "app/runtime", "app/shared"),
        rationale="Deterministic validation and legality gates are acceptable when they consume semantic-owner output.",
    ),
)


ALLOWLIST: tuple[AllowlistEntry, ...] = (
    AllowlistEntry(
        path="app/intake/application/transition_guard.py",
        markers=("payload.follow_up_needed =", "follow_up_needed"),
        reason="Transition guard legality validation may expose semantic fields without owning their meaning.",
    ),
    AllowlistEntry(
        path="app/runtime/application/request_trace_artifacts.py",
        markers=('trace_contract["followup_question"]', 'trace_contract["unresolved_info"]'),
        reason="Trace artifact projection records manager output for auditability without rewriting product truth.",
    ),
    AllowlistEntry(
        path="app/composition/payload_builders.py",
        markers=("follow_up_needed",),
        reason="Trace payload builders record manager follow-up posture for observability without owning ambiguous semantics.",
    ),
    AllowlistEntry(
        path="app/composition/phase_a_boundary_projection.py",
        markers=("follow_up_needed",),
        reason="Phase A boundary projection validates and traces manager output without mutating product truth.",
    ),
)


def _candidate_files(paths: Iterable[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for relative in paths:
        base = ROOT / relative
        if base.is_file() and base.suffix == ".py":
            if base not in seen:
                seen.add(base)
                yield base
        elif base.exists():
            for path in base.rglob("*.py"):
                if path not in seen:
                    seen.add(path)
                    yield path


def _read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _high_risk_findings(findings: list[dict[str, object]]) -> list[dict[str, object]]:
    return [finding for finding in findings if finding.get("severity") == "high"]


def _allowlist_reason(finding: dict[str, object]) -> str | None:
    path = str(finding.get("path") or "")
    marker = str(finding.get("marker") or "")
    for entry in ALLOWLIST:
        if path == entry.path and marker in entry.markers:
            return entry.reason
    return None


def _split_allowlisted_findings(
    findings: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    allowed: list[dict[str, object]] = []
    unauthorized: list[dict[str, object]] = []
    for finding in findings:
        reason = _allowlist_reason(finding)
        if reason:
            allowed.append({**finding, "allowlist_reason": reason})
        else:
            unauthorized.append(finding)
    return allowed, unauthorized


def _active_runtime_high_risk_findings(findings: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        finding
        for finding in _high_risk_findings(findings)
        if str(finding.get("path") or "").startswith(("app/", "scripts/"))
    ]


def _gate_failure(stage: str, unauthorized_findings: list[dict[str, object]]) -> bool:
    if stage == "report":
        return False
    if stage == "new-high-risk":
        return False
    if stage in {"active-runtime", "active-runtime-zero"}:
        return bool(_active_runtime_high_risk_findings(unauthorized_findings))
    if stage == "zero-high-risk":
        return bool(_high_risk_findings(unauthorized_findings))
    raise ValueError(f"unknown audit gate stage: {stage}")


def build_report(*, stage: str = "report") -> dict[str, object]:
    if stage not in GATE_STAGES:
        raise ValueError(f"stage must be one of {', '.join(GATE_STAGES)}")
    findings: list[dict[str, object]] = []
    for rule in RULES:
        for path in _candidate_files(rule.paths):
            relative_path = str(path.relative_to(ROOT)).replace("\\", "/")
            for marker in rule.markers:
                if marker.startswith("__path_contains__:"):
                    token = marker.removeprefix("__path_contains__:")
                    if token in relative_path:
                        findings.append(
                            {
                                "risk_id": rule.risk_id,
                                "severity": rule.severity,
                                "path": relative_path,
                                "line": 1,
                                "marker": marker,
                                "snippet": relative_path,
                                "rationale": rule.rationale,
                            }
                        )
            lines = _read_lines(path)
            for line_number, line in enumerate(lines, start=1):
                for marker in rule.markers:
                    if marker.startswith("__path_contains__:"):
                        continue
                    if marker in line:
                        findings.append(
                            {
                                "risk_id": rule.risk_id,
                                "severity": rule.severity,
                                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                                "line": line_number,
                                "marker": marker,
                                "snippet": line.strip()[:220],
                                "rationale": rule.rationale,
                            }
                        )

    counts: dict[str, int] = {}
    for finding in findings:
        key = str(finding["risk_id"])
        counts[key] = counts.get(key, 0) + 1

    high_risk = _high_risk_findings(findings)
    allowed_findings, unauthorized_findings = _split_allowlisted_findings(findings)
    allowed_high_risk = _high_risk_findings(allowed_findings)
    unauthorized_high_risk = _high_risk_findings(unauthorized_findings)
    active_runtime_high_risk = _active_runtime_high_risk_findings(findings)
    active_runtime_unauthorized_high_risk = _active_runtime_high_risk_findings(unauthorized_findings)
    fails_build = _gate_failure(stage, unauthorized_findings)

    return {
        "artifact_type": "deterministic_semantic_ownership_audit",
        "gate_stage": stage,
        "report_only": stage == "report",
        "fails_build": fails_build,
        "high_risk_finding_count": len(high_risk),
        "allowed_high_risk_finding_count": len(allowed_high_risk),
        "unauthorized_high_risk_finding_count": len(unauthorized_high_risk),
        "active_runtime_high_risk_finding_count": len(active_runtime_high_risk),
        "active_runtime_unauthorized_high_risk_finding_count": len(active_runtime_unauthorized_high_risk),
        "gate_policy": {
            "report": "inventory only; never fails",
            "new-high-risk": "reserved for baseline-diff enforcement; current invocation is non-blocking until a baseline is configured",
            "active-runtime": "backwards-compatible alias that fails on unauthorized active app/scripts high-risk semantic ownership findings after allowlist filtering",
            "active-runtime-zero": "fails on unauthorized active app/scripts high-risk semantic ownership findings after allowlist filtering",
            "zero-high-risk": "fails on any unauthorized high-risk semantic ownership finding after allowlist filtering",
        },
        "semantic_owner_policy": {
            "deterministic_diagnostic_mode_is_not_semantic_ownership": True,
            "llm_or_manager_structured_output_owns_ambiguous_intent_and_food_semantics": True,
            "manager_owns_composition_estimability_and_followup_necessity_before_guard": True,
            "active_runtime_forbids_shadow_stub_and_raw_text_food_family_fallbacks": True,
            "deterministic_code_owns_validation_guards_schema_persistence_legality_trace_and_evals": True,
            "legacy_scan_matches_are_supporting_evidence_only": True,
        },
        "risk_summary": counts,
        "allowlist": [
            {"path": entry.path, "markers": list(entry.markers), "reason": entry.reason}
            for entry in ALLOWLIST
        ],
        "allowed_findings": allowed_findings,
        "unauthorized_findings": unauthorized_findings,
        "findings": findings,
    }


def write_report(output_path: Path = DEFAULT_OUTPUT, *, stage: str = "report") -> dict[str, object]:
    report = build_report(stage=stage)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Report deterministic semantic-ownership risk surfaces.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--stage", choices=GATE_STAGES, default="report")
    args = parser.parse_args()
    report = write_report(Path(args.output), stage=args.stage)
    print(
        json.dumps(
            {
                "artifact": str(Path(args.output)),
                "report_only": report["report_only"],
                "gate_stage": report["gate_stage"],
                "fails_build": report["fails_build"],
                "finding_count": len(report["findings"]),  # type: ignore[arg-type]
                "high_risk_finding_count": report["high_risk_finding_count"],
                "unauthorized_high_risk_finding_count": report["unauthorized_high_risk_finding_count"],
                "active_runtime_unauthorized_high_risk_finding_count": report[
                    "active_runtime_unauthorized_high_risk_finding_count"
                ],
                "risk_summary": report["risk_summary"],
            },
            ensure_ascii=True,
        )
    )
    return 1 if report["fails_build"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
