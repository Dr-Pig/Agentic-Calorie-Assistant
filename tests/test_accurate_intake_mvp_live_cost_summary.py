from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_mvp_live_cost_summary import (
    build_accurate_intake_live_cost_summary,
    write_accurate_intake_live_cost_summary,
)


def _live_artifact(
    *,
    usage: dict[str, int] | None,
    estimated_cost_usd: float | None = None,
) -> dict[str, object]:
    provider_trace: dict[str, object] = {}
    if usage is not None:
        provider_trace["usage"] = usage
    if estimated_cost_usd is not None:
        provider_trace["estimated_cost_usd"] = estimated_cost_usd
    return {
        "artifact_type": "accurate_intake_mvp_live_diagnostic",
        "generated_at_utc": "2026-05-03T00:00:00Z",
        "claim_scope": "live_diagnostic",
        "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
        "provider_profile_model": "grok-4-fast",
        "readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
        "mutation_rollout_approved": False,
        "runtime_web_activation_approved": False,
        "live_provider_used_as_truth": False,
        "stages": [
            {
                "stage_id": "provider_health_smoke",
                "status": "pass",
                "latency_ms": 321,
                "result_kind": "strict_pass_first_attempt",
            }
        ],
        "provider_invocations": [
            {
                "stage": "provider_health_smoke",
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "provider_profile_model": "grok-4-fast",
                "provider_trace": provider_trace,
            }
        ],
    }


def test_live_cost_summary_totals_token_usage_and_reported_costs() -> None:
    summary = build_accurate_intake_live_cost_summary(
        [
            _live_artifact(
                usage={"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
                estimated_cost_usd=0.004,
            )
        ],
        source_paths=[Path("artifacts/run_a/provider_health.json")],
    )

    assert summary["artifact_type"] == "accurate_intake_mvp_live_cost_summary"
    assert summary["claim_scope"] == "live_diagnostic_cost_summary"
    assert summary["readiness_claimed"] is False
    assert summary["product_readiness_claimed"] is False
    assert summary["private_self_use_approved"] is False
    assert summary["production_selected"] is False
    assert summary["summary"] == {
        "source_artifact_count": 1,
        "stage_count": 1,
        "provider_invocation_count": 1,
        "usage_record_count": 1,
        "prompt_tokens": 12,
        "completion_tokens": 8,
        "total_tokens": 20,
        "reported_cost_record_count": 1,
        "reported_cost_usd": 0.004,
        "cost_unavailable_without_pricing": False,
    }
    assert summary["source_artifacts"][0]["sha256"]


def test_live_cost_summary_marks_cost_unavailable_when_tokens_have_no_pricing() -> None:
    summary = build_accurate_intake_live_cost_summary(
        [_live_artifact(usage={"input_tokens": 10, "output_tokens": 6, "total_tokens": 16})],
        source_paths=[Path("artifacts/run_b/schema_probe.json")],
    )

    assert summary["summary"]["usage_record_count"] == 1
    assert summary["summary"]["prompt_tokens"] == 10
    assert summary["summary"]["completion_tokens"] == 6
    assert summary["summary"]["total_tokens"] == 16
    assert summary["summary"]["reported_cost_record_count"] == 0
    assert summary["summary"]["reported_cost_usd"] is None
    assert summary["summary"]["cost_unavailable_without_pricing"] is True
    assert summary["cost_policy"] == {
        "billing_truth_source": "provider_reported_artifact_fields_only",
        "token_counts_are_not_billing_truth": True,
        "pricing_table_applied": False,
        "cost_unavailable_without_pricing": True,
    }


def test_live_cost_summary_writer_creates_run_specific_local_artifact(tmp_path: Path) -> None:
    source = tmp_path / "run_c" / "provider_health.json"
    source.parent.mkdir(parents=True)
    source.write_text(
        json.dumps(_live_artifact(usage={"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5})),
        encoding="utf-8",
    )
    output_path = tmp_path / "run_c" / "accurate_intake_mvp_live_cost_summary_run_c.json"

    output = write_accurate_intake_live_cost_summary(
        artifact_paths=[source],
        output_path=output_path,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output == output_path
    assert payload["artifact_type"] == "accurate_intake_mvp_live_cost_summary"
    assert payload["summary"]["total_tokens"] == 5
    assert payload["generated_artifact_policy"] == {
        "commit_as_repo_truth": False,
        "local_diagnostic_evidence_only": True,
    }
