from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from fastapi import FastAPI
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition import intake_routes  # noqa: E402
from app.composition.accurate_intake_manager_tool_choice_regression_wall import (  # noqa: E402
    build_manager_tool_choice_regression_wall_artifact,
)
from app.composition.accurate_intake_manager_tool_surface_inventory import (  # noqa: E402
    build_manager_tool_surface_inventory_artifact,
)
from app.composition.accurate_intake_body_observation_same_truth_gate import (  # noqa: E402
    build_body_observation_same_truth_gate_artifact,
)
from app.composition.accurate_intake_bootstrap_same_truth_gate import (  # noqa: E402
    build_bootstrap_same_truth_gate_artifact,
)
from app.composition.accurate_intake_clarify_commit_correction_same_truth_gate import (  # noqa: E402
    build_clarify_commit_correction_same_truth_gate_artifact,
)
from app.composition.accurate_intake_non_fooddb_manager_tool_contract import (  # noqa: E402
    build_non_fooddb_manager_tool_contract_artifact,
)
from app.composition.accurate_intake_non_fooddb_mutation_tool_guard_smoke import (  # noqa: E402
    build_non_fooddb_mutation_tool_guard_smoke_artifact,
)
from app.composition.accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke import (  # noqa: E402
    build_non_fooddb_read_only_tool_loop_fake_smoke_artifact,
)
from app.composition.accurate_intake_pl_ce_browser_activation_evidence_gate import (  # noqa: E402
    REQUIRED_INPUTS as BROWSER_GATE_REQUIRED_INPUTS,
    build_pl_ce_browser_activation_evidence_gate_artifact,
)
from app.composition.accurate_intake_pl_ce_product_pages_self_use_flow_gate import (  # noqa: E402
    build_pl_ce_product_pages_self_use_flow_gate_artifact,
)
from app.composition.accurate_intake_product_pages_renderer_source_map import (  # noqa: E402
    build_product_pages_renderer_source_closure_artifact,
    build_product_pages_renderer_source_map_artifact,
)
from app.composition.accurate_intake_today_macro_mirror_gate import (  # noqa: E402
    build_today_macro_runtime_mirror_gate_artifact,
)
from app.composition.accurate_intake_today_macro_mirror_gate import (  # noqa: E402
    build_today_macro_mirror_gate_artifact,
)
from app.composition.accurate_intake_ui_same_truth_render_contract import (  # noqa: E402
    build_ui_same_truth_render_contract,
)
from app.composition.dogfood_review_queue import (  # noqa: E402
    build_dogfood_review_queue_artifact,
    build_review_candidate_from_product_loop_diagnostic,
)
from app.shared.domain.canonical_models import CurrentBudgetView  # noqa: E402
from app.nutrition.application.approved_packet_ready_fooddb_artifact import (  # noqa: E402
    build_approved_packet_ready_fooddb_artifact,
)
from app.database import get_db  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402
from app.shared.infra.sqlite_route_harness import LocalSQLiteRouteHarness  # noqa: E402
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.build_current_shell_compatibility_product_pages_self_use_flow_gate import (  # noqa: E402
    DEFAULT_ARTIFACT_PATHS as PRODUCT_PAGES_FLOW_ARTIFACT_PATHS,
    build_input_artifacts as build_product_pages_flow_inputs,
)
from scripts.build_current_shell_compatibility_local_review_decision_pack import (  # noqa: E402
    build_current_shell_compatibility_local_review_decision_pack,
)
from scripts.build_current_shell_compatibility_local_review_evidence_manifest import (  # noqa: E402
    DEFAULT_EVIDENCE_PATHS as LOCAL_REVIEW_EVIDENCE_PATHS,
    build_current_shell_compatibility_local_review_evidence_manifest,
)
from scripts.build_accurate_intake_local_web_self_use_candidate_v2 import (  # noqa: E402
    build_local_web_self_use_candidate_v2,
)
from scripts.build_accurate_intake_product_loop_handoff_v3 import (  # noqa: E402
    build_product_loop_handoff_v3,
)
from scripts.build_current_shell_compatibility_browser_activation_evidence_gate import (  # noqa: E402
    DEFAULT_ARTIFACT_PATHS as BROWSER_GATE_ARTIFACT_PATHS,
)
from scripts.build_accurate_intake_pre_live_self_use_decision_pack import (  # noqa: E402
    build_pre_live_self_use_decision_pack,
)
from scripts.run_accurate_intake_context_live_diagnostic_gate import (  # noqa: E402
    build_context_live_diagnostic_gate_artifact,
)
from scripts.run_accurate_intake_product_pages_browser_smoke import (  # noqa: E402
    build_product_pages_browser_smoke_report,
)
from scripts.run_accurate_intake_product_pages_body_noplan_degraded_smoke import (  # noqa: E402
    build_body_noplan_degraded_smoke_report,
)
from scripts.run_accurate_intake_product_pages_seven_day_diary_smoke import (  # noqa: E402
    build_seven_day_diary_smoke_report,
)
from scripts.run_accurate_intake_product_pages_short_term_context_smoke import (  # noqa: E402
    build_product_pages_short_term_context_smoke_report,
)
from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (  # noqa: E402
    DEFAULT_EVIDENCE_PATHS,
    build_candidate_evidence_payload,
    build_local_web_candidate_gate_evidence,
)
from scripts.run_accurate_intake_mvp_manager_style_smoke import (  # noqa: E402
    DeterministicSelfUseManagerProvider,
    _seed_body_plan,
)


