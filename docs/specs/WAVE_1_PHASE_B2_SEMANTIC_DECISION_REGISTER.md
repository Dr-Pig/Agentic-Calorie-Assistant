# Wave 1 Phase B-2 Semantic Decision Register

## Purpose

This register records approved and pending product-semantic decisions for Wave 1 Phase B-2.

It is intentionally thin. It prevents live diagnostic reports, decision-pack helpers, eval bundle wording, or stale artifacts from becoming accidental product truth owners.

This register does not implement runtime behavior, mutation semantics, provider policy, retrieval policy, or UI same-truth behavior.

## Ownership Rules

- Approved decisions in this register supersede stale active eval expectations.
- Pending decisions must not be converted into guard behavior, test oracle truth, prompt policy, copy, runtime semantics, or mutation behavior.
- Decision pack artifacts remain diagnostic and reference-only; they are not canonical semantic owners.
- Bundle and runner vocabulary remains acceptance compatibility vocabulary unless this register or a canonical B2 spec promotes the behavior.
- Archived docs and completed task artifacts are not default truth for B2 semantics.

## Approved Decisions

```yaml
approved:
  pearl_milk_tea_missing_sugar_size:
    status: approved
    selected_policy: logged_estimate_with_followup
    scope:
      - missing sugar level
      - missing cup size
      - first-turn pearl milk tea logging
    decision:
      - missing sugar level or cup size does not make pearl milk tea unresolved
      - turn 1 may be a logged estimate with a strong follow-up
      - follow-up is a precision/refinement request, not a hidden commit gate
    supersedes:
      - C-001 old draft expectation
      - decision-pack pending status for this case
      - active oracle wording that requires canonical_commit=false on turn 1
      - active oracle wording that requires consumed_kcal==0 on turn 1
    affected_runtime_owner:
      - B2 final mapping boundary
      - CommitBoundaryDecision
      - Phase C projection as guardrail only

  follow_up_for_estimable_items:
    status: approved
    selected_policy: precision_refinement_not_commit_gate
    scope:
      - estimable food logging cases
      - follow-up after an honest estimate
    decision:
      - follow-up may coexist with logged estimates
      - follow-up severity describes refinement value, not commit permission
      - unresolved composition remains draft
    supersedes:
      - estimate_with_followup_always_means_draft
    affected_runtime_owner:
      - B2 final mapping boundary
      - follow-up policy
      - renderer honesty wording

  salt_crispy_chicken_surface_term_resolution:
    status: approved
    selected_policy: context_sensitive_multi_sense_resolution
    scope:
      - Taiwan food mention semantics
      - surface term 鹽酥雞
      - Wave 1 Phase B-2 evidence metadata placement
    decision:
      - surface term 鹽酥雞 must not be modeled as a one-way alias
      - portion cue present generally resolves toward a generic estimable item
      - meal or vendor context without listed items generally resolves toward self-selected basket ask-first
      - listed components resolve toward listed basket item-level lookup
    cue_examples:
      status: illustrative_not_exhaustive
      generic_item_examples:
        - 一份鹽酥雞
        - 一包鹽酥雞
        - 小份鹽酥雞
      self_selected_basket_examples:
        - 晚餐吃鹽酥雞
        - 買鹽酥雞
        - 宵夜吃鹽酥雞
      listed_basket_examples:
        - 鹽酥雞，有甜不辣、米血、四季豆
    affected_runtime_surfaces:
      - food knowledge metadata
      - evidence path selection
      - B2 packetizer inputs
      - Manager Pass 2 synthesis inputs
    downstream_observed_by:
      - B2 final mapping boundary

  self_selected_basket_without_listed_items:
    status: approved
    selected_policy: ask_first_unresolved_no_logged_estimate
    scope:
      - bare self-selected basket foods without listed items
      - composition-unknown mixed foods where the user has not named ingredients
    examples:
      - 滷味
      - 鹽酥雞 as vendor or self-selected-basket sense
      - 麻辣燙
      - 自助餐
      - 鹹水雞
      - 關東煮
    decision:
      - ask for items and approximate portions before estimating
      - do not emit kcal estimates before listed items are available
      - do not emit item_results before listed items are available
      - do not allow canonical write or logged estimate on the bare basket turn
    estimate_allowed: false
    item_results_allowed: false
    canonical_write_allowed: false
    affected_runtime_owner:
      - B2 source selection as ask-first selector
      - B2 live diagnostic payload contract
      - B2 live diagnostic validator
```

## Pending Decisions

```yaml
pending:
  homemade_dish_minimum_estimability:
    status: pending
    question: What minimum ingredient, dish, or portion detail makes homemade food estimable?
    default_until_approved: composition-unknown food remains draft or clarify-first

  tavily_exact_brand_scope:
    status: pending
    question: Should first live web scope stay exact-brand trace-only or widen after anchor policy?
    default_until_approved: exact_brand_trace_only

  llm_synthesis_trust_boundary:
    status: pending
    question: What error range and influence scope are acceptable before user-facing canary?
    default_until_approved: diagnostic_only_until_shadow_comparison_green

  founder_human_e2e_required_journeys:
    status: pending
    question: Which journeys are mandatory founder gates before a readiness claim?
    default_until_approved: core_intake_budget_correction_only
```

## Current Mainline Sequence

```yaml
current_mainline: B2 / Phase B semantic closure
next_mainline_after_this_register:
  - B2 final mapping closure
  - B2 evidence / packet / synthesis contract alignment
  - deterministic B2 semantic closure tests
  - packet-based B2 live LLM diagnostic
  - exact-brand web trace-only canary
```
