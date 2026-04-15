from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.web.provider_runtime import primary_provider
from scripts.audit_io_guard import enforce_file_backed_audit_input, load_json_audit_fixture


PACK_PATH = ROOT / "docs" / "quality" / "benchmarks" / "semantic_routing" / "semantic_routing_founder_fit_pack_v1.json"
LOG_ROOT = ROOT / ".logs" / "semantic_routing_eval"
ALLOWED_TARGET_WORKFLOW_FAMILIES = ("rescue_proposal", "intake_followup", "new_topic")
ALLOWED_TARGET_OBJECT_TYPES = ("proposal_container", "meal_log", "none")

SYSTEM_PROMPT = """
You are evaluating semantic routing for a chat-first nutrition agent.

Return exactly one JSON object with keys:
- semantic_family
- target_workflow_family
- target_object_type
- target_object_id
- semantic_confidence
- workflow_effect
- reasoning_brief

Allowed semantic_family values:
- proposal_accept
- proposal_reject
- proposal_defer
- proposal_adjust_shorter
- proposal_adjust_longer
- proposal_explain_request
- proposal_general_inquiry
- followup_completion
- followup_refinement
- new_topic_or_new_workflow

Allowed target_workflow_family values:
- rescue_proposal
- intake_followup
- new_topic

Allowed target_object_type values:
- proposal_container
- meal_log
- none

Allowed workflow_effect values:
- accept_and_apply_current_proposal
- close_current_proposal
- defer_current_proposal
- mutate_current_proposal
- request_explanation
- remain_inquiry_only
- continue_followup_lane
- open_new_workflow
- ask_clarify_before_mutation

Rules:
- Judge the user's current utterance against the provided active state pack.
- Prefer the workflow or object the utterance should operate on right now.
- Do not invent retrieval or memory state not present in the state pack.
- Use the canonical target vocabulary exactly as written above.
- If the utterance operates on the active rescue proposal, target_workflow_family must be rescue_proposal.
- If the utterance continues a pending intake follow-up lane, target_workflow_family must be intake_followup.
- If the utterance opens a different topic instead, target_workflow_family must be new_topic and target_object_type must be none.
- For ask_followup_only lanes, prefer followup_completion when the user is supplying the missing answer.
- For estimate_with_followup lanes, prefer followup_refinement when the user is refining an existing estimate rather than opening a new meal.
- If the utterance only asks about the current proposal, prefer inquiry-only behavior.
- If the utterance clearly continues a pending intake follow-up, attach to that follow-up lane.
- If the utterance opens a different topic instead, return new_topic_or_new_workflow.
- If the state pack is genuinely insufficient to choose between active objects, keep the best tentative family but you may use ask_clarify_before_mutation.
""".strip()


