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
from app.advanced_shadow_lab.proactive_copy_live_diagnostic import (  # noqa: E402
    run_proactive_copy_live_diagnostic,
)
from app.advanced_shadow_lab.shadow_comparison import (  # noqa: E402
    build_advanced_shadow_comparison_artifact,
)
from app.advanced_shadow_lab.e2e_fixture_chain import (  # noqa: E402
    run_advanced_shadow_e2e_fixture_chain,
)
from app.advanced_shadow_lab.chat_ux_packet import (  # noqa: E402
    build_advanced_shadow_chat_ux_packet,
)
from app.advanced_shadow_lab.live_bundle_profile_gate import (  # noqa: E402
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    resolve_live_bundle_profile_gate,
)
from app.advanced_shadow_lab.live_bundle_fake_providers import (  # noqa: E402
    FakeProactiveCopyDiagnosticProvider,
    FakeRecommendationCopyDiagnosticProvider,
    FakeRescueCopyDiagnosticProvider,
)
from app.advanced_shadow_lab.paired_fixture_cases import (  # noqa: E402
    build_paired_fixture_case_artifacts,
)


ALLOW_ENV = "ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
DEFAULT_OUTPUT = ROOT / "artifacts" / "advanced_shadow_comparison.json"
DEFAULT_ARTIFACT_DIR = ROOT / "artifacts" / "advanced_shadow_lab_live_bundle"
RECOMMENDATION_OUTPUT = "advanced_shadow_recommendation_copy_live_diagnostic.json"
RESCUE_OUTPUT = "advanced_shadow_rescue_copy_live_diagnostic.json"
PROACTIVE_OUTPUT = "advanced_shadow_proactive_copy_live_diagnostic.json"
DOGFOOD_OUTPUT = "advanced_shadow_dogfood_replay.json"
FIXTURE_CHAIN_OUTPUT = "advanced_shadow_e2e_fixture_chain.json"
PAIRED_CASES_OUTPUT = "advanced_shadow_paired_fixture_cases.json"
BASELINE_CASES_OUTPUT = "advanced_shadow_baseline_fixture_cases.json"
ADVANCED_CASES_OUTPUT = "advanced_shadow_advanced_fixture_cases.json"
BLOCKED_RECOMMENDATION_TYPE = "advanced_shadow_recommendation_copy_live_diagnostic_artifact"
BLOCKED_RESCUE_TYPE = "advanced_shadow_rescue_copy_live_diagnostic_artifact"
BLOCKED_PROACTIVE_TYPE = "advanced_shadow_proactive_copy_live_diagnostic_artifact"


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
    parser.add_argument("--provider-profile-id", default=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID)
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    live_profile, profile_blocked = resolve_live_bundle_profile_gate(
        provider_mode=str(args.provider_mode),
        provider_profile_id=str(args.provider_profile_id),
    )
    if profile_blocked is not None:
        _write_json(Path(args.output), profile_blocked)
        _print_terminal_summary(Path(args.output), profile_blocked, str(args.provider_mode))
        return 0

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    memory_review = _read_json(Path(args.memory_dogfood_replay_review))
    chain_payload = _read_json(Path(args.chain_payload))
    fixture_chain = _build_fixture_chain(chain_payload)
    _write_json(artifact_dir / FIXTURE_CHAIN_OUTPUT, fixture_chain)
    dogfood_replay = build_advanced_shadow_dogfood_replay_artifact(
        memory_dogfood_replay_review=memory_review,
        chain_payload=chain_payload,
    )
    _write_json(artifact_dir / DOGFOOD_OUTPUT, dogfood_replay)

    recommendation_report = _stage_artifact(
        fixture_chain, "recommendation_shadow_summary_consumer_quality_report"
    )
    rescue_input = _rescue_shaping_input(chain_payload)
    proactive_input = _mapping(fixture_chain.get("terminal_review_sink"))
    recommendation_live, rescue_live, proactive_live = _run_copy_diagnostics(
        recommendation_report=recommendation_report,
        rescue_input=rescue_input,
        proactive_input=proactive_input,
        provider_mode=str(args.provider_mode),
        allow_live_provider=bool(args.allow_live_provider),
        live_profile=live_profile,
        artifact_dir=artifact_dir,
    )
    fixture_chain["chat_ux_packet"] = build_advanced_shadow_chat_ux_packet(
        fixture_chain_artifact=fixture_chain,
        copy_diagnostic_artifacts=[
            recommendation_live,
            rescue_live,
            proactive_live,
        ],
    )
    _write_json(artifact_dir / FIXTURE_CHAIN_OUTPUT, fixture_chain)
    paired_cases = build_paired_fixture_case_artifacts(
        fixture_chain_artifact=fixture_chain,
    )
    _write_json(artifact_dir / PAIRED_CASES_OUTPUT, paired_cases)
    _write_json(
        artifact_dir / BASELINE_CASES_OUTPUT,
        paired_cases["baseline_case_artifacts"],
    )
    _write_json(
        artifact_dir / ADVANCED_CASES_OUTPUT,
        paired_cases["advanced_case_artifacts"],
    )
    baseline_cases = _read_list(args.baseline_cases) or paired_cases["baseline_case_artifacts"]
    advanced_cases = _read_list(args.advanced_cases) or paired_cases["advanced_case_artifacts"]

    terminal = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=fixture_chain,
        dogfood_replay_artifact=dogfood_replay,
        recommendation_copy_live_diagnostic_artifact=recommendation_live,
        rescue_copy_live_diagnostic_artifact=rescue_live,
        proactive_copy_live_diagnostic_artifact=proactive_live,
        baseline_case_artifacts=baseline_cases,
        advanced_case_artifacts=advanced_cases,
    )
    output = Path(args.output)
    _write_json(output, terminal)
    _print_terminal_summary(output, terminal, str(args.provider_mode))
    return 0


