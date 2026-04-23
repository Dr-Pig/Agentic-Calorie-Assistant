# Semantic Routing Eval Foundation

> **⚠️ V2 架構注意：** 本文件的 `workflow_routing_pass` 概念在 V2 架構下已被取消。V2 採用 Primary Manager Agent 作為唯一語義控制面，不再有前置 semantic router。
>
> 本文件的 **Oracle Contract**（target_workflow_family、disposition、workflow_effect 的評估框架）和 **Primary vs Secondary Routing Signals** 的原則仍然有效，可作為 eval 設計的參考。
>
> **V2 eval 設計真相：** UX Journey Map（`docs/quality/UX_JOURNEY_TO_SLICE_MAP.md`）是 V2 的 eval truth。

## Purpose

`2.7a` treats semantic routing as an eval problem before it becomes a production routing problem.

Within the broader quality stack, these semantic-routing artifacts now sit under the suite-governance layer defined by [`docs/quality/L5D_SUITE_GOVERNANCE_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5D_SUITE_GOVERNANCE_SPEC.md). They do not define a parallel benchmark governance system.

This foundation must obey the repo-level decision freeze rule:

- unapproved product semantics must not be written into eval packs, benchmark oracles, semantic taxonomies, or pass/fail rubrics
- evidence collection may record competing interpretations or ambiguity clusters, but it must not silently canonize unresolved product decisions

This foundation answers:

- which open workflow or object a chat utterance should attach to
- what disposition the user is expressing toward that object
- what workflow effect the system should produce
- which response-side nuances remain secondary diagnostics rather than primary routing labels

It does not implement durable memory, retrieval deepening, or production chat routing.

## Benchmark Authority Lanes

Semantic-routing benchmark artifacts are split into two authority lanes:

- `provisional_smoke`
  - non-canonical
  - kept for runner, harness, plumbing, and exploratory drift validation
  - must not be treated as product-approved benchmark truth
- `official_canonical`
  - canonical only after explicit user approval of each case's primary outcome
  - limited to primary oracle fields
  - ambiguity cases do not belong here

Candidate cases may live in a separate review queue.
Candidate queues are evidence-collection artifacts, not oracle truth.

Under `L5D`, the current semantic-routing artifacts map as:

- `semantic_routing_provisional_smoke_v1`
- `semantic_routing_official_canonical_v1`
- `semantic_routing_candidate_queue_v1`

They remain boundary-governance artifacts, not the whole-product benchmark backbone.

The first non-routing Official Golden workflow packs now live separately for:

- intake
- rescue

Those workflow packs are the preferred source of future boundary-truth extraction, instead of re-expanding semantic-routing packs into the whole benchmark backbone.

## Founder-Fit Taxonomy

The first founder-fit semantic-routing vocabulary is:

- `proposal_accept`
- `proposal_reject`
- `proposal_defer`
- `proposal_adjust_shorter`
- `proposal_adjust_longer`
- `proposal_explain_request`
- `proposal_general_inquiry`
- `followup_completion`
- `followup_refinement`
- `new_topic_or_new_workflow`

This taxonomy remains useful as a **secondary diagnostic vocabulary**.
It is not the primary routing oracle, and it is not a deterministic override table.

## Minimal State Pack

The semantic-routing state pack should contain only:

- current user utterance
- active or open rescue proposal summary
- pending intake follow-up summary
- latest linked meal or proposal identifiers
- minimal recent message summaries
- relevant proposal metadata
- thin reject or defer reason bridge, if present

For eval hardening, the runner may normalize this pack into explicit active-object descriptors and canonical target-vocabulary hints so the LLM sees:

- which active object is a `proposal`
- which active object is a `meal_thread`
- what `target_workflow_family` values are legal
- what `target_object_type` values are legal
- what `disposition` values are legal
- which follow-up lane is an active continuation target

For prompt/state-pack hardening, the normalized pack may also expose thin routing priors such as:

- active-object recency rank
- whether a lane is the most recent unresolved conversational anchor
- object-level allowed dispositions derived from governance eligibility
- whether a topic-reset utterance should open a new workflow against `none`
- whether a soft-stop should stay non-mutating unless the user explicitly asks for reject, defer, or adjust

The state pack should not inject:

- full transcript replay
- full `llm_traces`
- full retrieval history

Those artifacts remain for offline diagnosis only.

## Oracle Contract

Every semantic-routing case should define:

- `expected_target_workflow_family`
- `expected_target_object_type`
- `expected_target_object_id`
- `expected_disposition`
- `expected_workflow_effect`

The primary judgment is workflow truth, not wording style.

Primary oracle should evaluate:

- target object attachment
- workflow ownership
- disposition
- workflow effect

`expected_semantic_family` may still be retained for secondary analysis, but it must not drive primary pass/fail if it does not change workflow effect.

For `official_canonical` packs, the canonical oracle is limited to:

- `expected_target_workflow_family`
- `expected_target_object_type`
- `expected_disposition`
- `expected_workflow_effect`

If `expected_semantic_family` is present in an official pack, it remains secondary diagnostic only.

Canonical target vocabulary for the eval contract is:

- `target_workflow_family`
  - `intake`
  - `rescue`
  - `calibration`
  - `recommendation`
  - `body_observation`
  - `general_chat`
- `target_object_type`
  - `meal_thread`
  - `proposal`
  - `body_observation`
  - `none`

- `disposition`
  - `create`
  - `continue`
  - `correct`
  - `accept`
  - `reject`
  - `defer`
  - `adjust`
  - `answer_only`
  - `open_new_workflow`

The first-layer confidence and ambiguity contract is:

- `routing_confidence`
- `ambiguity_posture`

These are not first-layer dispositions:

- `uncertain`
- `no_action_soft_hold`

`uncertain` belongs to confidence / ambiguity handling.
`no_action_soft_hold` belongs to response posture.

## Primary vs Secondary Routing Signals

Primary routing labels exist only when they change one of:

- target object attachment
- workflow ownership
- state mutation intent
- proposal / commit disposition
- whether the system should act, wait, or remain no-op

By default, these differences belong to response realization or secondary eval rubric:

- inquiry vs explain
- tone
- style
- reluctance wording
- explanation density
- gentle vs blunt framing
- coaching style

This eval foundation must not promote those distinctions into primary routing labels unless canonical spec explicitly says they change workflow effect.

If a distinction does not change:

- target object attachment
- workflow ownership
- disposition
- workflow effect

it must not be promoted into primary oracle truth.

## Drift Hardening Extension

`2.7b` extends this foundation into evidence hardening.

The live eval goal is no longer only pass/fail counts.
Each run should also emit a thin drift triage artifact that makes routing misses reviewable by cluster rather than by anecdote.

At minimum, drift triage should expose:

- `semantic_failure_cluster`
- `routing_mismatch_type`
- `ambiguity_posture`
- `state_pack_sufficiency`
- `expected_dispositions`
- provisional hypothesis:
  - taxonomy issue
  - prompt issue
  - state-pack insufficiency
  - inherently ambiguous case

### Current Drift Clusters

The founder-fit pack should keep failures grouped into these clusters:

- rescue action family drift
- intake follow-up continuation drift
- boundary discrimination drift

This is still eval-only truth.
It must not be turned into a deterministic keyword router.

## Candidate Review Workflow

Official cases must not be self-canonicalized by the implementer or agent.

The allowed promotion path is:

1. collect a candidate case in a review queue
2. present the candidate primary outcome for user approval
3. promote only user-approved cases into the official canonical pack

Primary approval is limited to:

- target object
- workflow ownership
- disposition
- workflow effect

## Style-Personalization Extension Note

Current memory and context specs do not yet define a canonical `conversation_style_profile` equivalent to the user-described `sour.md` concept.

Future personalization may need:

- communication tone preference
- explanation density preference
- blunt vs gentle framing tendency
- response-style adaptation by user

That work belongs after semantic routing is proven, not before.
