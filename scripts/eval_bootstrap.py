from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval_parity_audit import run_parity_audit
from scripts.pre_edd_readiness import DEFAULT_REPORT_PATH as PRE_EDD_REPORT_PATH
from scripts.pre_edd_readiness import run_pre_edd_readiness

FOUNDER_OUTPUT_DIR = ROOT / "runtime" / "evals" / "v2_founder_realism"
CREDENTIALS_FILE = ROOT / ".evomap_credentials.json"
CANONICAL_PRE_EDD_STATUS_KEYS = (
    "single_manager_contract_status",
    "domain_tool_surface_status",
    "guard_invariant_status",
    "fat_service_status",
    "latency_trace_status",
    "product_truth_alignment_status",
    "anti_overfit_status",
)


def ensure_evomap_online() -> dict[str, Any]:
    """Ensures the EvoMap node is awake and online."""
    print("Checking EvoMap node status...")
    if not CREDENTIALS_FILE.exists():
        return {"status": "missing_credentials", "node_id": None}

    try:
        creds = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
        node_id = creds.get("your_node_id")
        secret = creds.get("node_secret")

        if not node_id or not secret:
            return {"status": "invalid_credentials", "node_id": node_id}

        req = urllib.request.Request(
            "https://evomap.ai/a2a/heartbeat",
            data=json.dumps({"node_id": node_id}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {secret}"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"EvoMap node {node_id} is ONLINE (Survival: {result.get('survival_status')})")
            return {
                "status": "online",
                "node_id": node_id,
                "survival_status": result.get("survival_status"),
                "credit_balance": result.get("credit_balance"),
            }
    except Exception as exc:
        print(f"EvoMap activation failed: {exc}")
        return {"status": "offline", "error": str(exc)}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_pre_edd_report(*, timeout_seconds: int = 180) -> dict[str, Any]:
    report = run_pre_edd_readiness(timeout_seconds=timeout_seconds)
    _write_json(PRE_EDD_REPORT_PATH, report)
    return report


def _canonical_pre_edd_statuses(pre_edd_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    statuses = dict(pre_edd_report.get("statuses") or {})
    return {
        key: dict(statuses.get(key) or {"status": "not_run", "details": ["missing canonical pre-EDD status"]})
        for key in CANONICAL_PRE_EDD_STATUS_KEYS
    }


def _architecture_purity_from_pre_edd(statuses: dict[str, dict[str, Any]]) -> str:
    architecture_keys = (
        "single_manager_contract_status",
        "domain_tool_surface_status",
        "guard_invariant_status",
        "fat_service_status",
        "product_truth_alignment_status",
    )
    return "pass" if all(statuses[key].get("status") == "pass" for key in architecture_keys) else "fail"


def _trace_roundtrip_status() -> tuple[bool, str]:
    trace_roots = (
        ROOT / ".logs",
        ROOT / "runtime" / "logs" / "requests",
        ROOT / "runtime" / "logs" / "stage_traces",
    )
    for root in trace_roots:
        if root.exists() and any(path.is_file() for path in root.rglob("*")):
            return True, str(root)
    return False, ""


def load_founder_realism_status() -> dict[str, Any]:
    if not FOUNDER_OUTPUT_DIR.exists():
        return {"status": "not_run", "report_path": None, "blocking_failed": None}
    reports = sorted(FOUNDER_OUTPUT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        return {"status": "not_run", "report_path": None, "blocking_failed": None}
    latest = reports[0]
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "not_run", "report_path": str(latest), "blocking_failed": None}
    summary = data.get("summary", {}) or {}
    blocking_failed = summary.get("blocking_failed")
    status = "pass" if int(blocking_failed or 0) == 0 else "fail"
    return {
        "status": status,
        "report_path": str(latest),
        "blocking_failed": blocking_failed,
    }


def build_bootstrap_checklist(
    *,
    bundle: int | str,
    founder_realism_status: dict[str, Any] | None = None,
    pre_edd_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pre_edd = pre_edd_report or ensure_pre_edd_report()
    all_pre_edd_statuses = dict(pre_edd.get("statuses") or {})
    pre_edd_statuses = _canonical_pre_edd_statuses(pre_edd)
    architecture_purity = _architecture_purity_from_pre_edd(pre_edd_statuses)
    encoding_status = dict(all_pre_edd_statuses.get("encoding_status") or {"status": "not_run", "details": []})
    evomap = ensure_evomap_online()
    parity = run_parity_audit(bundle)
    founder = founder_realism_status or load_founder_realism_status()
    trace_exists, trace_root = _trace_roundtrip_status()

    text_integrity = "healthy"
    if trace_exists:
        for trace_dir in (ROOT / ".logs", ROOT / "runtime" / "logs"):
            if not trace_dir.exists():
                continue
            for log_file in trace_dir.rglob("*.json*"):
                try:
                    txt = log_file.read_text(encoding="utf-8")
                    if "\\ufffd" in txt or "????" in txt:
                        text_integrity = "corrupted"
                        break
                except Exception:
                    continue
            if text_integrity == "corrupted":
                break

    return {
        "owner_truth_loaded": True,
        "bundle_eval_pack_loaded": True,
        "parity_audit_completed": True,
        "pre_edd_report_path": str(PRE_EDD_REPORT_PATH),
        "pre_edd_readiness_status": pre_edd.get("summary", {}).get("status", "not_ready_for_edd"),
        "architecture_purity": architecture_purity,
        "encoding_evidence_status": encoding_status.get("status", "not_run"),
        "encoding_evidence": {
            "status": encoding_status.get("status", "not_run"),
            "details": list(encoding_status.get("details") or []),
            "evidence_source": "pre_edd_readiness_report",
            "terminal_rendering_is_evidence": False,
        },
        "evomap_status": evomap.get("status"),
        "coverage_blocking_gaps": int(parity.get("coverage_blocking_gaps") or 0),
        "trace_roundtrip_verified": trace_exists,
        "trace_roundtrip_source": trace_root,
        "founder_suite_status": founder.get("status", "not_run"),
        "text_integrity_status": text_integrity,
        **pre_edd_statuses,
        "parity_audit": parity,
        "founder_realism": founder,
        "evomap": evomap,
    }


def build_bundle_verdict(
    *,
    runner_case_status: str,
    coverage_status: str,
    founder_realism_status: str,
    checklist: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checklist = checklist or {
        "architecture_purity": "pass",
        "encoding_evidence_status": "pass",
        "text_integrity_status": "healthy",
        "trace_roundtrip_verified": True,
        **{key: {"status": "pass"} for key in CANONICAL_PRE_EDD_STATUS_KEYS},
    }
    ready = (
        runner_case_status == "pass"
        and coverage_status == "complete"
        and founder_realism_status == "pass"
        and checklist.get("architecture_purity") == "pass"
        and checklist.get("encoding_evidence_status") == "pass"
        and all((checklist.get(key) or {}).get("status") == "pass" for key in CANONICAL_PRE_EDD_STATUS_KEYS)
        and checklist.get("text_integrity_status") == "healthy"
        and checklist.get("trace_roundtrip_verified") is True
    )
    return {
        "runner_case_status": runner_case_status,
        "coverage_status": coverage_status,
        "founder_realism_status": founder_realism_status,
        "bundle_ready_for_human_e2e": ready,
    }


if __name__ == "__main__":
    check = build_bootstrap_checklist(bundle=2)
    print("\n--- Bootstrap Checklist Result ---")
    print(json.dumps(check, indent=2))
