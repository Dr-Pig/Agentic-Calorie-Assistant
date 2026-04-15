# Semantic Routing Eval Foundation

## Purpose

`2.7a` treats semantic routing as an eval problem before it becomes a production routing problem.

This foundation answers:

- what semantic family a chat utterance belongs to
- which open workflow or object it should attach to
- whether it mutates an existing proposal or follow-up lane, requests explanation, defers, closes, or opens a new workflow

It does not implement durable memory, retrieval deepening, or production chat routing.

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

This taxonomy is an eval oracle and runtime target vocabulary.
It is not a deterministic override table.

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

- which active object is a `rescue_proposal`
- which active object is an `intake_followup`
- what `target_workflow_family` values are legal
- what `target_object_type` values are legal
- which follow-up lane maps to `followup_completion` versus `followup_refinement`

The state pack should not inject:

- full transcript replay
- full `llm_traces`
- full retrieval history

Those artifacts remain for offline diagnosis only.

## Oracle Contract

Every semantic-routing case should define:

- `expected_semantic_family`
- `expected_target_workflow_family`
- `expected_target_object_type`
- `expected_target_object_id`
- `expected_workflow_effect`

The primary judgment is workflow truth, not wording style.

Canonical target vocabulary for the eval contract is:

- `target_workflow_family`
  - `rescue_proposal`
  - `intake_followup`
  - `new_topic`
- `target_object_type`
  - `proposal_container`
  - `meal_log`
  - `none`

## Drift Hardening Extension

`2.7b` extends this foundation into evidence hardening.

The live eval goal is no longer only pass/fail counts.
Each run should also emit a thin drift triage artifact that makes routing misses reviewable by cluster rather than by anecdote.

At minimum, drift triage should expose:

- `semantic_failure_cluster`
- `routing_mismatch_type`
- `ambiguity_posture`
- `state_pack_sufficiency`
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

## Style-Personalization Extension Note

Current memory and context specs do not yet define a canonical `conversation_style_profile` equivalent to the user-described `sour.md` concept.

Future personalization may need:

- communication tone preference
- explanation density preference
- blunt vs gentle framing tendency
- response-style adaptation by user

That work belongs after semantic routing is proven, not before.
