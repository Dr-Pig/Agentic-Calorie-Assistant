from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_quality_pack import (  # noqa: E402
    build_context_quality_pack_artifact,
)
from app.composition.accurate_intake_context_replay_pack import (  # noqa: E402
    build_context_replay_pack_artifact,
)
from app.composition.accurate_intake_context_review import (  # noqa: E402
    build_context_review_artifact,
)
from app.composition.accurate_intake_context_target_candidate_eval import (  # noqa: E402
    build_context_target_candidate_eval_artifact,
)
from app.composition.accurate_intake_context_window_diagnostic import (  # noqa: E402
    build_context_window_diagnostic_artifact,
)
from app.composition.accurate_intake_fake_provider_context_smoke import (  # noqa: E402
    build_fake_provider_context_smoke_artifact,
)

DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_context_quality_pack.json"


def _object_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _fixture_context_review() -> dict[str, object]:
    return build_context_review_artifact(
        traces=[
            {
                "request_id": "context-quality-fixture-trace",
                "context_policy_version": "manager_context_policy_v1",
                "loaded_context_summary": {
                    "pending_followup_present": True,
                    "pending_draft_present": True,
                    "target_candidate_count": 2,
                },
                "omitted_context_summary": {
                    "policy_excluded_context_ids": [
                        "raw_trace_dump",
                        "long_term_memory",
                        "proactive_context",
                        "rescue_context",
                    ]
                },
                "manager_context_packet_v1": {
                    "hard_pins": {
                        "pending_followup": {"is_open": True},
                        "pending_draft": {"draft_id": "fixture-draft"},
                    },
                    "target_candidates": {
                        "for_correction_or_removal": [
                            {"meal_item_id": 1, "display_name": "tofu"},
                            {"meal_item_id": 2, "display_name": "rice"},
                        ]
                    },
                },
            }
        ]
    )


def _read_json_artifact(path: Path) -> dict[str, object]:
    return _object_dict(json.loads(path.read_text(encoding="utf-8")))


def _trace_from_chat_history_message(message: dict[str, object], index: int) -> dict[str, object]:
    loaded_summary = _object_dict(message.get("loaded_context_summary"))
    target_candidate_count = _int_value(message.get("target_candidate_count"))
    hard_pins: dict[str, object] = {}
    if message.get("pending_followup_linkage_present") is True or message.get("pending_pins_present") is True:
        hard_pins["pending_followup"] = {"source": "chat_history_runtime_trace"}
    if loaded_summary.get("pending_draft_present") is True:
        hard_pins["pending_draft"] = {"source": "chat_history_runtime_trace"}
    return {
        "request_id": str(message.get("trace_id") or message.get("message_id") or f"chat-history-message-{index + 1}"),
        "context_policy_version": message.get("context_policy_version"),
        "loaded_context_summary": loaded_summary,
        "omitted_context_summary": _object_dict(message.get("omitted_context_summary")),
        "manager_context_packet_v1": {
            "hard_pins": hard_pins,
            "target_candidates": {
                "for_correction_or_removal": [
                    {"source": "chat_history_runtime_trace", "candidate_index": candidate_index}
                    for candidate_index in range(target_candidate_count)
                ]
            },
        },
    }


def _runtime_context_review_from_short_term_context_smoke(
    smoke: dict[str, object],
) -> tuple[dict[str, object], list[str]]:
    blockers: list[str] = []
    if smoke.get("status") != "pass":
        blockers.append("runtime_trace_input.short_term_context_smoke_not_pass")
    if smoke.get("browser_executed") is not True:
        blockers.append("runtime_trace_input.browser_not_executed")
    for flag in (
        "live_llm_invoked",
        "web_tavily_used",
        "fooddb_evidence_used",
        "real_fooddb_pass_claimed",
        "product_readiness_claimed",
        "private_self_use_approved",
    ):
        if smoke.get(flag) is True:
            blockers.append(f"runtime_trace_input.{flag}")

    browser = _object_dict(smoke.get("browser"))
    chat_history = _object_dict(browser.get("chat_history_payload") or smoke.get("chat_history_payload"))
    messages = [
        _object_dict(message)
        for message in _list_value(chat_history.get("messages"))
        if isinstance(message, dict)
    ]
    traces = [
        _trace_from_chat_history_message(message, index)
        for index, message in enumerate(messages)
    ]
    if not traces:
        blockers.append("runtime_trace_input.no_chat_history_context_messages")
    review = build_context_review_artifact(traces=traces)
    return review, blockers


def _with_runtime_trace_metadata(
    artifact: dict[str, object],
    *,
    runtime_context_review: dict[str, object] | None,
    runtime_trace_source_artifact: str,
    runtime_trace_input_used: bool,
    runtime_trace_blockers: list[str],
) -> dict[str, object]:
    updated = dict(artifact)
    blockers = list(_list_value(updated.get("blockers")))
    blockers.extend(runtime_trace_blockers)
    updated["blockers"] = blockers
    if blockers:
        updated["status"] = "fail"
    updated["runtime_trace_input_used"] = runtime_trace_input_used
    updated["runtime_trace_source_artifact"] = runtime_trace_source_artifact
    updated["context_review_source"] = (
        "product_pages_short_term_context_smoke" if runtime_trace_input_used else "fixture"
    )
    updated["runtime_trace_context_review"] = runtime_context_review or {}
    return updated


def build_context_quality_pack_report(
    *,
    short_term_context_smoke: dict[str, object] | None = None,
    require_runtime_trace_input: bool = False,
) -> dict[str, object]:
    runtime_context_review: dict[str, object] | None = None
    runtime_trace_blockers: list[str] = []
    runtime_trace_source_artifact = "not_available"
    runtime_trace_input_used = False
    if short_term_context_smoke is not None:
        runtime_trace_source_artifact = str(
            short_term_context_smoke.get("smoke_id") or "unknown_short_term_context_smoke"
        )
        runtime_context_review, runtime_trace_blockers = _runtime_context_review_from_short_term_context_smoke(
            short_term_context_smoke
        )
        runtime_trace_input_used = not runtime_trace_blockers
    if require_runtime_trace_input and not runtime_trace_input_used:
        runtime_trace_blockers.append("runtime_trace_input.required_missing")

    context_review = runtime_context_review if runtime_trace_input_used else _fixture_context_review()
    artifact = build_context_quality_pack_artifact(
        context_review=context_review,
        target_candidate_eval=build_context_target_candidate_eval_artifact(),
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=build_fake_provider_context_smoke_artifact(),
    )
    return _with_runtime_trace_metadata(
        artifact,
        runtime_context_review=runtime_context_review,
        runtime_trace_source_artifact=runtime_trace_source_artifact,
        runtime_trace_input_used=runtime_trace_input_used,
        runtime_trace_blockers=runtime_trace_blockers,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the PL+CE context quality diagnostic pack."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--short-term-context-smoke")
    parser.add_argument("--require-runtime-trace-input", action="store_true")
    args = parser.parse_args(argv)

    short_term_context_smoke = (
        _read_json_artifact(Path(args.short_term_context_smoke))
        if args.short_term_context_smoke
        else None
    )
    artifact = build_context_quality_pack_report(
        short_term_context_smoke=short_term_context_smoke,
        require_runtime_trace_input=args.require_runtime_trace_input,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "context_quality_diagnostic_pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
