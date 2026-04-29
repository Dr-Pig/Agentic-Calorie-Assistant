from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.live_eval_readiness import DEFAULT_LOCAL_LIVE_BASE_URL, build_live_preflight_report, fetch_server_ping

OUTPUT_DIR = ROOT / "runtime" / "evals" / "heartbeat"
EVOMAP_NODE = Path.home() / ".codex" / "evomap-node.json"


def _latest_json(directory: Path) -> str | None:
    if not directory.exists():
        return None
    files = sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(files[0]) if files else None


def _latest_report_summary_field(report_path: str | None, field: str) -> Any:
    if not report_path:
        return "not_available"
    try:
        data = json.loads(Path(report_path).read_text(encoding="utf-8-sig"))
    except Exception:
        return "not_available"
    return (data.get("summary") or {}).get(field, "not_available")


def _run_step(name: str, command: list[str]) -> dict[str, Any]:
    env = {
        **dict(os.environ),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=1800,
    )
    return {
        "name": name,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _evomap_metadata() -> dict[str, Any]:
    if not EVOMAP_NODE.exists():
        return {"evomap_node": None, "evomap_posture": "repair", "evomap_assets_used": []}
    data = json.loads(EVOMAP_NODE.read_text(encoding="utf-8-sig"))
    return {
        "evomap_node": {
            "alias": data.get("alias"),
            "node_id": data.get("node_id"),
            "hub_url": data.get("hub_url"),
        },
        "evomap_posture": "repair",
        "evomap_assets_used": [
            "gene_gep_repair_from_errors",
            "Multi-result Synthesis and Clarification",
            "AI Agent Multi-Result Tool Handler",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the strict eval heartbeat pipeline.")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--local-date", default=datetime.now().date().isoformat())
    args = parser.parse_args()
    base_url = args.base_url or DEFAULT_LOCAL_LIVE_BASE_URL
    base_url_explicit = args.base_url is not None
    ping_payload, ping_error = fetch_server_ping(base_url)
    live_preflight = build_live_preflight_report(
        base_url=base_url,
        base_url_explicit=base_url_explicit,
        ping_payload=ping_payload,
        ping_error=ping_error,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    steps = [
        _run_step("encoding_evidence_gate", [sys.executable, "scripts/check_markdown_encoding.py", "--policy-docs", "--require-bom"]),
        _run_step("parity_audit_bundle1", [sys.executable, "scripts/eval_parity_audit.py", "--bundle", "1"]),
        _run_step("parity_audit_bundle2", [sys.executable, "scripts/eval_parity_audit.py", "--bundle", "2"]),
        _run_step("bundle1_eval", [sys.executable, "scripts/run_v2_bundle1_live_eval.py", "--base-url", base_url, "--local-date", args.local_date]),
        _run_step("bundle2_eval", [sys.executable, "scripts/run_v2_bundle2_live_eval.py", "--base-url", base_url, "--local-date", args.local_date]),
        _run_step("founder_realism", [sys.executable, "scripts/run_v2_founder_realism_eval.py", "--base-url", base_url, "--local-date", args.local_date]),
        _run_step("benchmark_shadow", [sys.executable, "scripts/run_v2_benchmark_shadow_eval.py"]),
        _run_step("benchmark_blocking", [sys.executable, "scripts/run_v2_benchmark_blocking_eval.py", "--base-url", base_url, "--local-date", args.local_date]),
    ]

    latest_reports = {
        "bundle1_report": _latest_json(ROOT / "runtime" / "evals" / "v2_bundle1_live"),
        "bundle2_report": _latest_json(ROOT / "runtime" / "evals" / "v2_bundle2_live"),
        "founder_realism_report": _latest_json(ROOT / "runtime" / "evals" / "v2_founder_realism"),
        "benchmark_shadow_report": _latest_json(ROOT / "runtime" / "evals" / "benchmark_registry"),
        "benchmark_blocking_report": _latest_json(ROOT / "runtime" / "evals" / "v2_benchmark_regression"),
        "bundle1_parity_report": str(ROOT / "runtime" / "evals" / "parity_audits" / "bundle1_parity_audit.json"),
        "bundle2_parity_report": str(ROOT / "runtime" / "evals" / "parity_audits" / "bundle2_parity_audit.json"),
    }
    phase_c_gate_status = _latest_report_summary_field(latest_reports["bundle2_report"], "phase_c_gate_status")

    failed_steps = [step["name"] for step in steps if step["returncode"] != 0]
    report = {
        "generated_at": datetime.now().isoformat(),
        "base_url": base_url,
        "live_test_mode": live_preflight["live_test_mode"],
        "server_ping_status": live_preflight["server_ping_status"],
        "provider_readiness": live_preflight["provider_readiness"],
        "readiness_claim_scope": live_preflight["readiness_claim_scope"],
        "phase_c_gate_status": phase_c_gate_status,
        "live_preflight": live_preflight,
        "local_date": args.local_date,
        **_evomap_metadata(),
        "summary": {
            "status": "blocked" if failed_steps else "ok",
            "failed_steps": failed_steps,
            "live_test_mode": live_preflight["live_test_mode"],
            "server_ping_status": live_preflight["server_ping_status"],
            "phase_c_gate_status": phase_c_gate_status,
            "readiness_claim_scope": live_preflight["readiness_claim_scope"],
        },
        "steps": steps,
        "latest_reports": latest_reports,
    }

    out = OUTPUT_DIR / f"eval_heartbeat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["summary"]["status"], "failed_steps": failed_steps, "out": str(out)}, ensure_ascii=False))
    return 1 if failed_steps else 0


if __name__ == "__main__":
    raise SystemExit(main())
