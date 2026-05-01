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

  homemade_food_minimum_estimability:
    status: approved
    selected_policy: clarify_bare_home_cooked_food_estimate_listed_anchored_food
    scope:
      - bare 家常菜 / 媽媽煮的 references
      - home-cooked listed dishes
      - home-cooked listed dishes with portion detail
    decision:
      - bare 家常菜 or 媽媽煮的 remains clarify/draft
      - listed dishes with portion anchors may become logged estimates
      - listed dishes without portions may be estimated only with strong follow-up
      - listed dishes without an approved local anchor remain clarify/draft
    affected_runtime_owner:
      - B2 retrieval intent from manager decision
      - local evidence metadata seed
      - B2 packetizer and synthesis inputs
      - B2 final mapping boundary

  taiwan_b2_case_law_narrow_set:
    status: approved
    selected_policy: formalize_existing_narrow_case_law_only
    scope:
      - 茶葉蛋
      - 雞腿便當
      - 麻辣燙
      - 麻辣臭豆腐
      - 松屋牛丼
      - 鹽酥雞 multi-sense resolution
      - self-selected basket rules already listed above
    decision:
      - this register formalizes the current narrow B2 case-law set
      - no additional food semantics are approved by this closure slice
      - seed metadata may support lookup and packetizer coverage but must not decide logged/draft/mutation

  exact_item_cards_local_diagnostic_seed_only:
    status: approved
    selected_policy: local_app_owned_diagnostic_seed
    scope:
      - app/knowledge/exact_item_cards_tw.json
      - exact lookup and packetizer tests
    decision:
      - exact item card seeds exercise local lookup and packetizer behavior only
      - the seed file does not claim production database accuracy
      - exact seed metadata must not become product semantic authority

  tavily_web_candidate_evidence_only:
    status: approved
    selected_policy: candidate_evidence_requires_packetizer_and_hard_recheck
    scope:
      - Tavily search candidates
      - selected web evidence
    decision:
      - web candidates must pass source selection, packetizer, and hard recheck before synthesis
      - rejected candidates must remain unavailable to synthesis evidence_used
      - web candidates do not become runtime truth or mutation authority by themselves

  model_policy_single_profile_stability_only:
    status: approved
    selected_policy: hooks_and_gates_only_before_pre_shadow
    scope:
      - Founder live decision pack
      - provider/profile matrix
      - model diversity evidence
    decision:
      - single-model 3x strict live evidence may claim single_profile_stability only
      - if no alternate profile was run, decision reason remains model_diversity_missing
      - alternate model canary belongs to the pre-shadow activation train, not B2 local closure
```

## Superseded Eval Expectations

- MS7 pearl milk tea old draft expectation is superseded by `pearl_milk_tea_missing_sugar_size`.
- Stale first-turn pearl milk tea draft fixtures must not override the approved logged-estimate-with-followup policy.
- This supersession does not add UI, memory, proactive, rescue, production DB accuracy, or shadow-readiness semantics.

## Pending Decisions

```yaml
pending:
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
