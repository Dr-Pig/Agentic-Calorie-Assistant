from __future__ import annotations

from collections.abc import Iterable
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runtime.infrastructure.trace.trace_triage import build_live_trace_triage
from .paths import RUNTIME_LOG_DIR, ensure_runtime_dirs
from .schemas import AuditEvent


ensure_runtime_dirs()

LOG_DIR = RUNTIME_LOG_DIR
LOG_FILE = LOG_DIR / "text_meal_events.jsonl"
REQUEST_TRACE_DIR = LOG_DIR / "requests"


def append_audit_event(event: AuditEvent) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(event.model_dump_json(ensure_ascii=False) + "\n")


def write_request_trace_artifact(request_id: str, payload: dict) -> Path:
    REQUEST_TRACE_DIR.mkdir(parents=True, exist_ok=True)
    path = REQUEST_TRACE_DIR / f"{request_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_recent_events(limit: int = 20) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    records: list[dict] = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(records))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_tokens(data: dict[str, Any]) -> int:
    """Robustly extract total tokens from a trace data object."""
    # 1. Direct field in token_usage dict
    token_usage = data.get("token_usage", {}) or {}
    if token_usage.get("total_tokens"):
        return int(token_usage["total_tokens"])
    
    # 2. Aggregation from llm_traces
    traces = data.get("llm_traces", []) or []
    total = 0
    for t in traces:
        # Some providers put it in 'usage', some directly
        usage = t.get("usage")
        if isinstance(usage, dict):
            total += usage.get("total_tokens") or usage.get("total_token") or 0
        else:
            total += t.get("total_tokens") or 0
    return total


def get_trace_summaries(limit: int = 100) -> dict[str, Any]:
    """Scan all request traces for global stats and return metadata summaries for the sidebar."""
    if not REQUEST_TRACE_DIR.exists():
        return {"traces": [], "stats": {"total": 0, "win_rate": 0, "avg_tokens": 0}}
    
    all_summaries: list[dict] = []
    files = sorted(REQUEST_TRACE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    total_tokens_all = 0
    total_wins = 0
    valid_count = 0
    
    for path in files:
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            
            # Metadata extraction
            req_data = data.get("request", {}) or {}
            mt_context = data.get("multi_turn_context", {}) or {}
            manager_decision = data.get("manager_decision", {}) or {}
            semantic_decision = (
                data.get("semantic_decision")
                or manager_decision.get("semantic_decision")
                or {}
            )
            eval_data = data.get("north_star_evaluation", {}) or {}
            diagnosis = data.get("diagnosis", {}) or {}
            trace_contract = data.get("trace_contract", {}) or {}
            trace_meta = data.get("trace_meta", {}) or {}
            triage = data.get("live_trace_triage")
            if not isinstance(triage, dict):
                triage = build_live_trace_triage(data)
            
            # Map verdict correctly (win_loss_neutral is the source of truth)
            verdict = eval_data.get("win_loss_neutral") or eval_data.get("verdict")
            if not verdict:
                verdict = "error" if data.get("status") == "error" or data.get("error") else "pending"
            
            tokens = _extract_tokens(data)
            
            # Global Stats aggregation
            if verdict != "error":
                valid_count += 1
                total_tokens_all += tokens
                if verdict in ["win", "WIN"]:
                    total_wins += 1
            
            # Sidebar summary (only for the first N records)
            if len(all_summaries) < limit:
                all_summaries.append({
                    "id": path.stem,
                    "timestamp": trace_meta.get("timestamp") or data.get("timestamp") or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                    "intent": mt_context.get("turn_intent") or semantic_decision.get("current_turn_intent") or manager_decision.get("intent_type") or "unknown",
                    "verdict": verdict,
                    "tokens": tokens,
                    "user_id": trace_meta.get("user_id") or req_data.get("user_id") or "anonymous",
                    "text": req_data.get("text") or "",
                    "is_multi_turn": mt_context.get("is_multi_turn") or False,
                    "failed_layer": diagnosis.get("failed_layer"),
                    "repairability": diagnosis.get("repairability", "unknown"),
                    "trace_health": diagnosis.get("trace_health", "healthy"),
                    "manager_mode": (trace_contract.get("manager_output") or {}).get("manager_mode"),
                    "best_answer_source": trace_contract.get("best_answer_source"),
                    "retry_triggered": trace_contract.get("retry_triggered", False),
                    "request_failure_family": triage.get("request_failure_family"),
                    "root_cause_bucket": triage.get("suspected_root_cause_bucket"),
                })
        except (json.JSONDecodeError, OSError):
            continue
            
    stats = {
        "total": len(files),
        "win_rate": round((total_wins / valid_count * 100), 1) if valid_count > 0 else 0,
        "avg_tokens": round(total_tokens_all / valid_count) if valid_count > 0 else 0
    }
    
    return {"traces": all_summaries, "stats": stats}


def get_full_trace(request_id: str) -> dict | None:
    """Read a specific full trace file by request ID."""
    path = REQUEST_TRACE_DIR / f"{request_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data.get("live_trace_triage"), dict):
            data["live_trace_triage"] = build_live_trace_triage(data)
        return data
    except (json.JSONDecodeError, OSError):
        return None


def find_latest_trace_for_user_date(*, user_id: str, local_date: str, bundle: str | None = None) -> dict | None:
    """Return the newest request trace artifact for the given user/date pair."""
    if bundle is not None:
        return find_latest_traces_for_user_date(
            user_id=user_id,
            local_date=local_date,
            bundles=(bundle,),
        ).get(bundle)
    if not REQUEST_TRACE_DIR.exists():
        return None
    files = sorted(REQUEST_TRACE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        trace_meta = data.get("trace_meta", {}) or {}
        request = data.get("request", {}) or {}
        if str(trace_meta.get("user_id") or request.get("user_id") or "") != user_id:
            continue
        if str(trace_meta.get("local_date") or request.get("local_date") or "") != local_date:
            continue
        if bundle is not None and str(trace_meta.get("bundle") or "") != bundle:
            continue
        if not isinstance(data.get("live_trace_triage"), dict):
            data["live_trace_triage"] = build_live_trace_triage(data)
        return data
    return None


def find_latest_traces_for_user_date(
    *,
    user_id: str,
    local_date: str,
    bundles: Iterable[str],
) -> dict[str, dict | None]:
    """Return newest request trace artifacts for several bundles in a single artifact scan."""
    bundle_order = tuple(str(bundle) for bundle in bundles)
    wanted = set(bundle_order)
    found: dict[str, dict] = {}
    if not wanted or not REQUEST_TRACE_DIR.exists():
        return {bundle: None for bundle in bundle_order}
    files = sorted(REQUEST_TRACE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        trace_meta = data.get("trace_meta", {}) or {}
        request = data.get("request", {}) or {}
        if str(trace_meta.get("user_id") or request.get("user_id") or "") != user_id:
            continue
        if str(trace_meta.get("local_date") or request.get("local_date") or "") != local_date:
            continue
        trace_bundle = str(trace_meta.get("bundle") or "")
        if trace_bundle not in wanted or trace_bundle in found:
            continue
        if not isinstance(data.get("live_trace_triage"), dict):
            data["live_trace_triage"] = build_live_trace_triage(data)
        found[trace_bundle] = data
        if len(found) == len(wanted):
            break
    return {bundle: found.get(bundle) for bundle in bundle_order}
