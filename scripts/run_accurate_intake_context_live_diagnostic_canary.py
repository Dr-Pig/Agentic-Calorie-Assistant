from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_live_diagnostic_canary import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID,
    build_context_live_diagnostic_canary_report,
    build_missing_token_report,
    build_provider_request_payload,
    provider_profile,
)
from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (  # noqa: E402
    REQUIRED_CASE_IDS,
)
from app.composition.accurate_intake_context_live_provider_input_preflight import (  # noqa: E402
    build_context_live_provider_input_preflight_artifact,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_context_live_diagnostic_canary.json"


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return dict(payload) if isinstance(payload, dict) else {"artifact_type": "invalid_json_shape"}


def select_context_live_provider_inputs(
    preflight: dict[str, Any],
    *,
    case_id: str,
    all_cases: bool,
) -> dict[str, Any]:
    if all_cases:
        return dict(preflight)
    if case_id not in REQUIRED_CASE_IDS:
        supported = ", ".join(REQUIRED_CASE_IDS)
        raise ValueError(f"Unsupported context live diagnostic case_id={case_id}. Supported: {supported}")
    provider_inputs = [_dict(row) for row in _list(preflight.get("provider_inputs"))]
    selected = [row for row in provider_inputs if row.get("case_id") == case_id]
    if len(selected) != 1:
        raise ValueError(f"Provider input preflight missing exactly one row for case_id={case_id}")
    narrowed = dict(preflight)
    narrowed["provider_inputs"] = selected
    narrowed["selected_case_id"] = case_id
    narrowed["full_matrix_live_probe"] = False
    return narrowed


def _extract_content(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return "{}"
    message = _dict(_dict(choices[0]).get("message"))
    content = message.get("content")
    return content if isinstance(content, str) else "{}"


def _redacted_excerpt(content: str, limit: int = 500) -> str:
    excerpt = content[:limit]
    for marker in ("Authorization", "Bearer", "AI_BUILDER_TOKEN"):
        excerpt = excerpt.replace(marker, "[redacted]")
    return excerpt


def _parse_provider_json(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    content = _extract_content(data)
    trace: dict[str, Any] = {
        "raw_provider_output_excerpt": _redacted_excerpt(content),
        "schema_status": "fail",
        "parse_error": None,
    }
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        trace["parse_error"] = str(exc)
        return {}, trace
    if not isinstance(parsed, dict):
        trace["parse_error"] = "provider_output_not_object"
        return {}, trace
    trace["schema_status"] = "json_object"
    trace["raw_top_level_keys"] = sorted(str(key) for key in parsed)
    return parsed, trace


async def run_context_live_diagnostic_canary(
    *,
    context_live_provider_input_preflight: dict[str, Any],
    token: str,
    provider_profile_id: str = DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID,
    base_url: str = DEFAULT_BASE_URL,
    timeout_seconds: int = 60,
    async_client_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    if async_client_factory is None:
        import httpx

        async_client_factory = httpx.AsyncClient
    profile = provider_profile(provider_profile_id)
    provider_outputs: list[dict[str, Any]] = []
    provider_traces: list[dict[str, Any]] = []
    async with async_client_factory(timeout=timeout_seconds) as client:
        for provider_input in _list(context_live_provider_input_preflight.get("provider_inputs")):
            row = _dict(provider_input)
            request_payload = build_provider_request_payload(row)
            started = time.perf_counter()
            response = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "model": profile["model"],
                    "temperature": profile["temperature"],
                    "max_tokens": profile["max_tokens"],
                    "response_format": {"type": profile["schema_mode"]},
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a context-only Accurate Intake Manager diagnostic. "
                                "Return only JSON matching the provided response_schema. "
                                "Use the manager_context_sidecar to choose manager_intent and workflow_effect. "
                                "target_resolution is only for resolving prior meal/item correction or removal "
                                "references; do not put daily calorie targets, kcal values, or new food identities "
                                "in target_resolution.candidate_ids. "
                                "Do not use FoodDB, WebSearch, tools, frontend inference, or mutation. "
                                "Preserve ambiguity when the sidecar says ambiguity_expected=true."
                            ),
                        },
                        {"role": "user", "content": json.dumps(request_payload, ensure_ascii=False)},
                    ],
                },
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            response.raise_for_status()
            data = response.json()
            parsed, parse_trace = _parse_provider_json(data)
            provider_outputs.append(parsed)
            provider_traces.append(
                {
                    "case_id": row.get("case_id"),
                    "provider": "builderspace",
                    "model": profile["model"],
                    "provider_profile_id": profile["provider_profile_id"],
                    "provider_profile_role": profile["provider_profile_role"],
                    "latency_ms": latency_ms,
                    "usage": _dict(data.get("usage")),
                    "response_status": getattr(response, "status_code", None),
                    **parse_trace,
                }
            )
    return build_context_live_diagnostic_canary_report(
        context_live_provider_input_preflight=context_live_provider_input_preflight,
        provider_outputs=provider_outputs,
        provider_traces=provider_traces,
        provider_profile_id=provider_profile_id,
        live_invoked=True,
    )


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


def main(argv: list[str] | None = None) -> int:
    _load_local_env(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Run the PL+CE context-only live diagnostic canary with GrokFast when configured."
    )
    parser.add_argument("--provider-input-preflight-json")
    parser.add_argument("--provider-profile-id", default=DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID)
    parser.add_argument("--base-url", default=os.getenv("AI_BUILDER_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--case-id", default=REQUIRED_CASE_IDS[0])
    parser.add_argument("--all-cases", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    preflight = (
        _read_json(Path(args.provider_input_preflight_json))
        if args.provider_input_preflight_json
        else build_context_live_provider_input_preflight_artifact()
    )
    preflight = select_context_live_provider_inputs(
        _dict(preflight),
        case_id=str(args.case_id),
        all_cases=bool(args.all_cases),
    )
    token = os.getenv("AI_BUILDER_TOKEN", "").strip()
    if not token:
        report = build_missing_token_report(
            context_live_provider_input_preflight=preflight,
            provider_profile_id=str(args.provider_profile_id),
        )
    else:
        report = asyncio.run(
            run_context_live_diagnostic_canary(
                context_live_provider_input_preflight=_dict(preflight),
                token=token,
                provider_profile_id=str(args.provider_profile_id),
                base_url=str(args.base_url),
                timeout_seconds=int(args.timeout_seconds),
            )
        )
    write_json_artifact(Path(args.output), report)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "status": report.get("status"),
                "provider_mode": report.get("provider_mode"),
                "live_invoked": report.get("live_invoked"),
                "provider_profile_model": report.get("provider_profile_model"),
                "failure_family": report.get("failure_family"),
                "readiness_claimed": report.get("readiness_claimed"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report.get("status") in {"live_diagnostic_pass", "not_invoked"} else 1


__all__ = [
    "run_context_live_diagnostic_canary",
    "select_context_live_provider_inputs",
]


if __name__ == "__main__":
    raise SystemExit(main())