class MockSemanticRoutingProvider:
    async def complete_with_trace(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        stage: str,
        max_tokens: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        utterance = str(user_payload.get("utterance") or "")
        state_pack = dict(user_payload.get("state_pack_summary") or {})
        raw_state_pack = dict(state_pack.get("raw_state_pack_summary") or state_pack)
        predicted = _mock_predict(utterance=utterance, state_pack=raw_state_pack)
        return predicted, {
            "stage": stage,
            "provider": "mock_semantic_routing",
            "model": "mock-semantic-routing",
            "raw_content": json.dumps(predicted, ensure_ascii=False),
            "parsed_object": predicted,
            "finish_reason": "stop",
            "completion_tokens": 0,
            "prompt_tokens": 0,
        }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run semantic routing founder-fit eval cases.")
    parser.add_argument("--case-id", default=None, help="Optional case id filter.")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock provider.")
    return parser


def _provider_ready() -> bool:
    return bool(primary_provider.readiness().get("configured"))


def _load_pack() -> dict[str, Any]:
    return load_json_audit_fixture(path=PACK_PATH, audit_name="semantic_routing_eval")


def _normalize_state_pack(state_pack: dict[str, Any]) -> dict[str, Any]:
    rescue = dict(state_pack.get("active_open_rescue_proposal") or {}) or None
    followup = dict(state_pack.get("pending_intake_followup") or {}) or None

    active_objects: list[dict[str, Any]] = []
    routing_notes: list[str] = []

    if rescue is not None:
        active_objects.append(
            {
                "workflow_family": "rescue_proposal",
                "object_type": "proposal_container",
                "object_id": rescue.get("proposal_container_id"),
                "proposal_status": rescue.get("proposal_status"),
                "supports_actions": [
                    "proposal_accept",
                    "proposal_reject",
                    "proposal_defer",
                    "proposal_adjust_shorter",
                    "proposal_adjust_longer",
                    "proposal_explain_request",
                    "proposal_general_inquiry",
                ],
            }
        )
        routing_notes.append(
            "If the utterance acts on the open rescue plan, use target_workflow_family=rescue_proposal and target_object_type=proposal_container."
        )

    if followup is not None:
        lane_family = str(followup.get("lane_family") or "")
        family_hint = "followup_completion" if lane_family == "ask_followup_only" else "followup_refinement"
        active_objects.append(
            {
                "workflow_family": "intake_followup",
                "object_type": "meal_log",
                "object_id": followup.get("meal_log_id"),
                "lane_family": lane_family,
                "family_hint": family_hint,
                "pending_question": followup.get("pending_question"),
            }
        )
        routing_notes.append(
            f"If the utterance answers the pending {lane_family or 'followup'} lane, use target_workflow_family=intake_followup and target_object_type=meal_log."
        )

    if rescue is not None and followup is not None:
        routing_notes.append(
            "When both rescue_proposal and intake_followup are active, attach only when the utterance clearly targets one object; otherwise prefer ask_clarify_before_mutation."
        )

    return {
        "active_objects": active_objects,
        "target_vocabulary": {
            "target_workflow_family": list(ALLOWED_TARGET_WORKFLOW_FAMILIES),
            "target_object_type": list(ALLOWED_TARGET_OBJECT_TYPES),
        },
        "routing_notes": routing_notes,
        "raw_state_pack_summary": state_pack,
    }


def _selected_cases(payload: dict[str, Any], *, case_id: str | None) -> list[dict[str, Any]]:
    cases = [dict(case) for case in payload.get("cases", [])]
    if case_id is None:
        return cases
    for case in cases:
        if str(case.get("case_id")) == case_id:
            return [case]
    raise SystemExit(f"Unknown case_id: {case_id}")


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _prediction(
    semantic_family: str,
    target_workflow_family: str,
    target_object_type: str,
    target_object_id: Any,
    semantic_confidence: str,
    workflow_effect: str,
    reasoning_brief: str,
) -> dict[str, Any]:
    return {
        "semantic_family": semantic_family,
        "target_workflow_family": target_workflow_family,
        "target_object_type": target_object_type,
        "target_object_id": target_object_id,
        "semantic_confidence": semantic_confidence,
        "workflow_effect": workflow_effect,
        "reasoning_brief": reasoning_brief,
    }


def _contains_any(text: str, *tokens: str) -> bool:
    return any(token in text for token in tokens)


def _mock_predict(*, utterance: str, state_pack: dict[str, Any]) -> dict[str, Any]:
    text = utterance.strip().lower()
    rescue = state_pack.get("active_open_rescue_proposal") or None
    followup = state_pack.get("pending_intake_followup") or None

    if rescue and followup and _contains_any(text, "先這樣吧", "再看看", "先這樣"):
        return _prediction(
            "proposal_general_inquiry",
            "rescue_proposal",
            "proposal_container",
            rescue.get("proposal_container_id"),
            "low",
            "ask_clarify_before_mutation",
            "multiple active objects and the utterance is ambiguous",
        )

    if rescue:
        proposal_id = rescue.get("proposal_container_id")
        if _contains_any(text, "每天大概要少多少", "每天要少多少", "如果照這個做", "會少多少"):
            return _prediction(
                "proposal_general_inquiry",
                "rescue_proposal",
                "proposal_container",
                proposal_id,
                "medium",
                "remain_inquiry_only",
                "asks about the current proposal without mutating it",
            )
        if _contains_any(text, "為什麼", "理由", "怎麼算", "為何", "why"):
            return _prediction(
                "proposal_explain_request",
                "rescue_proposal",
                "proposal_container",
                proposal_id,
                "high",
                "request_explanation",
                "explicit explanation request",
            )
        if _contains_any(text, "照這個", "就這個", "接受", "可以，就這樣", "好，就照這個"):
            return _prediction(
                "proposal_accept",
                "rescue_proposal",
                "proposal_container",
                proposal_id,
                "high",
                "accept_and_apply_current_proposal",
                "explicit acceptance",
            )
        if _contains_any(text, "不要這次", "先取消", "不要這個方案", "我不要", "照原本節奏"):
            return _prediction(
                "proposal_reject",
                "rescue_proposal",
                "proposal_container",
                proposal_id,
                "high",
                "close_current_proposal",
                "explicit rejection",
            )
        if _contains_any(text, "晚點再說", "晚點吧", "先放著", "之後再說", "現在沒空想這個"):
            return _prediction(
                "proposal_defer",
                "rescue_proposal",
                "proposal_container",
                proposal_id,
                "high",
                "defer_current_proposal",
                "explicit or soft defer",
            )
        if _contains_any(text, "拉長", "緩和", "不要那麼硬", "能不能拉長", "gentler"):
            return _prediction(
                "proposal_adjust_longer",
                "rescue_proposal",
                "proposal_container",
                proposal_id,
                "medium",
                "mutate_current_proposal",
                "request gentler or longer plan",
            )
        if _contains_any(text, "短一點", "積極一點", "更快", "再短", "shorter"):
            return _prediction(
                "proposal_adjust_shorter",
                "rescue_proposal",
                "proposal_container",
                proposal_id,
                "medium",
                "mutate_current_proposal",
                "request shorter or more aggressive plan",
            )
        return _prediction(
            "proposal_general_inquiry",
            "rescue_proposal",
            "proposal_container",
            proposal_id,
            "low",
            "remain_inquiry_only",
            "default rescue-bound inquiry",
        )

    if followup:
        meal_log_id = followup.get("meal_log_id")
        lane_family = str(followup.get("lane_family") or "")
        if lane_family == "ask_followup_only":
            return _prediction(
                "followup_completion",
                "intake_followup",
                "meal_log",
                meal_log_id,
                "medium",
                "continue_followup_lane",
                "pending ask-followup completion",
            )
        if lane_family == "estimate_with_followup" and _contains_any(text, "晚餐", "早餐", "午餐", "咖哩飯", "我又吃了"):
            return _prediction(
                "new_topic_or_new_workflow",
                "new_topic",
                "none",
                None,
                "medium",
                "open_new_workflow",
                "new meal or topic signal",
            )
        return _prediction(
            "followup_refinement",
            "intake_followup",
            "meal_log",
            meal_log_id,
            "medium",
            "continue_followup_lane",
            "pending estimate-followup refinement",
        )

    return _prediction(
        "new_topic_or_new_workflow",
        "new_topic",
        "none",
        None,
        "medium",
        "open_new_workflow",
        "no attachable active state",
    )


def _build_oracle(case: dict[str, Any], predicted: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "matched_semantic_family": predicted.get("semantic_family") == case.get("expected_semantic_family"),
        "matched_target_workflow_family": predicted.get("target_workflow_family") == case.get("expected_target_workflow_family"),
        "matched_target_object_type": predicted.get("target_object_type") == case.get("expected_target_object_type"),
        "matched_target_object_id": predicted.get("target_object_id") == case.get("expected_target_object_id"),
        "matched_workflow_effect": predicted.get("workflow_effect") == case.get("expected_workflow_effect"),
    }
    checks["passed"] = all(bool(value) for value in checks.values())
    return checks


def _mismatch_types(oracle: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    if not oracle.get("matched_semantic_family"):
        mismatches.append("semantic_family_mismatch")
    if not oracle.get("matched_target_workflow_family"):
        mismatches.append("target_workflow_family_mismatch")
    if not oracle.get("matched_target_object_type") or not oracle.get("matched_target_object_id"):
        mismatches.append("attachment_mismatch")
    if not oracle.get("matched_workflow_effect"):
        mismatches.append("workflow_effect_mismatch")
    return mismatches


def _case_triage(case: dict[str, Any], oracle: dict[str, Any]) -> dict[str, Any]:
    return {
        "semantic_failure_cluster": case.get("drift_cluster"),
        "routing_mismatch_types": _mismatch_types(oracle),
        "ambiguity_posture": case.get("expected_ambiguity_posture", "none"),
        "state_pack_sufficiency": case.get("state_pack_sufficiency_hint", "sufficient"),
        "provisional_hypothesis": case.get("provisional_hypothesis", "prompt_issue"),
    }


def _build_summary(results: list[dict[str, Any]], *, pack_id: str, provider_name: str) -> dict[str, Any]:
    passed = sum(1 for item in results if item["oracle"]["passed"])
    by_family: dict[str, dict[str, int]] = {}
    for item in results:
        family = str(item["expected"]["semantic_family"])
        bucket = by_family.setdefault(family, {"total": 0, "passed": 0, "failed": 0})
        bucket["total"] += 1
        if item["oracle"]["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
    return {
        "pack_id": pack_id,
        "provider": provider_name,
        "total_cases": len(results),
        "passed_cases": passed,
        "failed_cases": len(results) - passed,
        "by_semantic_family": by_family,
    }


def _build_drift_triage(results: list[dict[str, Any]], *, pack_id: str, provider_name: str) -> dict[str, Any]:
    failed_results = [item for item in results if not item["oracle"]["passed"]]
    clusters: dict[str, dict[str, Any]] = {}

    for item in failed_results:
        cluster_name = str(item["triage"]["semantic_failure_cluster"] or "unclassified")
        cluster = clusters.setdefault(
            cluster_name,
            {
                "semantic_failure_cluster": cluster_name,
                "failed_case_ids": [],
                "observed_failure_patterns": [],
                "expected_semantic_families": set(),
                "expected_target_attachments": set(),
                "provisional_hypotheses": Counter(),
                "routing_mismatch_types": Counter(),
                "ambiguity_postures": Counter(),
                "state_pack_sufficiency": Counter(),
            },
        )
        cluster["failed_case_ids"].append(item["case_id"])
        cluster["observed_failure_patterns"].append(
            {
                "case_id": item["case_id"],
                "expected": item["expected"],
                "predicted": item["predicted"],
            }
        )
        cluster["expected_semantic_families"].add(item["expected"]["semantic_family"])
        cluster["expected_target_attachments"].add(
            f"{item['expected']['target_object_type']}:{item['expected']['target_object_id']}"
        )
        cluster["provisional_hypotheses"].update([item["triage"]["provisional_hypothesis"]])
        cluster["routing_mismatch_types"].update(item["triage"]["routing_mismatch_types"])
        cluster["ambiguity_postures"].update([item["triage"]["ambiguity_posture"]])
        cluster["state_pack_sufficiency"].update([item["triage"]["state_pack_sufficiency"]])

    serialized_clusters: list[dict[str, Any]] = []
    for cluster in clusters.values():
        serialized_clusters.append(
            {
                "semantic_failure_cluster": cluster["semantic_failure_cluster"],
                "failed_case_ids": cluster["failed_case_ids"],
                "observed_failure_patterns": cluster["observed_failure_patterns"],
                "expected_semantic_families": sorted(cluster["expected_semantic_families"]),
                "expected_target_attachments": sorted(cluster["expected_target_attachments"]),
                "provisional_hypotheses": dict(cluster["provisional_hypotheses"]),
                "routing_mismatch_types": dict(cluster["routing_mismatch_types"]),
                "ambiguity_postures": dict(cluster["ambiguity_postures"]),
                "state_pack_sufficiency": dict(cluster["state_pack_sufficiency"]),
            }
        )

    return {
        "pack_id": pack_id,
        "provider": provider_name,
        "total_failures": len(failed_results),
        "failure_clusters": sorted(serialized_clusters, key=lambda item: item["semantic_failure_cluster"]),
    }


async def _run_case(case: dict[str, Any], *, provider: Any) -> dict[str, Any]:
    normalized_state_pack = _normalize_state_pack(dict(case["state_pack_summary"]))
    parsed, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload={
            "utterance": case["utterance"],
            "state_pack_summary": normalized_state_pack,
        },
        stage="semantic_routing_eval",
        max_tokens=1000,
    )
    predicted = dict(parsed or {})
    oracle = _build_oracle(case, predicted)
    triage = _case_triage(case, oracle)
    return {
        "case_id": case["case_id"],
        "title": case["title"],
        "utterance": case["utterance"],
        "origin": case["origin"],
        "case_family": case["case_family"],
        "drift_cluster": case["drift_cluster"],
        "predicted": predicted,
        "expected": {
            "semantic_family": case.get("expected_semantic_family"),
            "target_workflow_family": case.get("expected_target_workflow_family"),
            "target_object_type": case.get("expected_target_object_type"),
            "target_object_id": case.get("expected_target_object_id"),
            "workflow_effect": case.get("expected_workflow_effect"),
        },
        "oracle": oracle,
        "triage": triage,
        "state_pack_summary": normalized_state_pack,
        "source_state_pack_summary": case["state_pack_summary"],
        "llm_trace": trace,
    }


async def _run_all(cases: list[dict[str, Any]], *, provider: Any, provider_name: str, pack_id: str) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for case in cases:
        results.append(await _run_case(case, provider=provider))
    triage = _build_drift_triage(results, pack_id=pack_id, provider_name=provider_name)
    return {
        "run_id": f"semantic_routing_eval_{_now_tag()}",
        "pack_id": pack_id,
        "provider": provider_name,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": _build_summary(results, pack_id=pack_id, provider_name=provider_name),
        "triage": triage,
        "cases": results,
    }


def main() -> int:
    enforce_file_backed_audit_input(audit_name="semantic_routing_eval")
    args = _parser().parse_args()
    pack = _load_pack()
    cases = _selected_cases(pack, case_id=args.case_id)

    if args.mock:
        provider = MockSemanticRoutingProvider()
        provider_name = "mock_semantic_routing"
    else:
        if not _provider_ready():
            print("provider_not_configured")
            return 2
        provider = primary_provider
        provider_name = str(primary_provider.readiness().get("provider") or "primary_provider")

    report = asyncio.run(_run_all(cases, provider=provider, provider_name=provider_name, pack_id=str(pack["pack_id"])))
    output_path = LOG_ROOT / f"{report['run_id']}.json"
    triage_path = LOG_ROOT / f"{report['run_id']}_triage.json"
    _save_json(output_path, report)
    _save_json(triage_path, report["triage"])
    print(output_path)
    print(triage_path)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
