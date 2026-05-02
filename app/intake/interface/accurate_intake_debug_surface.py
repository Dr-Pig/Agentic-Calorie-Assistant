from __future__ import annotations

import json
from html import escape
from typing import Any


def render_accurate_intake_debug_surface(payload: dict[str, Any]) -> str:
    model = dict(payload.get("model") or {})
    today = dict(model.get("today_summary") or {})
    meal_threads = list(model.get("meal_threads") or [])
    pending_drafts = list(model.get("pending_drafts") or [])
    corrections = list(model.get("correction_history") or [])
    ledger_events = list(model.get("ledger_audit_events") or [])
    same_truth = dict(model.get("same_truth") or {})

    def _rows(items: list[Any], empty: str) -> str:
        if not items:
            return f"<li class=\"empty\">{escape(empty)}</li>"
        rows = []
        for item in items:
            text = json.dumps(item, ensure_ascii=False, sort_keys=True)
            rows.append(f"<li><code>{escape(text)}</code></li>")
        return "\n".join(rows)

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Accurate Intake Debug</title>
  <style>
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, sans-serif; background: #f8fafc; color: #0f172a; }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 32px 20px 48px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    section {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 18px; margin-top: 18px; }}
    .muted {{ color: #64748b; }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }}
    .stat {{ border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; }}
    .label {{ font-size: 11px; text-transform: uppercase; letter-spacing: .12em; color: #64748b; font-weight: 700; }}
    .value {{ font-size: 26px; font-weight: 800; margin-top: 6px; }}
    li {{ margin: 10px 0; }}
    code {{ white-space: pre-wrap; overflow-wrap: anywhere; }}
  </style>
</head>
<body>
  <main>
    <h1>Accurate Intake Debug Surface</h1>
    <p class="muted">Read-only local MVP surface. It mirrors canonical read models and does not create product truth.</p>
    <section>
      <div class="stats">
        <div class="stat"><div class="label">User</div><div class="value">{escape(str(payload.get("user_external_id") or ""))}</div></div>
        <div class="stat"><div class="label">Date</div><div class="value">{escape(str(payload.get("local_date") or ""))}</div></div>
        <div class="stat"><div class="label">Consumed</div><div class="value">{escape(str(today.get("consumed_kcal", 0)))}</div></div>
        <div class="stat"><div class="label">Remaining</div><div class="value">{escape(str(today.get("remaining_kcal", 0)))}</div></div>
        <div class="stat"><div class="label">Same Truth</div><div class="value">{escape(str(same_truth.get("status") or payload.get("state_posture") or "unknown"))}</div></div>
      </div>
    </section>
    <section><h2>Meal Threads</h2><ul>{_rows(meal_threads, "No meal threads found.")}</ul></section>
    <section><h2>Pending Drafts</h2><ul>{_rows(pending_drafts, "No pending drafts.")}</ul></section>
    <section><h2>Correction History</h2><ul>{_rows(corrections, "No corrections yet.")}</ul></section>
    <section><h2>Ledger Audit Events</h2><ul>{_rows(ledger_events, "No ledger audit events.")}</ul></section>
    <section><h2>Same Truth Trace</h2><ul>{_rows([same_truth] if same_truth else [], "No same-truth trace.")}</ul></section>
  </main>
</body>
</html>"""
