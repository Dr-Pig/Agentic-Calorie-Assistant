from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "static" / "accurate-intake-review.html"
SHELL = ROOT / "static" / "accurate-intake-local-shell.html"
PAGES = [
    ROOT / "static" / "accurate-intake-chat.html",
    ROOT / "static" / "accurate-intake-today.html",
    ROOT / "static" / "accurate-intake-body.html",
    ROOT / "static" / "accurate-intake-feedback.html",
    ROOT / "static" / "accurate-intake-data.html",
]


def _html(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_review_queue_static_page_is_read_only_local_triage_surface() -> None:
    html = _html(REVIEW)

    assert 'data-page-id="accurate-intake-review-page-v1"' in html
    assert 'data-surface-role="dogfood-review-queue"' in html
    assert 'data-claim-scope="local_dogfood_review_queue_artifact"' in html
    assert 'data-feedback-is-product-truth="false"' in html
    assert 'data-manager-context-injection="false"' in html
    assert 'data-fooddb-truth-update-allowed="false"' in html
    assert 'data-canonical-eval-promotion-allowed="false"' in html
    assert 'data-frontend-semantic-owner="false"' in html
    assert 'const endpoint = "/accurate-intake/review-queue";' in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html
    assert "canonical_eval_promotion_allowed: true" not in html
    assert "food_kb_truth_update_allowed: true" not in html


def test_review_queue_navigation_is_available_from_desktop_shell_pages() -> None:
    assert 'data-entry-target="review"' in _html(SHELL)
    assert "/static/accurate-intake-review.html" in _html(SHELL)

    for path in PAGES:
        html = _html(path)
        assert 'data-nav-target="review"' in html
        assert "/static/accurate-intake-review.html" in html


def test_review_queue_page_displays_feedback_trace_fields_without_semantic_inference() -> None:
    html = _html(REVIEW)

    for fragment in (
        "feedback_triage_record_count",
        "review_candidate_count",
        "correction_feedback_event_count",
        "desktop_feedback_records",
        "review_candidates",
        "record.feedback_id",
        "record.status",
        "linked.trace_id",
        "linked.message_id",
        "policy.feedback_can_create_product_truth",
        "policy.feedback_can_create_fooddb_truth",
        "policy.feedback_can_create_eval_truth",
    ):
        assert fragment in html

    for forbidden in (
        "final_action",
        "workflow_effect",
        "mutation_legality",
        "message.content.includes",
        "message.content.match",
        "ready_for_fdb_integration=true",
        "product_readiness_claimed=true",
        "private_self_use_approved=true",
    ):
        assert forbidden not in html


def test_review_queue_page_surfaces_feedback_source_context_for_triage() -> None:
    html = _html(REVIEW)

    for fragment in (
        "linked.user_external_id",
        "uiEvent.source_page",
        "uiEvent.route",
        "uiEvent.feedback_route",
        "source_page",
        "route",
        "feedback_id",
        "status",
        "user",
    ):
        assert fragment in html
