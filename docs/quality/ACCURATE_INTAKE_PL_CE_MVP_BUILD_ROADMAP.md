# PL+CE MVP Build Roadmap

This document is the Product Loop + Context Engineering build map for the Accurate Intake local web self-use MVP.
It is repo coordination truth, not product runtime truth.

## Current State

The merged PL+CE checkpoint train is the current local diagnostic baseline:

- PR123: Product Loop browser shell checkpoint.
- PR125: PL+CE diagnostic review bundle.
- Later PL+CE slices landed as independent main-based PRs through GitHub Merge Queue.
- Future PL+CE work should be separate follow-up PRs, not a mega-PR or long-lived stack.

FoodDB/Search Evidence owns retrieval, ranking, packet-ready evidence, and runtime-visible nutrition truth.
PL+CE owns context visibility, review artifacts, fake-provider context smoke, and local product shell diagnostics.

The FoodDB boundary remains blocked_waiting_for_fdb_artifact until FoodDB provides approved packet-ready metadata.

## Merge Queue Delivery Policy

Default PL+CE delivery is GitHub Merge Queue serial delivery from latest `origin/main`.
The goal is to avoid ancestry drift, stale queue races, and the obsolete `main-merge-lock` path.

```yaml
agent_policy:
  low_risk_work:
    mode: merge_queue_serial
    behavior:
      - fetch latest origin/main
      - create a new main-based branch
      - open PR
      - run tests
      - wait for PR checks green
      - Add to Merge Queue
      - wait for PR state MERGED
      - confirm main push CI is not red
      - cleanup only after merged and clean
      - fetch latest origin/main before the next slice
      - do not use main-merge-lock

  dependent_child_pr:
    mode: allowed_but_not_queueable_until_parent_merged
    behavior:
      - build child only if the next slice truly depends on parent
      - keep child out of Merge Queue until parent PR is MERGED
      - refresh child onto main after parent merges
      - rerun checks before Add to Merge Queue

  high_risk_work:
    mode: stop_for_human_gate
```

Low-risk PL+CE diagnostic work can proceed in one run as multiple serial PRs if each PR is opened,
tested, checks-green, added to GitHub Merge Queue, merged, and verified on main before the next slice starts.
Branch cleanup is allowed only after the PR is merged, local status is clean, and the remote branch has been pruned or confirmed gone.
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
