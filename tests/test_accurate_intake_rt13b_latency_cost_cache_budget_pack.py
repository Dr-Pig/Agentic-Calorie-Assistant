from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_accurate_intake_rt13b_latency_cost_cache_budget_pack as module  # noqa: E402


def _live_artifact(
    *,
    stage_id: str = "single_case_live_probe",
    latency_ms: int = 940,
    timeout_budget_ms: int = 180000,
    retry_policy_applied: bool = False,
    result_kind: str = "strict_pass_first_attempt",
    usage: dict[str, object] | None = None,
    estimated_cost_usd: float | None = 0.004,
) -> dict[str, object]:
    provider_trace: dict[str, object] = {
        "usage": usage
        or {
            "prompt_tokens": 1400,
            "completion_tokens": 120,
            "total_tokens": 1520,
            "prompt_tokens_details": {"cached_tokens": 1024},
        }
    }
    if estimated_cost_usd is not None:
        provider_trace["estimated_cost_usd"] = estimated_cost_usd
    return {
        "artifact_type": "accurate_intake_mvp_live_diagnostic",
        "provider_mode": "live",
        "live_invoked": True,
        "live_llm_invoked": True,
        "readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
        "mutation_rollout_approved": False,
        "runtime_web_activation_approved": False,
        "live_provider_used_as_truth": False,
        "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
        "provider_profile_model": "grok-4-fast",
        "stages": [
            {
                "stage_id": stage_id,
                "status": "pass",
                "attempt_count": 1,
                "latency_ms": latency_ms,
                "timeout_budget_ms": timeout_budget_ms,
                "retry_policy_applied": retry_policy_applied,
                "result_kind": result_kind,
                "case_ids": ["bubble_milk_tea_refinement"],
            }
        ],
        "provider_invocations": [
            {
                "stage": stage_id,
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "provider_profile_model": "grok-4-fast",
                "provider_trace": provider_trace,
            }
        ],
        "summary": {
            "case_count": 1,
            "strict_pass_count": 1,
            "repaired_pass_count": 0,
            "contract_fail_count": 0,
            "timeout_count": 0,
            "provider_timeout_count": 0,
        },
    }


def _rt1c_artifact() -> dict[str, object]:
    return {
        "target_manager_runtime_gate": "rt1c_cache_metrics_observability",
        "status": "pass",
    }


def _rt13_artifact() -> dict[str, object]:
    return {
        "target_manager_runtime_gate": "rt13_observability_pack",
        "status": "pass",
    }


def _rt12b_artifact() -> dict[str, object]:
    return {
        "target_manager_runtime_gate": "rt12b_live_trace_grading_extension",
        "status": "pass",
    }


def _build(**overrides: object) -> dict[str, object]:
    payloads: dict[str, object] = {
        "live_artifacts": [_live_artifact(), _live_artifact(stage_id="schema_contract_probe", latency_ms=410)],
        "rt1c_artifact": _rt1c_artifact(),
        "rt13_artifact": _rt13_artifact(),
        "rt12b_artifact": _rt12b_artifact(),
    }
    payloads.update(overrides)
    return module.build_rt13b_latency_cost_cache_budget_pack(**payloads)


def test_rt13b_budget_pack_passes_with_latency_cost_and_cache_visibility() -> None:
    artifact = _build()

    assert artifact["artifact_type"] == "accurate_intake_rt13b_latency_cost_cache_budget_pack"
    assert artifact["target_manager_runtime_gate"] == "rt13b_latency_cost_cache_budget_pack"
    assert artifact["status"] == "pass"
    assert artifact["pass_type"] == "runtime_backed"
    assert artifact["runtime_backed"] is True
    assert artifact["live_llm_invoked"] is True
    assert artifact["summary"] == {
        "source_artifact_count": 2,
        "stage_count": 2,
        "provider_invocation_count": 2,
        "total_latency_ms": 1350,
        "max_stage_latency_ms": 940,
        "timeout_stage_count": 0,
        "retry_dependent_stage_count": 0,
        "usage_record_count": 2,
        "total_tokens": 3040,
        "cached_prompt_tokens": 2048,
        "cache_reporting_call_count": 2,
        "cache_hit_call_count": 2,
        "reported_cost_usd": 0.008,
        "cost_budget_enforceable": True,
    }
    assert artifact["budget_policy"]["cost_truth_source"] == "provider_reported_artifact_fields_only"
    assert artifact["budget_policy"]["cache_hit_not_required_for_green"] is True
    assert artifact["non_claims"]["private_self_use_approved"] is False


def test_rt13b_blocks_live_artifacts_without_cache_metric_reporting() -> None:
    artifact = _build(
        live_artifacts=[
            _live_artifact(
                usage={
                    "prompt_tokens": 1400,
                    "completion_tokens": 120,
                    "total_tokens": 1520,
                }
            )
        ]
    )

    assert artifact["status"] == "fail"
    assert "prompt_cache_visibility.cache_reporting_not_observed" in artifact["blockers"]


def test_rt13b_blocks_retry_dependent_or_timeout_budget_evidence() -> None:
    artifact = _build(
        live_artifacts=[
            _live_artifact(retry_policy_applied=True, result_kind="pass_after_retry"),
            _live_artifact(stage_id="slow_stage", latency_ms=181000, timeout_budget_ms=180000),
        ]
    )

    assert artifact["status"] == "fail"
    assert "retry_timeout_budget.retry_dependent_stage_present" in artifact["blockers"]
    assert "latency_budget.stage_exceeded_timeout_budget:slow_stage" in artifact["blockers"]


def test_rt13b_blocks_missing_dependency_gate() -> None:
    bad_rt12b = _rt12b_artifact()
    bad_rt12b["status"] = "fail"

    artifact = _build(rt12b_artifact=bad_rt12b)

    assert artifact["status"] == "fail"
    assert "dependencies.rt12b_live_trace_grading_extension_not_pass" in artifact["blockers"]


def test_rt13b_cli_writes_artifact(tmp_path: Path) -> None:
    live_a = tmp_path / "live_a.json"
    live_b = tmp_path / "live_b.json"
    rt1c = tmp_path / "rt1c.json"
    rt13 = tmp_path / "rt13.json"
    rt12b = tmp_path / "rt12b.json"
    output_path = tmp_path / "rt13b.json"

    live_a.write_text(json.dumps(_live_artifact(), ensure_ascii=False), encoding="utf-8")
    live_b.write_text(
        json.dumps(_live_artifact(stage_id="schema_contract_probe", latency_ms=410), ensure_ascii=False),
        encoding="utf-8",
    )
    rt1c.write_text(json.dumps(_rt1c_artifact(), ensure_ascii=False), encoding="utf-8")
    rt13.write_text(json.dumps(_rt13_artifact(), ensure_ascii=False), encoding="utf-8")
    rt12b.write_text(json.dumps(_rt12b_artifact(), ensure_ascii=False), encoding="utf-8")

    rc = module.main(
        [
            "--live-artifact",
            str(live_a),
            "--live-artifact",
            str(live_b),
            "--rt1c-artifact",
            str(rt1c),
            "--rt13-artifact",
            str(rt13),
            "--rt12b-artifact",
            str(rt12b),
            "--output",
            str(output_path),
        ]
    )

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
