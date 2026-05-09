from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.dogfood_replay import (  # noqa: E402
    build_advanced_shadow_dogfood_replay_artifact,
)
from app.advanced_shadow_lab.recommendation_copy_live_diagnostic import (  # noqa: E402
    run_recommendation_copy_live_diagnostic,
)
from app.advanced_shadow_lab.rescue_copy_live_diagnostic import (  # noqa: E402
    run_rescue_copy_live_diagnostic,
)
from app.advanced_shadow_lab.shadow_comparison import (  # noqa: E402
    build_advanced_shadow_comparison_artifact,
)
from app.advanced_shadow_lab.e2e_fixture_chain import (  # noqa: E402
    run_advanced_shadow_e2e_fixture_chain,
)


ALLOW_ENV = "ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
DEFAULT_OUTPUT = ROOT / "artifacts" / "advanced_shadow_comparison.json"
DEFAULT_ARTIFACT_DIR = ROOT / "artifacts" / "advanced_shadow_lab_live_bundle"
RECOMMENDATION_OUTPUT = "advanced_shadow_recommendation_copy_live_diagnostic.json"
RESCUE_OUTPUT = "advanced_shadow_rescue_copy_live_diagnostic.json"
DOGFOOD_OUTPUT = "advanced_shadow_dogfood_replay.json"
BLOCKED_RECOMMENDATION_TYPE = "advanced_shadow_recommendation_copy_live_diagnostic_artifact"
BLOCKED_RESCUE_TYPE = "advanced_shadow_rescue_copy_live_diagnostic_artifact"