REFRESHED_ARTIFACT_FILENAMES = {
    "manager_tool_surface_inventory": "accurate_intake_manager_tool_surface_inventory.json",
    "manager_tool_choice_regression_wall": "accurate_intake_manager_tool_choice_regression_wall.json",
    "non_fooddb_read_only_tool_loop_fake_smoke": "accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke.json",
    "non_fooddb_mutation_tool_guard_smoke": "accurate_intake_non_fooddb_mutation_tool_guard_smoke.json",
    "product_pages_self_use_flow_gate": (
        "accurate_intake_current_shell_compatibility_product_pages_self_use_flow_gate.json"
    ),
    "today_macro_mirror_gate": "accurate_intake_today_macro_mirror_gate.json",
    "bootstrap_same_truth_gate": "accurate_intake_bootstrap_same_truth_gate.json",
    "body_observation_same_truth_gate": "accurate_intake_body_observation_same_truth_gate.json",
    "clarify_commit_correction_same_truth_gate": "accurate_intake_clarify_commit_correction_same_truth_gate.json",
    "browser_activation_evidence_gate": (
        "accurate_intake_current_shell_compatibility_browser_activation_evidence_gate.json"
    ),
    "non_fooddb_manager_tool_contract": "accurate_intake_non_fooddb_manager_tool_contract.json",
    "ui_same_truth_contract": "accurate_intake_ui_same_truth_render_contract.json",
    "product_pages_renderer_source_map": "accurate_intake_product_pages_renderer_source_map.json",
    "today_macro_runtime_mirror_gate": "accurate_intake_today_macro_runtime_mirror_gate.json",
    "product_pages_renderer_source_closure_gate": (
        "accurate_intake_product_pages_renderer_source_closure_gate.json"
    ),
    "product_pages_browser_smoke": "accurate_intake_product_pages_browser_smoke.json",
    "product_pages_seven_day_diary_smoke": (
        "accurate_intake_product_pages_seven_day_diary_smoke.json"
    ),
    "product_pages_body_noplan_degraded_smoke": (
        "accurate_intake_product_pages_body_noplan_degraded_smoke.json"
    ),
    "product_pages_short_term_context_smoke": (
        "accurate_intake_product_pages_short_term_context_smoke.json"
    ),
    "context_live_diagnostic_gate": "accurate_intake_context_live_diagnostic_gate.json",
    "current_shell_compatibility_local_review_evidence_manifest": (
        "accurate_intake_current_shell_compatibility_local_review_evidence_manifest.json"
    ),
    "current_shell_compatibility_local_review_decision_pack": (
        "accurate_intake_current_shell_compatibility_local_review_decision_pack.json"
    ),
    "dogfood_review_queue": "accurate_intake_dogfood_review_queue.json",
    "pre_live_evidence": "accurate_intake_pre_live_evidence.json",
    "pre_live_decision_pack": "accurate_intake_pre_live_self_use_decision_pack.json",
    "local_web_candidate": "accurate_intake_local_web_self_use_candidate_v2.json",
    "approved_packet_ready_fooddb_artifact": (
        "accurate_intake_approved_packet_ready_fooddb_artifact.json"
    ),
    "product_loop_handoff": "accurate_intake_product_loop_handoff_v3.json",
}

PRODUCT_LOOP_HANDOFF_EVIDENCE_FILENAMES = {
    "browser_fixture_dogfood": "accurate_intake_browser_one_day_fixture_dogfood.json",
    "browser_realistic_dogfood": "accurate_intake_browser_realistic_web_dogfood_v2.json",
    "operator_review": "accurate_intake_dogfood_operator_review_v2.json",
}
CLOSEOUT_NON_CLAIMS = {
    "product_ready": False,
    "web_ready": False,
    "private_self_use_approved": False,
    "production_ready": False,
    "live_llm_ready": False,
    "fooddb_truth_promoted": False,
}
ROUTE_BACKED_MACRO_LOCAL_DATE = "2026-05-09"
ROUTE_BACKED_MACRO_PRESENT_TEXT = "\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73(400ml)"
ROUTE_BACKED_MACRO_MISSING_TEXT = "\u722d\u9bae \u7126\u7cd6\u9bae\u9b5a(\u5169\u8cab)"
STATIC_MACRO_LOCAL_DATE = "2026-05-09"


def _artifact_path(artifacts_dir: Path, filename: str) -> Path:
    return artifacts_dir / filename


def _group_path(artifacts_dir: Path, path: Path) -> Path:
    return artifacts_dir / path.name