def _run_copy_diagnostics(
    *,
    recommendation_report: Mapping[str, Any],
    rescue_input: Mapping[str, Any],
    proactive_input: Mapping[str, Any],
    provider_mode: str,
    allow_live_provider: bool,
    live_profile: Mapping[str, object] | None,
    artifact_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    recommendation_path = artifact_dir / RECOMMENDATION_OUTPUT
    rescue_path = artifact_dir / RESCUE_OUTPUT
    proactive_path = artifact_dir / PROACTIVE_OUTPUT
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
            proactive = _blocked_not_invoked(
                artifact_type=BLOCKED_PROACTIVE_TYPE,
                output=proactive_path,
                reason="live_gate_not_enabled",
            )
            return recommendation, rescue, proactive
        profile = _mapping(live_profile)
        recommendation_provider = _live_provider(profile, "recommendation_copy")
        rescue_provider = _live_provider(profile, "rescue_copy")
        proactive_provider = _live_provider(profile, "proactive_copy")
        return (
            run_recommendation_copy_live_diagnostic(
                recommendation_summary_report=recommendation_report,
                provider=recommendation_provider,
                provider_mode=str(profile.get("provider_profile_id") or ""),
                live_invoked=True,
                output_path=recommendation_path,
            ),
            run_rescue_copy_live_diagnostic(
                rescue_shaping_input_packet=rescue_input,
                provider=rescue_provider,
                provider_mode=str(profile.get("provider_profile_id") or ""),
                live_invoked=True,
                output_path=rescue_path,
            ),
            run_proactive_copy_live_diagnostic(
                no_send_review_sink=proactive_input,
                provider=proactive_provider,
                provider_mode=str(profile.get("provider_profile_id") or ""),
                live_invoked=True,
                output_path=proactive_path,
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
        run_proactive_copy_live_diagnostic(
            no_send_review_sink=proactive_input,
            provider=FakeProactiveCopyDiagnosticProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
            output_path=proactive_path,
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
    return {
        "artifact_type": "recommendation_shadow_summary_consumer_quality_report",
        "status": "blocked",
        "candidate_count": 0,
        "primary_candidate_id": "",
        "candidate_evaluations": [],
        "blockers": [f"stage_artifact_missing:{artifact_type}"],
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


def _live_provider(profile: Mapping[str, object], role_suffix: str) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    return BuilderSpaceAdapter(
        manager_model_override=str(profile["model_id"]),
        role_label=f"{profile['role_label']}_{role_suffix}",
    )


def _blocked_not_invoked(*, artifact_type: str, output: Path, reason: str) -> dict[str, Any]:
    artifact = {
        "artifact_type": artifact_type,
        "artifact_schema_version": "1.0",
        "status": "not_run",
        "provider_mode": "not_run",
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


def _write_json(path: Path, artifact: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_terminal_summary(
    output: Path, terminal: Mapping[str, Any], provider_mode: str
) -> None:
    print(
        json.dumps(
            {
                "artifact": str(output),
                "artifact_type": str(terminal.get("artifact_type") or ""),
                "status": terminal.get("status"),
                "provider_mode": provider_mode,
                "blockers": terminal.get("blockers"),
            },
            ensure_ascii=False,
        )
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