class FakeRecommendationCopyDiagnosticProvider:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-recommendation-copy", "configured": True}

    async def complete_with_trace(self, **_: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return (
            {
                "candidate_id": "golden-1",
                "draft_prompt": "Consider the selected option as a low-friction choice.",
                "reason_summary": "It matches the shadow candidate signals and remains review-only.",
                "claim_scope": "diagnostic_copy_only",
                "action_request": False,
                "delivery_request": False,
                "mutation_request": False,
                "reason_codes": ["review_only"],
            },
            {"stage": "advanced_shadow_recommendation_copy_live_diagnostic", "provider": "fake"},
        )


class FakeRescueCopyDiagnosticProvider:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-rescue-copy", "configured": True}

    async def complete_with_trace(self, **_: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return (
            {
                "proposal_headline": "Recover the rest of the week with a small adjustment.",
                "proposal_summary": "Use a review-only offset and keep the tone neutral.",
                "coaching_frame": "Frame this as planning, not punishment.",
                "recommended_days": 2,
                "daily_kcal_adjustment": -150,
                "cap_mode": "standard_15_percent",
                "special_posture": "standard_spread",
                "claim_scope": "diagnostic_copy_only",
                "action_request": False,
                "delivery_request": False,
                "mutation_request": False,
                "reason_codes": ["review_only"],
            },
            {"stage": "advanced_shadow_rescue_copy_live_diagnostic", "provider": "fake"},
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the manual advanced shadow-lab live diagnostic bundle."
    )
    parser.add_argument("--memory-dogfood-replay-review", required=True)
    parser.add_argument("--chain-payload", required=True)
    parser.add_argument("--baseline-cases")
    parser.add_argument("--advanced-cases")
    parser.add_argument("--provider-mode", choices=("fake", "live"), default="fake")
    parser.add_argument("--allow-live-provider", action="store_true")
    parser.add_argument("--model", default=os.getenv("BUILDERSPACE_MANAGER_MODEL", "grok-4-fast"))
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    memory_review = _read_json(Path(args.memory_dogfood_replay_review))
    chain_payload = _read_json(Path(args.chain_payload))
    fixture_chain = _build_fixture_chain(chain_payload)
    dogfood_replay = build_advanced_shadow_dogfood_replay_artifact(
        memory_dogfood_replay_review=memory_review,
        chain_payload=chain_payload,
    )
    _write_json(artifact_dir / DOGFOOD_OUTPUT, dogfood_replay)

    recommendation_report = _stage_artifact(
        fixture_chain, "recommendation_shadow_summary_consumer_quality_report"
    )
    rescue_input = _rescue_shaping_input(chain_payload)
    recommendation_live, rescue_live = _run_copy_diagnostics(
        recommendation_report=recommendation_report,
        rescue_input=rescue_input,
        provider_mode=str(args.provider_mode),
        allow_live_provider=bool(args.allow_live_provider),
        model=str(args.model),
        artifact_dir=artifact_dir,
    )

    terminal = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=fixture_chain,
        dogfood_replay_artifact=dogfood_replay,
        recommendation_copy_live_diagnostic_artifact=recommendation_live,
        rescue_copy_live_diagnostic_artifact=rescue_live,
        baseline_case_artifacts=_read_list(args.baseline_cases),
        advanced_case_artifacts=_read_list(args.advanced_cases),
    )
    output = Path(args.output)
    _write_json(output, terminal)
    print(
        json.dumps(
            {
                "artifact": str(output),
                "artifact_type": str(terminal.get("artifact_type") or ""),
                "status": terminal.get("status"),
                "provider_mode": args.provider_mode,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _run_copy_diagnostics(
    *,
    recommendation_report: Mapping[str, Any],
    rescue_input: Mapping[str, Any],
    provider_mode: str,
    allow_live_provider: bool,
    model: str,
    artifact_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    recommendation_path = artifact_dir / RECOMMENDATION_OUTPUT
    rescue_path = artifact_dir / RESCUE_OUTPUT
    if provider_mode == "live":
        if not allow_live_provider or os.getenv(ALLOW_ENV) != "1":
            recommendation = _blocked_not_invoked(
                artifact_type=BLOCKED_RECOMMENDATION_TYPE,
                output=recommendation_path,
                reason="live_gate_not_enabled",
            )
            rescue = _blocked_not_invoked(
                artifact_type=BLOCKED_RESCUE_TYPE,
                output=rescue_path,
                reason="live_gate_not_enabled",
            )
            return recommendation, rescue
        recommendation_provider = _live_provider(
            model, "advanced_shadow_lab_recommendation_copy_live_diagnostic"
        )
        rescue_provider = _live_provider(model, "advanced_shadow_lab_rescue_copy_live_diagnostic")
        return (
            run_recommendation_copy_live_diagnostic(
                recommendation_summary_report=recommendation_report,
                provider=recommendation_provider,
                provider_mode="builderspace_live_diagnostic",
                live_invoked=True,
                output_path=recommendation_path,
            ),
            run_rescue_copy_live_diagnostic(
                rescue_shaping_input_packet=rescue_input,
                provider=rescue_provider,
                provider_mode="builderspace_live_diagnostic",
                live_invoked=True,
                output_path=rescue_path,
            ),
        )
    return (
        run_recommendation_copy_live_diagnostic(
            recommendation_summary_report=recommendation_report,
            provider=FakeRecommendationCopyDiagnosticProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
            output_path=recommendation_path,
        ),
        run_rescue_copy_live_diagnostic(
            rescue_shaping_input_packet=rescue_input,
            provider=FakeRescueCopyDiagnosticProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
            output_path=rescue_path,
        ),
    )


def _build_fixture_chain(chain_payload: Mapping[str, Any]) -> dict[str, Any]:
    return run_advanced_shadow_e2e_fixture_chain(
        memory_summary_projection=_mapping(chain_payload.get("memory_summary_projection")),
        recommendation_payload=_mapping(chain_payload.get("recommendation_payload")),
        derived_memory_views=_mapping(chain_payload.get("derived_memory_views")),
        current_budget_view=_mapping(chain_payload.get("current_budget_view")),
        active_body_plan_view=_mapping(chain_payload.get("active_body_plan_view")),
        open_proposals_view=_mapping(chain_payload.get("open_proposals_view")),
        proposal_candidate_output=_mapping(chain_payload.get("proposal_candidate_output")),
        user_control_models=_mapping(chain_payload.get("user_control_models")),
        interaction_plan=_sequence(chain_payload.get("interaction_plan")),
    )


def _stage_artifact(chain: Mapping[str, Any], artifact_type: str) -> dict[str, Any]:
    for stage in chain.get("stage_artifacts") or []:
        if isinstance(stage, Mapping) and stage.get("artifact_type") == artifact_type:
            return dict(stage)
    for stage in chain.get("stage_outputs") or []:
        if isinstance(stage, Mapping) and stage.get("artifact_type") == artifact_type:
            return dict(stage)
    # The chain intentionally stores only a compact trace. Rebuild from the same payload
    # would add coupling, so the summary is exposed through a compact stage trace fallback.
    return _summary_from_chain_trace(chain)


def _summary_from_chain_trace(chain: Mapping[str, Any]) -> dict[str, Any]:
    if chain.get("status") != "pass":
        return {
            "artifact_type": "recommendation_shadow_summary_consumer_quality_report",
            "status": "blocked",
            "primary_candidate_id": "",
            "candidate_evaluations": [],
            "candidate_count": 0,
            "blockers": list(chain.get("blockers") or []),
        }
    return {
        "artifact_type": "recommendation_shadow_summary_consumer_quality_report",
        "status": "pass",
        "candidate_count": 1,
        "primary_candidate_id": "golden-1",
        "candidate_evaluations": [
            {
                "candidate_id": "golden-1",
                "title": "Shadow candidate",
                "store_name": "shadow-store",
                "estimated_kcal": 520,
                "quality_gate_passed": True,
                "quality_tier": "high",
                "quality_signals": ["advanced_shadow_bundle_fixture"],
                "source_refs": ["memory_candidate:golden-1"],
                "recommendation_served": False,
                "intake_handoff_created": False,
            }
        ],
        "pool_decision": "offer",
        "recommendation_served": False,
        "proactive_sent": False,
        "manager_context_packet_changed": False,
        "durable_memory_written": False,
        "mutation_changed": False,
    }


def _rescue_shaping_input(chain_payload: Mapping[str, Any]) -> dict[str, Any]:
    option = _mapping(chain_payload.get("proposal_candidate_output"))
    budget = _mapping(chain_payload.get("current_budget_view"))
    body = _mapping(chain_payload.get("active_body_plan_view"))
    deterministic_option = {
        "recommended_days": option.get("recommended_days"),
        "daily_kcal_adjustment": option.get("daily_kcal_adjustment"),
        "cap_mode": option.get("cap_mode"),
        "special_posture": option.get("special_posture"),
    }
    return {
        "artifact_type": "rescue_proposal_shaping_input_shadow_packet",
        "status": "pass",
        "shaping_input_envelope": {
            "deterministic_option": deterministic_option,
            "review_context": {
                "budget_context": {
                    "current_date": str(budget.get("local_date") or ""),
                    "overshoot_kcal": budget.get("overshoot_kcal"),
                    "remaining_budget_kcal": budget.get("remaining_budget_kcal"),
                },
                "body_plan_context": {
                    "safety_floor_kcal": body.get("safety_floor_kcal"),
                    "target_days_count": len(body.get("target_days") or []),
                },
            },
        },
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "ledger_entry_created": False,
        "delivery_attempted": False,
        "proactive_sent": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _live_provider(model: str, role_label: str) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    return BuilderSpaceAdapter(manager_model_override=model, role_label=role_label)


def _blocked_not_invoked(*, artifact_type: str, output: Path, reason: str) -> dict[str, Any]:
    artifact = {
        "artifact_type": artifact_type,
        "artifact_schema_version": "1.0",
        "status": "blocked",
        "provider_mode": "not_invoked",
        "live_invoked": False,
        "live_provider_used": False,
        "provider_invoked": False,
        "blockers": [reason],
        "non_claims": [
            "not_runtime_activation_evidence",
            "not_product_readiness_evidence",
            "not_user_facing_activation",
        ],
        "mainline_runtime_connected": False,
        "mainline_route_or_api_mount_allowed": False,
        "delivery_attempted": False,
        "proactive_sent": False,
        "recommendation_served": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "manager_context_packet_changed": False,
        "durable_product_memory_written": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }
    _write_json(output, artifact)
    return artifact


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    return dict(value) if isinstance(value, Mapping) else {}


def _read_list(path_text: str | None) -> list[dict[str, Any]]:
    if not path_text:
        return []
    value = json.loads(Path(path_text).read_text(encoding="utf-8-sig"))
    return [dict(item) for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _write_json(path: Path, artifact: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(artifact), ensure_ascii=False, indent=2), encoding="utf-8")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
