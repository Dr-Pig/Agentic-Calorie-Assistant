from __future__ import annotations

from html import escape

from app.budget.interface.today_trace_debug_fields import TraceDebugFields


def render_trace_debug_html(fields: TraceDebugFields) -> str:
    manager_decision_html = ""
    if fields.manager.should_render:
        manager_decision_html = f'<div class=\"meal-meta\">clarify_posture: {escape(fields.manager.clarify_posture)} | final_action: {escape(fields.manager.final_action)}</div>'

    trace_link_html = ""
    if fields.request.trace_link:
        trace_link_html = f'<div class=\"meal-meta\"><a href=\"{escape(fields.request.trace_link)}\" target=\"_blank\">open /admin/trace/{escape(fields.request.request_id)}</a></div>'

    return f"""
    <section class=\"panel\">
      <div class=\"eyebrow\">{escape(fields.label)}</div>
      <div class=\"subtle\">Latest request artifact for this user and local day, even if the meal did not canonically commit.</div>
      <ul>
        <li class=\"meal-item\">
          <div class=\"meal-title\">Request {escape(fields.request.request_id)}</div>
          <div class=\"meal-meta\">text: {escape(fields.request.text)}</div>
          <div class=\"meal-meta\">estimated_kcal: {fields.payload.estimated_kcal} | route_target: {escape(fields.payload.route_target)}</div>
          <div class=\"meal-meta\">action_taken: {escape(fields.payload.action_taken)}</div>
          {manager_decision_html}
          <div class=\"meal-meta\">eligibility: {escape(fields.evidence.eligibility)} | why_not_exact: {escape(fields.evidence.why_not_exact)}</div>
          <div class=\"meal-meta\">macro_display: {escape(fields.macro.macro_display)} | macro_reason: {escape(fields.macro.macro_reason)}</div>
          <div class=\"meal-meta\">latency total: {fields.latency.latency_total_ms} ms | slowest: {escape(fields.latency.slowest_step_name)}</div>
          {trace_link_html}
        </li>
      </ul>
    </section>
    """


__all__ = ["render_trace_debug_html"]
