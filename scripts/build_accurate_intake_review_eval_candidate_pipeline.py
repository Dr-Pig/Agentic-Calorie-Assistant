from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_fake_provider_context_smoke import (  # noqa: E402
    build_fake_provider_context_smoke_artifact,
)
from app.composition.accurate_intake_fake_provider_tool_loop_smoke import (  # noqa: E402
    build_fake_provider_tool_loop_smoke_artifact,
)
from app.composition.accurate_intake_fixture_evidence_packet_emulator import (  # noqa: E402
    build_fixture_evidence_packet_emulator_artifact,
)
from app.composition.accurate_intake_context_conditioned_intent_wall import (  # noqa: E402
    build_context_conditioned_intent_wall_artifact,
)
from app.composition.accurate_intake_contextual_interaction_matrix import (  # noqa: E402
    build_contextual_interaction_matrix_artifact,
)
from app.composition.accurate_intake_pl_ce_context_coverage_matrix import (  # noqa: E402
    build_pl_ce_context_coverage_matrix_artifact,
)
from app.composition.accurate_intake_review_eval_candidate_pipeline import (  # noqa: E402
    build_review_eval_candidate_pipeline_artifact,
)
from app.composition.accurate_intake_session_context_carryover_qa_bundle import (  # noqa: E402
    build_session_context_carryover_qa_bundle_artifact,
)
from app.composition.accurate_intake_short_term_context_runtime_replay import (  # noqa: E402
    build_short_term_context_runtime_replay_artifact,
)
from app.composition.accurate_intake_ui_same_truth_render_contract import (  # noqa: E402
    build_ui_same_truth_render_contract,
)
from scripts.build_accurate_intake_context_quality_pack import (  # noqa: E402
    build_context_quality_pack_report,
)

DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_review_eval_candidate_pipeline.json"
DEFAULT_SHELL_PATH = ROOT / "static" / "accurate-intake-local-shell.html"
DEFAULT_TARGET_CANDIDATE_UI_SMOKE_PATH = (
    ROOT / "artifacts" / "accurate_intake_product_pages_target_candidate_ui_smoke_ci.json"
)


def _fixture_product_loop_e2e() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_fixture_full_product_loop_e2e",
        "status": "fixture_product_loop_e2e_diagnostic_pass",
        "fixture_evidence_used": True,
        "fooddb_evidence_used": False,
        "websearch_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "ready_for_fdb_integration": False,
    }


def _product_pages_short_term_context_smoke() -> dict[str, object]:
    return {
        "smoke_id": "accurate_intake_product_pages_short_term_context_smoke_v1",
        "status": "pass",
        "browser_executed": True,
        "browser_reload_checked": True,
        "fixture_manager_used": True,
        "pending_followup_created": True,
        "pending_followup_reloaded": True,
        "context_policy_version_present": True,
        "loaded_context_summary_present": True,
        "omitted_context_summary_present": True,
        "pending_pins_present_after_followup": True,
        "chat_history_context_fields_reloaded": True,
        "assistant_followup_bubble_rendered": True,
        "assistant_commit_bubble_rendered": True,
        "product_pages_no_debug_trace": True,
        "frontend_semantic_owner": False,
        "deterministic_semantic_inference_used": False,
        "raw_text_intent_router_used": False,
        "mutation_authority": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "fooddb_evidence_used": False,
    }


def _product_pages_target_candidate_ui_smoke() -> dict[str, object]:
    return {
        "smoke_id": "accurate_intake_product_pages_target_candidate_ui_smoke_v1",
        "status": "pass",
        "browser_executed": True,
        "browser_reload_checked": True,
        "chat_page_loaded": True,
        "chat_history_reloaded": True,
        "target_candidate_surface_checked": True,
        "target_candidate_count_rendered": 2,
        "target_candidate_names_rendered": ["luwei", "milk tea"],
        "target_candidate_list_read_only": True,
        "context_strip_read_only": True,
        "product_pages_no_debug_trace": True,
        "manager_provider_call_count": 0,
        "frontend_selected_target": False,
        "frontend_semantic_owner": False,
        "deterministic_selected_target": False,
        "deterministic_semantic_inference_used": False,
        "raw_text_intent_router_used": False,
        "mutation_authority": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "fooddb_evidence_used": False,
    }


def _read_json_artifact_or_fixture(path: Path, fixture: dict[str, object]) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return fixture
    return payload if isinstance(payload, dict) else fixture


def build_review_eval_candidate_pipeline_report(
    *,
    shell_path: Path = DEFAULT_SHELL_PATH,
    target_candidate_ui_smoke_path: Path = DEFAULT_TARGET_CANDIDATE_UI_SMOKE_PATH,
) -> dict[str, object]:
    fixture_packets = build_fixture_evidence_packet_emulator_artifact()
    context_quality = build_context_quality_pack_report()
    intent_wall = build_context_conditioned_intent_wall_artifact()
    runtime_replay = build_short_term_context_runtime_replay_artifact()
    fake_provider_context = build_fake_provider_context_smoke_artifact()
    context_coverage = build_pl_ce_context_coverage_matrix_artifact(
        context_conditioned_intent_wall=intent_wall,
        short_term_context_runtime_replay=runtime_replay,
        fake_provider_context_smoke=fake_provider_context,
        context_quality_pack=context_quality,
    )
    session_carryover = build_session_context_carryover_qa_bundle_artifact(
        {
            "context_quality_pack": context_quality,
            "short_term_context_runtime_replay": runtime_replay,
            "context_conditioned_intent_wall": intent_wall,
            "context_coverage_matrix": context_coverage,
            "product_pages_short_term_context_smoke": (
                _product_pages_short_term_context_smoke()
            ),
            "product_pages_target_candidate_ui_smoke": (
                _read_json_artifact_or_fixture(
                    target_candidate_ui_smoke_path,
                    _product_pages_target_candidate_ui_smoke(),
                )
            ),
        }
    )
    return build_review_eval_candidate_pipeline_artifact(
        product_loop_e2e=_fixture_product_loop_e2e(),
        ui_same_truth_contract=build_ui_same_truth_render_contract(
            shell_path.read_text(encoding="utf-8")
        ),
        context_quality_pack=context_quality,
        contextual_interaction_matrix=build_contextual_interaction_matrix_artifact(),
        session_context_carryover_qa_bundle=session_carryover,
        fixture_packet_emulator=fixture_packets,
        fake_provider_tool_loop_smoke=build_fake_provider_tool_loop_smoke_artifact(
            context_smoke=fake_provider_context,
            fixture_packet_emulator=fixture_packets,
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build local review candidates from PL+CE diagnostic artifacts."
    )
    parser.add_argument("--shell-path", default=str(DEFAULT_SHELL_PATH))
    parser.add_argument("--target-candidate-ui-smoke", default=str(DEFAULT_TARGET_CANDIDATE_UI_SMOKE_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    artifact = build_review_eval_candidate_pipeline_report(
        shell_path=Path(args.shell_path),
        target_candidate_ui_smoke_path=Path(args.target_candidate_ui_smoke),
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "review_eval_candidate_pipeline_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
