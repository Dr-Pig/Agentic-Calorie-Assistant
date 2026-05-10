from __future__ import annotations

import json
import subprocess
from pathlib import Path


TODAY_PAGE = Path("static/accurate-intake-today.html")


def _extract_function_source(html: str, function_name: str) -> str:
    marker = f"function {function_name}("
    start = html.find(marker)
    if start == -1:
        raise AssertionError(f"Could not find {function_name} in Today page")
    signature_end = html.find(") {", start)
    brace_start = signature_end + 2 if signature_end != -1 else -1
    if brace_start == -1:
        raise AssertionError(f"Could not find opening brace for {function_name}")

    depth = 0
    index = brace_start
    while index < len(html):
        char = html[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return html[start : index + 1]
        index += 1
    raise AssertionError(f"Could not find closing brace for {function_name}")


def _run_render_meals(meals: list[dict[str, object]]) -> dict[str, object]:
    html = TODAY_PAGE.read_text(encoding="utf-8")
    feedback_url_source = _extract_function_source(html, "feedbackUrlForMeal")
    render_meals_source = _extract_function_source(html, "renderMeals")
    meals_json = json.dumps(meals)
    node_script = f"""
const elements = new Map();
function makeElement(tag = "div") {{
  return {{
    tagName: tag,
    className: "",
    textContent: "",
    href: "",
    dataset: {{}},
    children: [],
    innerHTML: "",
    append(...items) {{ this.children.push(...items); }},
  }};
}}
const document = {{
  createElement(tag) {{ return makeElement(tag); }},
  getElementById(id) {{
    if (!elements.has(id)) {{
      elements.set(id, makeElement("div"));
    }}
    return elements.get(id);
  }},
}};
function el(id) {{
  return document.getElementById(id);
}}
function userId() {{ return "dogfood-user"; }}
function selectedDate() {{ return "2026-05-10"; }}
{feedback_url_source}
{render_meals_source}
renderMeals({meals_json});
const list = el("meal-list");
const feedbackLinks = [];
function collect(node) {{
  if (!node || typeof node !== "object") return;
  if (node.dataset && node.dataset.feedbackAction) {{
    feedbackLinks.push({{ href: node.href, action: node.dataset.feedbackAction, text: node.textContent }});
  }}
  for (const child of node.children || []) collect(child);
}}
collect(list);
process.stdout.write(JSON.stringify({{ rowCount: list.children.length, feedbackLinks }}));
"""
    completed = subprocess.run(
        ["node", "-e", node_script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_today_meal_feedback_link_uses_stable_meal_thread_id_context() -> None:
    result = _run_render_meals(
        [
            {
                "meal_thread_id": 42,
                "meal_title": "chicken bento",
                "total_kcal": 640,
                "occurred_at": "12:30",
                "resolution_status": "completed_meal",
            }
        ]
    )

    assert result["rowCount"] == 1
    assert result["feedbackLinks"] == [
        {
            "href": (
                "/static/accurate-intake-feedback.html?"
                "user_id=dogfood-user&local_date=2026-05-10&source_page=today_diary&"
                "meal_id=42&meal_title=chicken+bento"
            ),
            "action": "report-meal",
            "text": "Report",
        }
    ]


def test_today_meal_feedback_link_is_omitted_without_stable_meal_thread_id() -> None:
    result = _run_render_meals(
        [{"meal_title": "display-only row", "total_kcal": 320, "resolution_status": "completed_meal"}]
    )

    assert result["rowCount"] == 1
    assert result["feedbackLinks"] == []
