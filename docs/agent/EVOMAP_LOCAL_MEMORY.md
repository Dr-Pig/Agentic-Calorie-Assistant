# EvoMap Local Memory

This file is the repo-local fallback for reusable EvoMap lessons when remote EvoMap is unavailable.

It is not source truth for current product behavior. Current repo docs, code, tests, and artifacts remain higher authority.

## Record Format

Each entry should include:

- `lesson_id`
- `status`
- `signals`
- `summary`
- `future_use`
- `source_of_truth_boundary`

## Lessons

### local-2026-05-01-windows-cjk-cp950-byte-evidence

```yaml
status: active
signals:
  - windows_cp950_decode_error
  - cjk_mojibake_risk
  - terminal_rendering_issue
  - markdown_encoding
summary: >
  Windows console, PowerShell rendering, and cp950 decoding failures are not proof
  of repo file corruption. Treat terminal output as display evidence only. Verify
  bytes and parser behavior before changing content.
future_use:
  - use Python byte reads or repo encoding checkers for formal evidence
  - classify valid UTF-8 bytes with garbled terminal output as terminal_rendering_issue
  - use scripts/check_markdown_encoding.py --policy-docs --require-bom for policy markdown
  - do not use PowerShell inline non-ASCII probes as formal encoding evidence
source_of_truth_boundary: AGENTS.md Encoding Evidence Contract
```

### local-2026-05-01-remote-evomap-402-local-fallback

```yaml
status: active
signals:
  - evomap_402_insufficient_credits
  - remote_memory_unavailable
  - reusable_lesson_recording
summary: >
  Remote EvoMap recall/record can fail with insufficient credits. Do not block the
  current repo slice and do not fabricate recall. Record durable reusable lessons
  in this local fallback, then continue from repo truth.
future_use:
  - try remote EvoMap for reusable architecture/runtime/provider/eval lessons
  - if remote fails, add a concise local lesson instead of repeating long chat context
  - report that local memory does not override repo truth
source_of_truth_boundary: docs/agent/EVOMAP_WORKFLOW.md
```

### local-2026-05-01-composition-is-orchestration-not-truth

```yaml
status: active
signals:
  - architecture_boundary_debt
  - business_domain_independence
  - composition_layer_risk
  - prompt_ownership_split
summary: >
  app.composition is allowed as use-case orchestration and wiring, but must not
  become a truth owner or dumping ground. Runtime owns prompt assembly mechanics;
  domain/product specs own business instructions; provider/model profiles own
  model-specific adaptation.
future_use:
  - move cross-domain use cases to composition only when they coordinate owners
  - keep domains independent from composition and from each other
  - split composition modules by product use case instead of creating generic utils
  - do not move all prompts blindly into runtime or provider adapters
source_of_truth_boundary: AGENTS.md architecture boundary rules plus app composition PR evidence
```

### local-2026-05-01-provider-transport-capability-must-be-artifact-proven

```yaml
status: active
signals:
  - provider_transport_contract
  - model_contract_adherence
  - tool_choice_vs_json_schema
  - false_green_prevention
summary: >
  Endpoint compatibility does not prove model/provider contract reliability.
  Provider/model choices must be profile-scoped and artifact-proven. Deterministic
  code must reject unsupported tool calls rather than aliasing them into canonical
  tools.
future_use:
  - use explicit diagnostic profiles before changing default providers
  - prefer tool_choice/function-calling lanes for tool decisions when supported
  - classify unsupported model outputs as provider/model contract failures
  - keep provider adapters transport-aware, not product-semantic
source_of_truth_boundary: provider docs, B1 transport diagnostics, runtime boundary gates
```

### local-2026-05-01-readiness-scope-prevents-false-green

```yaml
status: active
signals:
  - false_green_readiness
  - fixture_scope
  - deterministic_runtime_scope
  - live_diagnostic_scope
summary: >
  Fixtures and deterministic runs may prove schemas, guards, traces, and offline
  runtime paths, but must not claim live Manager semantics, mutation readiness, or
  product readiness. Readiness claims must match evidence lineage.
future_use:
  - fixture_scaffold_pass unlocks deterministic runtime checks only
  - deterministic_runtime_pass does not imply live or product readiness
  - live_diagnostic_pass can unlock shadow evaluation, not user-facing mutation
  - require shared readiness claim blocks for official artifacts
source_of_truth_boundary: readiness claim contract and audit_readiness_claim_integrity.py
```

### local-2026-05-01-web-search-candidate-not-truth

```yaml
status: active
signals:
  - tavily_trace_only
  - web_candidate_evidence
  - packet_hard_recheck
  - runtime_web_activation
summary: >
  Web search and extract results are candidate evidence, not product truth.
  Tavily output must pass candidate extraction, packetization, hard recheck,
  accepted-packet consumption, and synthesis verification before it can support
  diagnostic synthesis. Runtime web activation is separate from trace-only canary.
future_use:
  - keep Tavily behind WebSearchPort/WebExtractPort or provider seams
  - never treat snippets or accepted extract packets as exact truth by themselves
  - classify provider unavailable, extract mismatch, candidate insufficient, and packet rejection separately
  - do not let web evidence bypass packet/hard recheck
source_of_truth_boundary: B2 evidence/synthesis specs and live search seam decision packs
```

### local-2026-05-01-auxiliary-wide-research-tests-are-not-mainline-gates

```yaml
status: active
signals:
  - full_pytest_collection_blocker
  - data_build_missing
  - auxiliary_research_tests
  - evidence_claim_integrity
summary: >
  Full pytest can be blocked by auxiliary wide-research tests that require the
  out-of-repo data_build package. Do not classify that as a mainline runtime,
  B2, or architecture regression unless the current slice explicitly depends on
  wide-research tooling.
future_use:
  - report full-suite collection blockers separately from targeted gate results
  - use repo-defined B1/B2/Founder/governance walls for mainline readiness evidence
  - do not add unrelated optional dependencies to make a focused PR look green
source_of_truth_boundary: CI workflow and targeted gate definitions
```

### local-2026-05-01-founder-live-contract-diagnostic-before-readiness

```yaml
status: active
signals:
  - founder_live_diagnostic
  - manager_contract_non_adherence
  - provider_profile_scope
  - activation_ladder
summary: >
  Founder deterministic E2E can be green while Founder live E2E still fails at
  provider/model manager-contract adherence. Treat live diagnostic failures such
  as missing required manager fields as provider_contract_non_adherence, not as
  product readiness or mutation blockers.
future_use:
  - run Founder live diagnostic only after deterministic and B2 local gates are green
  - keep GrokFast or other live models scoped to diagnostic profiles until shadow/canary evidence exists
  - record missing required structured fields as provider/model contract evidence
  - do not promote a live diagnostic pass or fail into product readiness by itself
source_of_truth_boundary: wave1_founder_e2e_live_diagnostic artifact and activation ladder
```
