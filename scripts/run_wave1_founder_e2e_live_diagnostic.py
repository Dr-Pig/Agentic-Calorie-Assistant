from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.contracts.readiness_claim import build_readiness_claim
from app.runtime.agent.founder_live_manager_contract import (
    FOUNDER_LIVE_MANAGER_SCHEMA_NAME,
    FOUNDER_LIVE_MANAGER_SCHEMA_VERSION,
    FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY,
    founder_live_manager_contract_constraints,
)


BASE_RUNNER = importlib.import_module("scripts.run_wave1_founder_e2e_deterministic_diagnostic")

ARTIFACT_PATH = ROOT / "artifacts" / "wave1_founder_e2e_live_diagnostic.json"
DEFAULT_DB_PATH = ROOT / "artifacts" / "wave1_founder_e2e_live_diagnostic.sqlite3"
DEFAULT_LOCAL_DATE = "2026-04-30"
DEFAULT_FOUNDER_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID = "builderspace-grok-4-fast-founder-live-contract"

_PROVIDER_PROFILES: dict[str, dict[str, Any]] = {
    DEFAULT_FOUNDER_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID: {
        "provider_profile_id": DEFAULT_FOUNDER_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID,
        "provider": "builderspace",
        "model": "grok-4-fast",
        "provider_profile_role": "founder_live_contract_diagnostic",
        "cost_tier": "low",
        "production_selected": False,
        "not_production_selection": True,
        "readiness_owner": False,
        "temperature": 0.0,
        "schema_name": FOUNDER_LIVE_MANAGER_SCHEMA_NAME,
        "schema_version": FOUNDER_LIVE_MANAGER_SCHEMA_VERSION,
        "transport_policy": {
            "primary": FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY,
            "fallback": "json_schema",
            "forbidden_as_success": ["plain_json_object_without_schema_validation"],
        },
    },
    "builderspace-grok-4-fast-founder-live-diagnostic": {
        "provider_profile_id": "builderspace-grok-4-fast-founder-live-diagnostic",
        "provider": "builderspace",
        "model": "grok-4-fast",
        "provider_profile_role": "founder_live_diagnostic_primary_legacy_alias",
        "cost_tier": "low",
        "production_selected": False,
        "not_production_selection": True,
        "readiness_owner": False,
        "temperature": 0.0,
        "schema_name": FOUNDER_LIVE_MANAGER_SCHEMA_NAME,
        "schema_version": FOUNDER_LIVE_MANAGER_SCHEMA_VERSION,
        "transport_policy": {
            "primary": FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY,
            "fallback": "json_schema",
            "forbidden_as_success": ["plain_json_object_without_schema_validation"],
        },
    },
}

_FORBIDDEN_CLAIMS = [
    "product_ready",
    "live_ready",
    "user_facing_ready",
    "mutation_ready",
    "production_ready",
    "runtime_web_activation_ready",
]


