# Current Shell v1 Coordination Roadmap

This legacy-path document records the Current Shell v1 coordination map for the Accurate Intake local web self-use candidate.
The file path retains `PL_CE` for compatibility, but the active ownership split is `ManagerRuntime` + `AppShell`.
It is repo coordination truth, not product runtime truth.

## Current State

The merged legacy PL+CE checkpoint train is the current local diagnostic baseline:

- PR123: Product Loop browser shell checkpoint.
- PR125: PL+CE diagnostic review bundle.
- PR508: pre-live artifact refresh chain that rebuilds promoted product-page, browser-activation, context-live, and local-web candidate artifacts from current canonical local evidence.
- Later legacy PL+CE slices landed as independent main-based PRs through GitHub Merge Queue.
- Future Current Shell v1 work should be separate follow-up PRs, not a mega-PR or long-lived stack.

FoodDB/Search Evidence owns retrieval, ranking, packet-ready evidence, and runtime-visible nutrition truth.
ManagerRuntime owns upstream runtime contracts, manager/tool gates, and renderer input basis.
AppShell owns downstream browser verification, render-only shell behavior, and same-truth review artifacts.

The FoodDB boundary remains blocked_waiting_for_fdb_artifact until FoodDB provides approved packet-ready metadata.

## Non-FoodDB Manager Tool Convergence

ManagerRuntime owns the chat-first Manager-managed tool surface for app-state capabilities outside FoodDB/Search Evidence.
This is a pre-FoodDB integration responsibility: users may ask about daily budget, body plan, weight state, calibration proposals, or app usage through chat before FoodDB/WebSearch is ready.

The target coarse tool inventory is:

- `budget.get_today_summary`
- `budget.get_remaining_calories`
- `budget.get_day_meal_log`
- `body.get_active_plan`
- `body.get_latest_observation`
- `body.record_observation`
- `calibration.preview_proposal`
- `calibration.get_pending_proposal`
- `calibration.apply_stored_proposal_action`
- `app.answer_usage_question`

The currently converged runtime subset on `main` is:

- `budget.get_remaining_calories` via the live `read_day_budget` read-only manager tool seam
- `budget.get_day_meal_log` via the live `read_day_budget` read-only manager tool seam
- `body.get_active_plan` via the live `read_body_plan` read-only manager tool seam
- `app.answer_usage_question` via the live fallback app-help read-only manager tool seam

The remaining non-FoodDB tool inventory is still partially diagnostic or direct-lane backed until later slices convert it:

- `budget.get_today_summary`
- `body.get_latest_observation`
- `body.record_observation`
- `calibration.preview_proposal`
- `calibration.get_pending_proposal`
- `calibration.apply_stored_proposal_action`

Tool staging is:

- `read_only`: budget, body, and app-help reads from canonical read models.
- `proposal_persisting`: calibration preview or pending proposal surfaces may persist proposal containers only through existing domain policy.
- `mutation_bearing`: weight recording and stored calibration proposal actions require explicit Manager decision plus guard evidence.

FoodDB/Search Evidence still owns nutrition retrieval, ranking, packet-ready evidence, WebSearch candidate evidence, and runtime-visible nutrition truth.
ManagerRuntime must not implement FoodDB lookup, WebSearch ranking, packet promotion, nutrition truth, or evidence-truth mutation.
AppShell must not invent runtime semantics, frontend truth math, or mutation legality.

Semantic ownership for this convergence is:

- Manager owns natural-language intent, tool choice, target posture, and final response planning.
- Deterministic code may provide context, candidates, schemas, allowed tool lists, validation, guard results, and canonical tool results.
- Deterministic code must not infer final intent, choose the final tool, select the final target, or authorize mutation from raw text.
- UI may render backend/read-model/trace structured fields only.

The pre-FoodDB legacy PL+CE build train is:

1. Product Pages Evidence Into Pre-Live Pack
2. Manager Tool Surface Inventory / Direct Lane Audit
3. Non-FoodDB Manager Tool Contract
4. Manager Tool-Choice Regression Wall
5. Context-Conditioned Intent + Target Wall
6. Read-Only Tool Loop Fake Smoke
7. Proposal / Mutation Tool Guard Smoke
8. Live Context/Tool Diagnostic Case Matrix
9. Limited Live Diagnostic
10. Legacy `PLCE` Pre-FoodDB Candidate Bundle