def _read_payload(path: Path) -> dict[str, Any]:
    try:
        payload = read_json_artifact(path)
    except FileNotFoundError:
        return {
            "artifact_type": "missing",
            "status": "missing",
            "_source_artifact_path": str(path),
            "autofix_attempted": False,
        }
    except (OSError, ValueError, json.JSONDecodeError):
        return {
            "artifact_type": "invalid_json",
            "status": "invalid_json",
            "_source_artifact_path": str(path),
            "autofix_attempted": False,
        }
    payload.setdefault("_source_artifact_path", str(path))
    return payload


def _read_yaml_payload(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _object_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _payload_status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _payload_blockers(payload: dict[str, Any]) -> list[str]:
    blockers = _string_list(payload.get("blockers"))
    metadata = _object_dict(payload.get("_manifest_metadata"))
    blockers.extend(f"missing_evidence:{item}" for item in _string_list(metadata.get("missing_evidence")))
    blockers.extend(f"missing_evidence:{item}" for item in _string_list(payload.get("missing_evidence")))
    return blockers


def _missing_evidence_from_blockers(ordered_payloads: list[tuple[str, dict[str, Any]]]) -> list[str]:
    root_missing: list[str] = []
    downstream_missing: list[str] = []
    aliases = {
        "target_candidate_ui_smoke": "product_pages_target_candidate_ui_smoke",
    }
    for _gate_id, payload in ordered_payloads:
        for blocker in _payload_blockers(payload):
            if ".unexpected_status:missing" in blocker:
                item = blocker.split(".", 1)[0]
                root_missing.append(aliases.get(item, item))
            elif blocker.startswith("missing_evidence:"):
                downstream_missing.append(blocker.split(":", 1)[1])
            elif blocker.startswith("pre-live missing evidence: "):
                downstream_missing.append(blocker.removeprefix("pre-live missing evidence: "))
            elif blocker.startswith("missing evidence: "):
                downstream_missing.append(blocker.removeprefix("missing evidence: "))
    selected = root_missing if root_missing else downstream_missing
    return sorted({item for item in selected if item})


def _stale_evidence_from_blockers(ordered_payloads: list[tuple[str, dict[str, Any]]]) -> list[str]:
    if _missing_evidence_from_blockers(ordered_payloads):
        return []
    stale: list[str] = []
    for _gate_id, payload in ordered_payloads:
        for blocker in _payload_blockers(payload):
            if ".unexpected_status:" in blocker and ".unexpected_status:missing" not in blocker:
                stale.append(blocker.split(".", 1)[0])
            elif blocker.startswith("failed evidence: "):
                stale.append(blocker.removeprefix("failed evidence: ").split(" ", 1)[0])
    return sorted({item for item in stale if item})


def _first_blocking_gate(
    ordered_payloads: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any] | None:
    blocking_statuses = {
        "blocked",
        "blocked_missing_evidence",
        "fail",
        "failed",
        "invalid_json",
        "missing",
    }
    for gate_id, payload in ordered_payloads:
        status = _payload_status(payload)
        blockers = _payload_blockers(payload)
        if status in blocking_statuses or blockers:
            return {
                "gate_id": gate_id,
                "status": status,
                "blocker_count": len(blockers),
                "first_blocker": blockers[0] if blockers else None,
            }
    return None


def _build_closeout_navigation(
    ordered_payloads: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    return {
        "missing_evidence": _missing_evidence_from_blockers(ordered_payloads),
        "stale_evidence": _stale_evidence_from_blockers(ordered_payloads),
        "first_blocking_gate": _first_blocking_gate(ordered_payloads),
        "non_claims": dict(CLOSEOUT_NON_CLAIMS),
    }


def _append_mismatch(
    blockers: list[str],
    *,
    name: str,
    actual: Any,
    expected: Any,
) -> None:
    if actual != expected:
        blockers.append(f"{name}.expected:{expected}.actual:{actual}")


def _macro_route_case(
    client: Any,
    *,
    text: str,
    user_external_id: str,
    expected_kcal: int,
    expected_show_macro: bool,
    expected_guard_reason: str,
    expected_protein: int,
    expected_carbs: int,
    expected_fat: int,
    expected_trace_visibility: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    estimate_response = client.post(
        "/estimate",
        json={
            "text": text,
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": ROUTE_BACKED_MACRO_LOCAL_DATE,
        },
    )
    estimate_body = _object_dict(estimate_response.json()) if estimate_response.status_code == 200 else {}
    route_payload = _object_dict(estimate_body.get("payload"))
    sidecar = _object_dict(route_payload.get("sidecar"))
    macro = _object_dict(sidecar.get("macro"))
    state_delta = _object_dict(route_payload.get("state_delta"))
    manager_final = _object_dict(
        _object_dict(route_payload.get("intake_execution_manager")).get("final")
    )
    exact_trace = _object_dict(macro.get("approved_exact_macro_trace"))

    budget_response = client.get(
        "/today/current-budget",
        params={"user_id": user_external_id, "local_date": ROUTE_BACKED_MACRO_LOCAL_DATE},
    )
    current_budget = (
        _object_dict(budget_response.json()) if budget_response.status_code == 200 else {}
    )

    actual_values = {
        "estimate_route.status_code": estimate_response.status_code,
        "today_current_budget.status_code": budget_response.status_code,
        "state_delta.canonical_commit": state_delta.get("canonical_commit"),
        "manager_final.final_action": manager_final.get("final_action"),
        "current_budget.consumed_kcal": current_budget.get("consumed_kcal"),
        "current_budget.consumed_protein": current_budget.get("consumed_protein"),
        "current_budget.consumed_carbs": current_budget.get("consumed_carbs"),
        "current_budget.consumed_fat": current_budget.get("consumed_fat"),
        "current_budget.show_macro": current_budget.get("show_macro"),
        "current_budget.macro_guard_reason": current_budget.get("macro_guard_reason"),
        "approved_exact_macro_trace.macro_truth_owner": exact_trace.get("macro_truth_owner"),
        "approved_exact_macro_trace.macro_visibility_status": exact_trace.get(
            "macro_visibility_status"
        ),
        "approved_exact_macro_trace.live_llm_invoked": exact_trace.get("live_llm_invoked"),
        "approved_exact_macro_trace.websearch_evidence_used": exact_trace.get(
            "websearch_evidence_used"
        ),
    }
    expected_values = {
        "estimate_route.status_code": 200,
        "today_current_budget.status_code": 200,
        "state_delta.canonical_commit": True,
        "manager_final.final_action": "commit",
        "current_budget.consumed_kcal": expected_kcal,
        "current_budget.consumed_protein": expected_protein,
        "current_budget.consumed_carbs": expected_carbs,
        "current_budget.consumed_fat": expected_fat,
        "current_budget.show_macro": expected_show_macro,
        "current_budget.macro_guard_reason": expected_guard_reason,
        "approved_exact_macro_trace.macro_truth_owner": "fooddb_approved_packet",
        "approved_exact_macro_trace.macro_visibility_status": expected_trace_visibility,
        "approved_exact_macro_trace.live_llm_invoked": False,
        "approved_exact_macro_trace.websearch_evidence_used": False,
    }
    for name, expected in expected_values.items():
        _append_mismatch(
            blockers,
            name=name,
            actual=actual_values.get(name),
            expected=expected,
        )

    return {
        "status": "pass" if not blockers else "blocked",
        "text": text,
        "estimate_status_code": estimate_response.status_code,
        "today_current_budget_status_code": budget_response.status_code,
        "route_final_action": manager_final.get("final_action"),
        "state_delta": {
            "canonical_commit": state_delta.get("canonical_commit"),
        },
        "macro_sidecar": {
            "protein_g": macro.get("protein_g"),
            "carbs_g": macro.get("carbs_g"),
            "fat_g": macro.get("fat_g"),
            "display_status": macro.get("display_status"),
            "guard_reason": macro.get("guard_reason"),
        },
        "approved_exact_macro_trace": exact_trace,
        "current_budget": {
            "consumed_kcal": current_budget.get("consumed_kcal"),
            "consumed_protein": current_budget.get("consumed_protein"),
            "consumed_carbs": current_budget.get("consumed_carbs"),
            "consumed_fat": current_budget.get("consumed_fat"),
            "show_macro": current_budget.get("show_macro"),
            "macro_guard_reason": current_budget.get("macro_guard_reason"),
        },
        "blockers": blockers,
    }


def build_route_backed_macro_closeout(*, artifacts_dir: Path) -> dict[str, Any]:
    db_path = artifacts_dir / "accurate_intake_route_backed_macro_closeout.sqlite3"
    if db_path.exists():
        db_path.unlink()

    app = FastAPI()
    app.include_router(router)
    provider = DeterministicSelfUseManagerProvider()
    previous_runtime = (
        intake_routes.manager_provider,
        intake_routes.search_provider,
        intake_routes.extract_provider,
    )
    intake_routes.manager_provider = provider
    intake_routes.search_provider = None
    intake_routes.extract_provider = None
    try:
        with LocalSQLiteRouteHarness(
            app=app,
            db_dependency=get_db,
            db_path=db_path,
            base_metadata=Base.metadata,
        ) as harness:
            if harness.SessionLocal is None or harness.client is None:
                raise RuntimeError("route harness did not initialize")
            with harness.SessionLocal() as db:
                _seed_body_plan(
                    db,
                    user_external_id="route-macro-present-closeout",
                    local_date=ROUTE_BACKED_MACRO_LOCAL_DATE,
                )
                _seed_body_plan(
                    db,
                    user_external_id="route-macro-missing-closeout",
                    local_date=ROUTE_BACKED_MACRO_LOCAL_DATE,
                )
            present_case = _macro_route_case(
                harness.client,
                text=ROUTE_BACKED_MACRO_PRESENT_TEXT,
                user_external_id="route-macro-present-closeout",
                expected_kcal=300,
                expected_show_macro=True,
                expected_guard_reason="committed_and_aligned",
                expected_protein=12,
                expected_carbs=48,
                expected_fat=6,
                expected_trace_visibility="visible",
            )
            missing_case = _macro_route_case(
                harness.client,
                text=ROUTE_BACKED_MACRO_MISSING_TEXT,
                user_external_id="route-macro-missing-closeout",
                expected_kcal=130,
                expected_show_macro=False,
                expected_guard_reason="no_macro_data",
                expected_protein=0,
                expected_carbs=0,
                expected_fat=0,
                expected_trace_visibility="hidden_missing_source",
            )
    finally:
        (
            intake_routes.manager_provider,
            intake_routes.search_provider,
            intake_routes.extract_provider,
        ) = previous_runtime

    blockers = [
        f"macro_present_exact_item.{blocker}"
        for blocker in list(present_case.get("blockers") or [])
    ]
    blockers.extend(
        f"macro_missing_exact_item.{blocker}"
        for blocker in list(missing_case.get("blockers") or [])
    )
    if provider.readiness().get("live_llm_invoked") is not False:
        blockers.append("provider.live_llm_invoked_not_false")

    return {
        "artifact_type": "accurate_intake_route_backed_macro_closeout",
        "status": "pass" if not blockers else "blocked",
        "route_backed_macro_checked": not blockers,
        "claim_scope": "local_route_backed_macro_closeout_only",
        "macro_present_exact_item": present_case,
        "macro_missing_exact_item": missing_case,
        "non_claims": {
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "blockers": blockers,
    }


def _browser_gate_inputs(artifacts_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        group_id: _read_payload(_group_path(artifacts_dir, BROWSER_GATE_ARTIFACT_PATHS[group_id]))
        for group_id in BROWSER_GATE_REQUIRED_INPUTS
    }


def _product_pages_flow_path_overrides(artifacts_dir: Path) -> dict[str, Path]:
    return {
        group_id: _group_path(artifacts_dir, path)
        for group_id, path in PRODUCT_PAGES_FLOW_ARTIFACT_PATHS.items()
    }


def _local_gate_path_overrides(artifacts_dir: Path) -> dict[str, Path]:
    return {
        group_id: _group_path(artifacts_dir, path)
        for group_id, path in DEFAULT_EVIDENCE_PATHS.items()
    }


def _local_review_path_overrides(artifacts_dir: Path) -> dict[str, Path]:
    return {
        group_id: _group_path(artifacts_dir, path)
        for group_id, path in LOCAL_REVIEW_EVIDENCE_PATHS.items()
    }


def _static_macro_current_budget_payload() -> dict[str, Any]:
    view = CurrentBudgetView(
        user_id=1,
        local_date=STATIC_MACRO_LOCAL_DATE,
        budget_kcal=1800,
        consumed_kcal=640,
        consumed_protein=31,
        consumed_carbs=44,
        consumed_fat=12,
        show_macro=True,
        macro_guard_reason=None,
        remaining_kcal=1160,
        active_meal_count=2,
    )
    return view.model_dump(mode="json")


def _generate_static_product_page_inputs(
    *,
    artifacts_dir: Path,
) -> dict[str, dict[str, Any]]:
    ui_contract = build_ui_same_truth_render_contract(
        (ROOT / "static" / "accurate-intake-local-shell.html").read_text(encoding="utf-8")
    )
    renderer_source_map = build_product_pages_renderer_source_map_artifact()
    manager_gate_ledger = _read_yaml_payload(
        ROOT / "docs" / "quality" / "MANAGER_RUNTIME_GATE_LEDGER.yaml"
    )
    today_macro_runtime = build_today_macro_runtime_mirror_gate_artifact(
        manager_gate_ledger_artifact=manager_gate_ledger,
        current_budget_payload=_static_macro_current_budget_payload(),
        renderer_source_map_artifact=renderer_source_map,
    )
    renderer_source_closure = build_product_pages_renderer_source_closure_artifact(
        manager_gate_ledger_artifact=manager_gate_ledger,
        renderer_source_map_artifact=renderer_source_map,
    )
    artifacts = {
        "ui_same_truth_contract": ui_contract,
        "product_pages_renderer_source_map": renderer_source_map,
        "today_macro_runtime_mirror_gate": today_macro_runtime,
        "product_pages_renderer_source_closure_gate": renderer_source_closure,
    }
    for group_id, artifact in artifacts.items():
        write_json_artifact(
            _group_path(artifacts_dir, PRODUCT_PAGES_FLOW_ARTIFACT_PATHS[group_id]),
            artifact,
        )
    return artifacts


def _generate_product_pages_browser_smoke(*, artifacts_dir: Path) -> dict[str, Any]:
    return build_product_pages_browser_smoke_report(
        db_path=artifacts_dir / "accurate_intake_product_pages_browser_smoke.sqlite3",
        reset_db=True,
        require_browser_execution=True,
        timeout_ms=30000,
        headless=True,
    )


def _generate_product_pages_seven_day_diary_smoke(*, artifacts_dir: Path) -> dict[str, Any]:
    return build_seven_day_diary_smoke_report(
        db_path=artifacts_dir / "accurate_intake_product_pages_seven_day_diary_smoke.sqlite3",
        reset_db=True,
        require_browser_execution=True,
        timeout_ms=30000,
        headless=True,
    )


def _generate_product_pages_body_noplan_degraded_smoke(*, artifacts_dir: Path) -> dict[str, Any]:
    return build_body_noplan_degraded_smoke_report(
        db_path=artifacts_dir / "accurate_intake_product_pages_body_noplan_degraded.sqlite3",
        reset_db=True,
        require_browser_execution=True,
        timeout_ms=30000,
        headless=True,
    )


def _generate_product_pages_short_term_context_smoke(*, artifacts_dir: Path) -> dict[str, Any]:
    return build_product_pages_short_term_context_smoke_report(
        db_path=artifacts_dir / "accurate_intake_product_pages_short_term_context_smoke.sqlite3",
        reset_db=True,
        require_browser_execution=True,
        timeout_ms=30000,
        headless=True,
    )


def _product_loop_handoff_evidence(
    artifacts_dir: Path,
    *,
    local_web_candidate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "browser_shell_smoke": _read_payload(
            _group_path(artifacts_dir, DEFAULT_EVIDENCE_PATHS["browser_shell_smoke"])
        ),
        "local_web_candidate": local_web_candidate,
        "browser_fixture_dogfood": _read_payload(
            _artifact_path(
                artifacts_dir,
                PRODUCT_LOOP_HANDOFF_EVIDENCE_FILENAMES["browser_fixture_dogfood"],
            )
        ),
        "local_dogfood_hygiene": _read_payload(
            _group_path(
                artifacts_dir,
                DEFAULT_EVIDENCE_PATHS["local_dogfood_data_hygiene"],
            )
        ),
        "browser_realistic_dogfood": _read_payload(
            _artifact_path(
                artifacts_dir,
                PRODUCT_LOOP_HANDOFF_EVIDENCE_FILENAMES["browser_realistic_dogfood"],
            )
        ),
        "operator_review": _read_payload(
            _artifact_path(
                artifacts_dir,
                PRODUCT_LOOP_HANDOFF_EVIDENCE_FILENAMES["operator_review"],
            )
        ),
        "mvp_gate": _read_payload(
            _group_path(artifacts_dir, DEFAULT_EVIDENCE_PATHS["accurate_intake_mvp_gate"])
        ),
    }


def _dogfood_review_candidates_from_closeout_diagnostics(
    artifacts_dir: Path,
) -> list[dict[str, Any]]:
    browser_realistic = _read_payload(
        _artifact_path(
            artifacts_dir,
            PRODUCT_LOOP_HANDOFF_EVIDENCE_FILENAMES["browser_realistic_dogfood"],
        )
    )
    if (
        browser_realistic.get("artifact_type")
        == "accurate_intake_browser_realistic_web_dogfood_v2"
        and "evidence_gap" in str(browser_realistic.get("status") or "")
    ):
        return [build_review_candidate_from_product_loop_diagnostic(browser_realistic)]
    return []


def build_local_web_self_use_candidate_refresh_chain(
    *,
    artifacts_dir: Path,
) -> dict[str, Any]:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    route_backed_macro_closeout = build_route_backed_macro_closeout(
        artifacts_dir=artifacts_dir
    )
    route_backed_macro_checked = route_backed_macro_closeout.get(
        "route_backed_macro_checked"
    ) is True

    refreshed_artifacts = {
        "manager_tool_surface_inventory": build_manager_tool_surface_inventory_artifact(),
        "non_fooddb_manager_tool_contract": build_non_fooddb_manager_tool_contract_artifact(),
        "manager_tool_choice_regression_wall": build_manager_tool_choice_regression_wall_artifact(),
        "non_fooddb_read_only_tool_loop_fake_smoke": build_non_fooddb_read_only_tool_loop_fake_smoke_artifact(),
        "non_fooddb_mutation_tool_guard_smoke": build_non_fooddb_mutation_tool_guard_smoke_artifact(),
    }
    refreshed_artifacts.update(
        _generate_static_product_page_inputs(artifacts_dir=artifacts_dir)
    )
    refreshed_artifacts["product_pages_browser_smoke"] = _generate_product_pages_browser_smoke(
        artifacts_dir=artifacts_dir
    )
    refreshed_artifacts["product_pages_seven_day_diary_smoke"] = (
        _generate_product_pages_seven_day_diary_smoke(artifacts_dir=artifacts_dir)
    )
    refreshed_artifacts["product_pages_body_noplan_degraded_smoke"] = (
        _generate_product_pages_body_noplan_degraded_smoke(artifacts_dir=artifacts_dir)
    )
    refreshed_artifacts["product_pages_short_term_context_smoke"] = (
        _generate_product_pages_short_term_context_smoke(artifacts_dir=artifacts_dir)
    )
    for group_id, artifact in refreshed_artifacts.items():
        write_json_artifact(
            _artifact_path(artifacts_dir, REFRESHED_ARTIFACT_FILENAMES[group_id]),
            artifact,
        )

    body_observation_same_truth_gate = build_body_observation_same_truth_gate_artifact(
        browser_smoke_artifact=_read_payload(
            _group_path(artifacts_dir, PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["product_pages_browser_smoke"])
        )
    )
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["body_observation_same_truth_gate"],
        ),
        body_observation_same_truth_gate,
    )

    product_pages_self_use_flow_gate = build_pl_ce_product_pages_self_use_flow_gate_artifact(
        build_product_pages_flow_inputs(
            path_overrides=_product_pages_flow_path_overrides(artifacts_dir)
        )
    )
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["product_pages_self_use_flow_gate"],
        ),
        product_pages_self_use_flow_gate,
    )

    today_macro_mirror_gate = build_today_macro_mirror_gate_artifact()
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["today_macro_mirror_gate"],
        ),
        today_macro_mirror_gate,
    )

    bootstrap_same_truth_gate = build_bootstrap_same_truth_gate_artifact(
        browser_smoke_artifact=_read_payload(
            _group_path(artifacts_dir, PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["product_pages_browser_smoke"])
        )
    )
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["bootstrap_same_truth_gate"],
        ),
        bootstrap_same_truth_gate,
    )

    clarify_commit_correction_same_truth_gate = (
        build_clarify_commit_correction_same_truth_gate_artifact(
            product_pages_browser_smoke=_read_payload(
                _group_path(artifacts_dir, PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["product_pages_browser_smoke"])
            ),
            short_term_context_smoke=_read_payload(
                _group_path(
                    artifacts_dir,
                    PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["product_pages_short_term_context_smoke"],
                )
            ),
            target_candidate_ui_smoke=_read_payload(
                _group_path(
                    artifacts_dir,
                    PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["product_pages_target_candidate_ui_smoke"],
                )
            ),
            fixture_full_product_loop_e2e=_read_payload(
                _group_path(artifacts_dir, PRODUCT_PAGES_FLOW_ARTIFACT_PATHS["fixture_full_product_loop_e2e"])
            ),
        )
    )
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["clarify_commit_correction_same_truth_gate"],
        ),
        clarify_commit_correction_same_truth_gate,
    )

    browser_activation_evidence_gate = build_pl_ce_browser_activation_evidence_gate_artifact(
        _browser_gate_inputs(artifacts_dir)
    )
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["browser_activation_evidence_gate"],
        ),
        browser_activation_evidence_gate,
    )

    context_live_diagnostic_gate = build_context_live_diagnostic_gate_artifact(
        artifact_dir=artifacts_dir
    )
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["context_live_diagnostic_gate"],
        ),
        context_live_diagnostic_gate,
    )

    local_review_manifest = (
        build_current_shell_compatibility_local_review_evidence_manifest(
            path_overrides=_local_review_path_overrides(artifacts_dir)
        )
    )
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES[
                "current_shell_compatibility_local_review_evidence_manifest"
            ],
        ),
        local_review_manifest,
    )

    local_review_decision_path = _artifact_path(
        artifacts_dir,
        REFRESHED_ARTIFACT_FILENAMES[
            "current_shell_compatibility_local_review_decision_pack"
        ],
    )
    local_review_manifest_status = _object_dict(
        local_review_manifest.get("_manifest_metadata")
    ).get("status")
    if local_review_manifest_status == "complete" or not local_review_decision_path.exists():
        local_review_decision_pack = (
            build_current_shell_compatibility_local_review_decision_pack(
                local_review_manifest
            )
        )
        write_json_artifact(local_review_decision_path, local_review_decision_pack)

    dogfood_review_queue = build_dogfood_review_queue_artifact(
        review_candidates=_dogfood_review_candidates_from_closeout_diagnostics(artifacts_dir),
        correction_feedback_events=[],
    )
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["dogfood_review_queue"],
        ),
        dogfood_review_queue,
    )

    pre_live_evidence = build_local_web_candidate_gate_evidence(
        path_overrides=_local_gate_path_overrides(artifacts_dir)
    )
    write_json_artifact(
        _artifact_path(artifacts_dir, REFRESHED_ARTIFACT_FILENAMES["pre_live_evidence"]),
        pre_live_evidence,
    )

    pre_live_decision_pack = build_pre_live_self_use_decision_pack(pre_live_evidence)
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["pre_live_decision_pack"],
        ),
        pre_live_decision_pack,
    )

    local_web_candidate = build_local_web_self_use_candidate_v2(
        build_candidate_evidence_payload(pre_live_evidence, pre_live_decision_pack)
    )
    local_web_candidate_payload = dict(
        local_web_candidate.get("local_web_self_use_candidate_v2") or {}
    )
    local_web_candidate_payload["route_backed_macro_checked"] = route_backed_macro_checked
    local_web_candidate_payload["route_backed_macro_closeout_status"] = (
        route_backed_macro_closeout.get("status")
    )
    local_web_candidate_payload["route_backed_macro_non_claims"] = dict(
        route_backed_macro_closeout.get("non_claims") or {}
    )
    if not route_backed_macro_checked:
        blockers = list(local_web_candidate_payload.get("blockers") or [])
        blockers.extend(
            f"route_backed_macro_closeout.{blocker}"
            for blocker in list(route_backed_macro_closeout.get("blockers") or [])
        )
        local_web_candidate_payload["candidate_prepared"] = False
        local_web_candidate_payload["blockers"] = blockers
    local_web_candidate["local_web_self_use_candidate_v2"] = local_web_candidate_payload
    write_json_artifact(
        _artifact_path(artifacts_dir, REFRESHED_ARTIFACT_FILENAMES["local_web_candidate"]),
        local_web_candidate,
    )

    approved_fooddb_artifact_path = _artifact_path(
        artifacts_dir,
        REFRESHED_ARTIFACT_FILENAMES["approved_packet_ready_fooddb_artifact"],
    )
    approved_fooddb_artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path=str(approved_fooddb_artifact_path)
    )
    write_json_artifact(approved_fooddb_artifact_path, approved_fooddb_artifact)

    product_loop_handoff = build_product_loop_handoff_v3(
        _product_loop_handoff_evidence(
            artifacts_dir,
            local_web_candidate=local_web_candidate,
        ),
        fooddb_artifact=approved_fooddb_artifact,
    )
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["product_loop_handoff"],
        ),
        product_loop_handoff,
    )

    candidate_payload = dict(local_web_candidate.get("local_web_self_use_candidate_v2") or {})
    appshell_browser_evidence_chain = dict(
        candidate_payload.get("appshell_browser_evidence_chain") or {}
    )
    candidate_prepared = candidate_payload.get("candidate_prepared") is True
    closeout_payloads = [
        ("route_backed_macro_closeout", route_backed_macro_closeout),
        ("product_pages_self_use_flow_gate", product_pages_self_use_flow_gate),
        ("today_macro_mirror_gate", today_macro_mirror_gate),
        ("bootstrap_same_truth_gate", bootstrap_same_truth_gate),
        ("body_observation_same_truth_gate", body_observation_same_truth_gate),
        (
            "clarify_commit_correction_same_truth_gate",
            clarify_commit_correction_same_truth_gate,
        ),
        ("browser_activation_evidence_gate", browser_activation_evidence_gate),
        ("context_live_diagnostic_gate", context_live_diagnostic_gate),
        ("dogfood_review_queue", dogfood_review_queue),
        ("pre_live_evidence", pre_live_evidence),
        ("pre_live_decision_pack", pre_live_decision_pack),
        ("local_web_candidate", local_web_candidate_payload),
        ("approved_packet_ready_fooddb_artifact", approved_fooddb_artifact),
        ("product_loop_handoff", product_loop_handoff),
    ]
    return {
        "artifact_type": "accurate_intake_local_web_self_use_candidate_v2_refresh_chain",
        "status": "pass" if candidate_prepared and route_backed_macro_checked else "blocked",
        "artifacts_dir": str(artifacts_dir),
        "refreshed_artifacts": {
            group_id: str(_artifact_path(artifacts_dir, filename))
            for group_id, filename in REFRESHED_ARTIFACT_FILENAMES.items()
        },
        "closeout_navigation": _build_closeout_navigation(closeout_payloads),
        "route_backed_macro_checked": route_backed_macro_checked,
        "route_backed_macro_closeout_status": route_backed_macro_closeout.get("status"),
        "route_backed_macro_closeout": route_backed_macro_closeout,
        "route_backed_macro_blockers": list(route_backed_macro_closeout.get("blockers") or []),
        "browser_activation_status": browser_activation_evidence_gate.get("status"),
        "product_pages_self_use_flow_status": product_pages_self_use_flow_gate.get("status"),
        "appshell_browser_evidence_chain": appshell_browser_evidence_chain,
        "context_live_diagnostic_gate_status": context_live_diagnostic_gate.get("status"),
        "pre_live_evidence_status": pre_live_evidence.get("_evidence_metadata", {}).get("status"),
        "pre_live_selected_option": pre_live_decision_pack.get("selected_option"),
        "approved_fooddb_artifact_status": approved_fooddb_artifact.get("status"),
        "product_loop_handoff_status": product_loop_handoff.get("status"),
        "ready_for_fdb_integration_validation": product_loop_handoff.get("ready_for_fdb_integration")
        is True,
        "product_loop_handoff_blockers": list(product_loop_handoff.get("blockers") or []),
        "candidate_prepared": candidate_prepared,
        "candidate_blockers": list(candidate_payload.get("blockers") or []),
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "fooddb_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh canonical local artifacts for the PLCE pre-live local web self-use gate."
    )
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts",
        help="Directory containing canonical local artifact inputs and outputs.",
    )
    args = parser.parse_args(argv)

    summary = build_local_web_self_use_candidate_refresh_chain(
        artifacts_dir=Path(args.artifacts_dir)
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