class FounderLiveDiagnosticProvider:
    """Profile wrapper that adds diagnostic trace metadata without changing provider behavior."""

    def __init__(self, provider: Any, *, profile: dict[str, Any], live_invoked: bool) -> None:
        self._provider = provider
        self.profile = dict(profile)
        self.live_invoked = live_invoked
        self.invocations: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        readiness = self._provider.readiness() if hasattr(self._provider, "readiness") else {}
        return {
            **(readiness if isinstance(readiness, dict) else {}),
            "provider_profile_id": self.profile["provider_profile_id"],
            "provider_profile_model": self.profile["model"],
            "provider_profile_role": self.profile["provider_profile_role"],
            "production_selected": False,
            "not_production_selection": True,
            "readiness_owner": False,
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        stage = str(kwargs.get("stage") or "")
        kwargs = _with_founder_live_contract_constraints(kwargs, profile=self.profile)
        try:
            payload, trace = await self._provider.complete_with_trace(**kwargs)
        except Exception as exc:
            error_trace = _provider_error_trace(exc, stage=stage, profile=self.profile)
            self.invocations.append(error_trace)
            raise
        enriched_trace = {
            **_dict(trace),
            "provider_profile_id": self.profile["provider_profile_id"],
            "provider_profile_model": self.profile["model"],
            "provider_profile_role": self.profile["provider_profile_role"],
            "transport_policy": self.profile["transport_policy"],
            "schema_name": self.profile["schema_name"],
            "schema_version": self.profile["schema_version"],
            "production_selected": False,
            "not_production_selection": True,
            "live_llm_invoked": self.live_invoked,
        }
        self.invocations.append(
            {
                "stage": stage,
                "provider_profile_id": self.profile["provider_profile_id"],
                "provider_profile_model": self.profile["model"],
                "provider_profile_role": self.profile["provider_profile_role"],
                "transport_policy": self.profile["transport_policy"],
                "schema_name": self.profile["schema_name"],
                "schema_version": self.profile["schema_version"],
                "live_llm_invoked": self.live_invoked,
                "failure_family": None,
                "provider_trace": enriched_trace,
            }
        )
        return payload, enriched_trace


def provider_profile(provider_profile_id: str) -> dict[str, Any]:
    if provider_profile_id not in _PROVIDER_PROFILES:
        supported = ", ".join(sorted(_PROVIDER_PROFILES))
        raise ValueError(f"Unsupported Founder live diagnostic provider profile: {provider_profile_id}. Supported: {supported}")
    return dict(_PROVIDER_PROFILES[provider_profile_id])


def build_missing_provider_report(*, profile: dict[str, Any]) -> dict[str, Any]:
    return _report_shell(
        profile=profile,
        provider_mode="not_invoked",
        live_invoked=False,
        provider_readiness={
            "provider": profile["provider"],
            "configured": False,
            "provider_profile_id": profile["provider_profile_id"],
            "provider_profile_model": profile["model"],
        },
        provider_invocations=[],
        legacy_guard=BASE_RUNNER.build_legacy_guard(),
        cases=[],
        failure_layer="provider_runtime_error",
        failure_family="missing_provider_token",
    )


def run_diagnostic(
    *,
    output_path: Path = ARTIFACT_PATH,
    db_path: Path = DEFAULT_DB_PATH,
    local_date: str = DEFAULT_LOCAL_DATE,
    provider_profile_id: str = DEFAULT_FOUNDER_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID,
    provider_timeout_ms: int = 180000,
    provider_override: Any | None = None,
    provider_mode: str = "live",
    live_invoked: bool = True,
) -> dict[str, Any]:
    profile = provider_profile(provider_profile_id)
    if provider_override is None:
        provider_override = _build_builderspace_provider(profile=profile, provider_timeout_ms=provider_timeout_ms)
    provider = FounderLiveDiagnosticProvider(provider_override, profile=profile, live_invoked=live_invoked)
    readiness = provider.readiness()
    if provider_mode == "live" and not readiness.get("configured"):
        report = build_missing_provider_report(profile=profile)
        _write_report(output_path, report)
        return report

    database = BASE_RUNNER._configure_database(db_path)  # noqa: SLF001 - diagnostic runner reuses active harness setup.
    db = database.SessionLocal()
    try:
        legacy_guard = BASE_RUNNER.build_legacy_guard()
        cases = asyncio.run(BASE_RUNNER._run_cases(db, provider, local_date=local_date))  # noqa: SLF001
        cases = [_decorate_case(case, profile=profile) for case in cases]
        if legacy_guard["legacy_dependency_detected"]:
            for case in cases:
                case["verdict"] = "fail"
                case["failure_layer"] = "legacy_dependency"
                case["failure_family"] = "legacy_dependency"
        report = _report_shell(
            profile=profile,
            provider_mode=provider_mode,
            live_invoked=live_invoked,
            provider_readiness=readiness,
            provider_invocations=provider.invocations,
            legacy_guard=legacy_guard,
            cases=cases,
            failure_layer=None,
            failure_family=None,
        )
        _write_report(output_path, report)
        return report
    finally:
        db.close()
        engine = getattr(database, "engine", None)
        if engine is not None:
            engine.dispose()


def _build_builderspace_provider(*, profile: dict[str, Any], provider_timeout_ms: int) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    timeout_seconds = max(1, int(provider_timeout_ms / 1000))
    previous_timeout = os.environ.get("AI_BUILDER_TIMEOUT_SECONDS")
    os.environ["AI_BUILDER_TIMEOUT_SECONDS"] = str(timeout_seconds)
    try:
        return BuilderSpaceAdapter(manager_model_override=str(profile["model"]), role_label="founder_live_diagnostic")
    finally:
        if previous_timeout is None:
            os.environ.pop("AI_BUILDER_TIMEOUT_SECONDS", None)
        else:
            os.environ["AI_BUILDER_TIMEOUT_SECONDS"] = previous_timeout


def _report_shell(
    *,
    profile: dict[str, Any],
    provider_mode: str,
    live_invoked: bool,
    provider_readiness: dict[str, Any],
    provider_invocations: list[dict[str, Any]],
    legacy_guard: dict[str, Any],
    cases: list[dict[str, Any]],
    failure_layer: str | None,
    failure_family: str | None,
) -> dict[str, Any]:
    return _json_safe(
        {
            "artifact_type": "wave1_founder_e2e_live_diagnostic",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "current_mainline": "Wave 1 Founder live diagnostic re-entry",
            "provider_mode": provider_mode,
            "live_invoked": live_invoked,
            "live_llm_invoked": live_invoked,
            "provider_profile_id": profile["provider_profile_id"],
            "provider_profile_model": profile["model"],
            "provider_profile_role": profile["provider_profile_role"],
            "transport_policy": profile["transport_policy"],
            "schema_name": profile["schema_name"],
            "schema_version": profile["schema_version"],
            "provider_readiness": provider_readiness,
            "provider_invocations": provider_invocations,
            "production_selected": False,
            "not_production_selection": True,
            "readiness_claimed": False,
            "readiness_claim": _readiness_claim(
                provider_mode=provider_mode,
                live_invoked=live_invoked,
            ),
            "active_entrypoint": BASE_RUNNER.ACTIVE_ENTRYPOINT,
            "active_entrypoint_verified": bool(legacy_guard.get("active_entrypoint_verified")),
            "legacy_guard": legacy_guard,
            "user_facing_enabled": False,
            "mutation_enabled": False,
            "runtime_web_activation_approved": False,
            "runtime_web_activation_recommended": False,
            "tavily_or_web_activated": False,
            "allow_search": False,
            "failure_layer": failure_layer,
            "failure_family": failure_family,
            "cases": cases,
            "summary": _summary(cases),
        }
    )


def _readiness_claim(*, provider_mode: str, live_invoked: bool) -> dict[str, Any]:
    fake_contract_test = provider_mode != "live" or not live_invoked
    return build_readiness_claim(
        claim_scope="unit_contract" if fake_contract_test else "live_diagnostic",
        activation_stage="contract" if fake_contract_test else "live_diagnostic",
        semantic_authority_source="fake_manager_structured_output" if fake_contract_test else "live_manager_structured_output",
        producer_honesty={
            "runner_inferred_semantics": False,
            "fake_provider_simulated_manager": fake_contract_test,
            "final_mapping_fabricated": False,
            "mutation_fabricated": False,
        },
        evidence_lineage={
            "artifacts": [],
            "producers": ["scripts/run_wave1_founder_e2e_live_diagnostic.py"],
            "active_entrypoint": BASE_RUNNER.ACTIVE_ENTRYPOINT,
            "live_invoked": live_invoked,
            "legacy_oracle_used": False,
        },
        allowed_next_stage=None,
        forbidden_claims=_FORBIDDEN_CLAIMS,
        readiness_claimed=False,
    )


def _decorate_case(case: dict[str, Any], *, profile: dict[str, Any]) -> dict[str, Any]:
    decorated = dict(case)
    failure_layer, failure_family = _classify_failure(decorated)
    decorated["provider_profile_id"] = profile["provider_profile_id"]
    decorated["provider_profile_model"] = profile["model"]
    decorated["provider_profile_role"] = profile["provider_profile_role"]
    decorated["transport_policy"] = profile["transport_policy"]
    decorated["schema_name"] = profile["schema_name"]
    decorated["schema_version"] = profile["schema_version"]
    decorated["case_contract_status"] = _case_contract_status(decorated)
    decorated["readiness_claimed"] = False
    decorated["production_selected"] = False
    decorated["failure_family"] = failure_family
    if failure_layer is not None:
        decorated["failure_layer"] = failure_layer
    return decorated


def _with_founder_live_contract_constraints(kwargs: dict[str, Any], *, profile: dict[str, Any]) -> dict[str, Any]:
    updated = dict(kwargs)
    user_payload = dict(_dict(updated.get("user_payload")))
    constraints = dict(_dict(user_payload.get("constraints")))
    constraints.update(founder_live_manager_contract_constraints(str(profile["provider_profile_id"])))
    user_payload["constraints"] = constraints
    updated["user_payload"] = user_payload
    return updated


def _case_contract_status(case: dict[str, Any]) -> str:
    actual = _dict(case.get("actual_behavior"))
    runtime_error = _dict(actual.get("runtime_error"))
    if runtime_error:
        return "fail"
    for trace in _case_manager_traces(case):
        if trace.get("repair_attempted") is True or str(trace.get("repair_result") or "") == "passed_after_repair":
            return "repaired_pass"
    if _dict(actual.get("manager_semantic_decision")) or actual.get("manager_intent"):
        return "strict_pass"
    if case.get("verdict") != "pass":
        return "fail"
    return "strict_pass"


def _case_manager_traces(case: dict[str, Any]) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    actual = _dict(case.get("actual_behavior"))
    for round_item in actual.get("manager_rounds") or []:
        if isinstance(round_item, dict):
            traces.append(_dict(round_item.get("trace")))
    trace = _dict(actual.get("manager_trace"))
    if trace:
        traces.append(trace)
    return traces


def _summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    summary = dict(BASE_RUNNER._summary(cases))  # noqa: SLF001
    statuses = [str(case.get("case_contract_status") or "fail") for case in cases]
    summary["strict_pass_count"] = statuses.count("strict_pass")
    summary["repaired_pass_count"] = statuses.count("repaired_pass")
    summary["contract_fail_count"] = statuses.count("fail")
    summary["shadow_or_canary_unlock_allowed"] = False
    return summary


def _classify_failure(case: dict[str, Any]) -> tuple[str | None, str | None]:
    if case.get("verdict") in {"pass", "deferred"}:
        return case.get("failure_layer"), None
    runtime_error = _dict(_dict(case.get("actual_behavior")).get("runtime_error"))
    if runtime_error:
        error_type = str(runtime_error.get("type") or "")
        message = str(runtime_error.get("message") or "")
        if "missing required fields" in message or "validate_manager_payload" in message:
            return "provider_contract_non_adherence", "provider_contract_non_adherence"
        if "did not return JSON" in message or "JSON" in message and "must" in message:
            return "schema_parse_failure", "schema_parse_failure"
        if error_type in {"ConnectError", "ReadTimeout", "TimeoutException", "RuntimeError"}:
            return "provider_runtime_error", "provider_runtime_error"
        if error_type == "BuilderSpaceResponseError":
            return "provider_contract_non_adherence", "provider_contract_non_adherence"
        return "provider_contract_non_adherence", "provider_contract_non_adherence"
    existing = case.get("failure_layer")
    if existing:
        return str(existing), str(existing)
    return "unknown", "unknown"


def _provider_error_trace(exc: Exception, *, stage: str, profile: dict[str, Any]) -> dict[str, Any]:
    trace = _dict(getattr(exc, "trace", {}))
    return {
        "stage": stage,
        "provider_profile_id": profile["provider_profile_id"],
        "provider_profile_model": profile["model"],
        "provider_profile_role": profile["provider_profile_role"],
        "live_llm_invoked": True,
        "failure_family": "provider_runtime_error",
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "provider_trace": trace,
    }


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _load_local_env(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=False, encoding="utf-8-sig")
        return
    except ModuleNotFoundError:
        pass
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> int:
    _load_local_env(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Run Wave 1 Founder E2E live diagnostic.")
    parser.add_argument("--output", default=str(ARTIFACT_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--local-date", default=DEFAULT_LOCAL_DATE)
    parser.add_argument("--provider-profile-id", default=DEFAULT_FOUNDER_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)
    parser.add_argument("--provider-timeout-ms", type=int, default=180000)
    args = parser.parse_args()

    report = run_diagnostic(
        output_path=Path(args.output),
        db_path=Path(args.db_path),
        local_date=str(args.local_date),
        provider_profile_id=str(args.provider_profile_id),
        provider_timeout_ms=int(args.provider_timeout_ms),
    )
    print(
        json.dumps(
            {
                "artifact": str(Path(args.output)),
                "provider_mode": report.get("provider_mode"),
                "live_invoked": report.get("live_invoked"),
                "provider_profile_model": report.get("provider_profile_model"),
                "summary": report.get("summary"),
                "readiness_claimed": report.get("readiness_claimed"),
                "failure_layer": report.get("failure_layer"),
                "failure_family": report.get("failure_family"),
            },
            ensure_ascii=False,
        )
    )
    return 0


__all__ = [
    "DEFAULT_FOUNDER_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID",
    "FounderLiveDiagnosticProvider",
    "build_missing_provider_report",
    "provider_profile",
    "run_diagnostic",
]


if __name__ == "__main__":
    raise SystemExit(main())
