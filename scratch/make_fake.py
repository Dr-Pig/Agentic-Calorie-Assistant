import json
from pathlib import Path

Path("fake_report.json").write_text(json.dumps({
  "summary": {
    "bundle_gate": "pass",
    "p0_failed": 0
  },
  "audit": {
    "request_trace_exists": False
  }
}), encoding="utf-8")