The top-level pre-live decision pack must directly consume the finished product-page/browser activation artifacts and the finished non-FoodDB Manager tool diagnostics before any human live-diagnostic review:

- `product_pages_self_use_flow_gate`
- `ui_context_alignment_pack`
- `browser_activation_evidence_gate`
- `manager_tool_surface_inventory`
- `non_fooddb_manager_tool_contract`
- `manager_tool_choice_regression_wall`
- `context_conditioned_intent_wall`
- `non_fooddb_read_only_tool_loop_fake_smoke`
- `non_fooddb_mutation_tool_guard_smoke`

## Current-Shell Coordination Artifacts

The machine-readable coordination artifacts for downstream AppShell/browser work and merge-governance checks are:

- `docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml`
- `docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml`

These are the sources that downstream AppShell/browser gates and merge-governance checks should read instead of inferring runtime readiness from markdown prose alone.

## Merge Queue Delivery Policy

Default Current Shell v1 coordination delivery is GitHub Merge Queue serial delivery from latest `origin/main`.
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

Low-risk Current Shell v1 diagnostic work can proceed in one run as multiple serial PRs if each PR is opened,
tested, checks-green, added to GitHub Merge Queue, merged, and verified on main before the next slice starts.
Branch cleanup is allowed only after the PR is merged, local status is clean, and the remote branch has been pruned or confirmed gone.
High-risk work still stops for a human gate before merge or runtime activation.

## Activation Ladder

The Current Shell v1 activation sequence is:

1. deterministic and fixture diagnostics
2. fake-provider context smoke
3. prompt registry and cache policy recorded
4. nutrition estimate quality and final response quality walls green
5. human review
6. human-approved live-diagnostic only
7. provider health smoke
8. schema contract probe
9. tool-choice or context-conditioned single-case live probe
10. FoodDB packet single-case probe
11. nutrition/response quality mini-matrix
12. review artifact and overfit guard
13. FoodDB packet smoke or Kimi target-model validation

This means local context and review artifacts are built before any provider call.
Limited LLM smoke tests are local seam tests, not full product dogfood.

Do not jump directly to Kimi E2E.
Current forbidden activations:

- no Kimi full E2E
- no GrokFast full suite
- no Tavily/WebSearch runtime calling
- no FoodDB truth changes
- no product/web/private self-use readiness claim

Kimi remains deferred until model-agnostic ManagerRuntime diagnostics and FoodDB packet integration are stable.

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
- Keep stable prompt prefix content first and dynamic user/context content later to improve prompt-cache hits:
  https://developers.openai.com/api/docs/guides/prompt-caching
- Keep role/tone guidance in the system/developer layer and task-specific details/examples in the user layer:
  https://developers.openai.com/api/docs/guides/prompting
- Define eval objectives, datasets, metrics, and held-out continuous evaluation rather than vibe-based checks:
  https://developers.openai.com/api/docs/guides/evaluation-best-practices
- Grade agent traces, tool calls, and end-to-end decisions as structured runtime evidence:
  https://developers.openai.com/api/docs/guides/trace-grading

## Required Non-Claims

Every legacy `PL+CE` / Current Shell coordination artifact must preserve:

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
- the legacy `pl_ce_local_review_decision_pack` artifact is green.
- Context replay pack scenarios match real correction/removal use.
- Fake-provider context smoke passes without live provider calls.
- FoodDB remains separate and no runtime evidence truth was promoted by ManagerRuntime or AppShell.

## Later Live Gate

The later live diagnostic gate starts only after deterministic Current Shell v1 closure.
The order is:

1. deterministic Current Shell v1 decision pack green
2. fake-provider context smoke green
3. human approval
4. provider health smoke
5. schema contract probe
6. one context-only single-case live probe
7. review artifact and overfit guard
8. only then FoodDB packet smoke or Kimi target-model validation

The live gate remains diagnostic-only.
It must not select a production provider, approve private self-use, or change runtime truth.
