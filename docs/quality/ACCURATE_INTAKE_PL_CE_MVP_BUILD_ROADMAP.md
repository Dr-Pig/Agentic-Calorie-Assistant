# PL+CE MVP Build Roadmap

This document is the Product Loop + Context Engineering build map for the Accurate Intake local web self-use MVP.
It is repo coordination truth, not product runtime truth.

## Current State

PR123 -> PR125 is the current PL+CE checkpoint chain:

- PR123: Product Loop browser shell checkpoint.
- PR125: PL+CE diagnostic review bundle, stacked on PR123.
- Future PL+CE work should be separate follow-up PRs, not a PR123 or PR125 mega-PR.

FoodDB/Search Evidence owns retrieval, ranking, packet-ready evidence, and runtime-visible nutrition truth.
PL+CE owns context visibility, review artifacts, fake-provider context smoke, and local product shell diagnostics.

The FoodDB boundary remains blocked_waiting_for_fdb_artifact until FoodDB provides approved packet-ready metadata.

## Serial PR Delivery Policy

Default PL+CE delivery is serial squash-merge, not long-lived stack accumulation.
The goal is to avoid ancestry drift after GitHub squash merge rewrites the PR branch lineage.

```yaml
agent_policy:
  low_risk_work:
    mode: auto_serial
    behavior:
      - open PR
      - run tests
      - verify CI green
      - verify mergeable clean
      - squash merge after the applicable human/review gate is satisfied
      - delete branch if it is not a stack base
      - refresh next branch
      - continue

  stacked_work:
    mode: allowed_with_self_retarget
    max_depth: 2
    behavior:
      - merge base PR first
      - retarget child PR to main
      - rerun CI
      - continue only if green and mergeable clean

  high_risk_work:
    mode: stop_for_human_gate
```

Low-risk PL+CE diagnostic work can proceed in one run as multiple serial PRs if each PR is opened,
tested, CI-green, mergeable clean, and squash-merged before continuing to the next slice.
Stacking is allowed only as a short bridge, with max_depth: 2 and self-retarget after the base PR merges.
High-risk work still stops for a human gate before merge or runtime activation.

## Activation Ladder

The PL+CE activation sequence is:

1. deterministic and fixture diagnostics
2. fake-provider context smoke
3. human review
4. human-approved live-diagnostic only
5. provider health smoke
6. schema contract probe
7. context-only single-case live probe
8. review artifact and overfit guard
9. FoodDB packet smoke or Kimi target-model validation

This means local context and review artifacts are built before any provider call.
Limited LLM smoke tests are local seam tests, not full product dogfood.

Do not jump directly to Kimi E2E.
Current forbidden activations:

- no Kimi full E2E
- no GrokFast full suite
- no Tavily/WebSearch runtime calling
- no FoodDB truth changes
- no product/web/private self-use readiness claim

Kimi remains deferred until model-agnostic PL+CE diagnostics and FoodDB packet integration are stable.

## Best-Practice Basis

The operating guidance is:

- Establish evals and a capability baseline before optimizing cost or latency:
  https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/
- Use function calling when connecting models to application tools and data:
  https://developers.openai.com/api/docs/guides/function-calling
- Use structured outputs when response shape needs schema-level reliability:
  https://developers.openai.com/api/docs/guides/structured-outputs
- Keep context informative but tight, and use just-in-time retrieval rather than full dumps:
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Keep tool use schema-bound and application-executed unless explicitly using a server tool:
  https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview

## Required Non-Claims

Every PL+CE artifact must preserve:

```yaml
product_readiness_claimed=false
private_self_use_approved=false
real_fooddb_pass_claimed=false
dogfood_pass=false
live_llm_invoked=false
web_tavily_used=false
production_db_used=false
fooddb_truth_updated=false
manager_context_packet_schema_changed=false
```

## Review Checkpoints

Before provider calls, human review must confirm:

- PR123 browser shell checkpoint is accepted.
- PR125 diagnostic review bundle is accepted.
- PL+CE local review decision pack is green.
- Context replay pack scenarios match real correction/removal use.
- Fake-provider context smoke passes without live provider calls.
- FoodDB remains separate and no runtime evidence truth was promoted by PL+CE.

## Later Live Gate

The later live diagnostic gate starts only after deterministic PL+CE closure.
The order is:

1. deterministic PL+CE decision pack green
2. fake-provider context smoke green
3. human approval
4. provider health smoke
5. schema contract probe
6. one context-only single-case live probe
7. review artifact and overfit guard
8. only then FoodDB packet smoke or Kimi target-model validation

The live gate remains diagnostic-only.
It must not select a production provider, approve private self-use, or change runtime truth.
