# Anti-Slop Catalog

## Purpose

This is the living record of agent failure patterns observed in this repo.

Every entry comes from a real incident. Nothing is invented preemptively.

Use this file to:

- prevent the same mistake from happening twice
- give Codex a concrete "what not to do" reference before starting a task
- record new failures as they happen

**Read this before starting any implementation task.**

---

## Definition of Done

A task is NOT complete until all of the following pass:

1. `python scripts/check_layer_integrity.py` — zero hard failures
2. `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings` — no freeze-growth violations
3. `powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1 -AuditDocsPolicy` — encoding clean
4. Relevant targeted tests pass (smoke, integration, or benchmark as appropriate for the slice)
5. `git diff --stat` — only files declared in `allowed_touch_areas` are changed
6. No protected legacy file (`app/routes.py`, `app/schemas.py`, `app/usecases/text_meal.py`) grew without explicit justification
7. No freeze-growth file (`app/application/evidence_assembly.py`, `app/application/context_assembly.py`, `app/agent/knowledge_packets.py`) was touched without a recorded reason
8. If a new spec or governance doc was added: `docs/index.md` and `AGENTS.md` Conditional Reads are updated

Do not mark a task complete until every gate above passes.

---

## Forbidden Patterns (Structural)

These are hard rules. Violating them is always wrong regardless of context.

### F-01: Business logic in `app/usecases/`

**Observed**: Agent adds orchestration, decision logic, or workflow branching directly into `app/usecases/text_meal.py` instead of extracting to `app/application/`.

**Why it's slop**: `app/usecases/` is a protected thin entrypoint. It should only wire and delegate. Business logic there cannot be tested in isolation and creates a god-file.

**Correct pattern**: New orchestration goes in `app/application/<capability>_service.py`. `app/usecases/text_meal.py` calls it.

---

### F-02: Expanding `app/routes.py` directly

**Observed**: Agent adds new route handlers or business logic directly into `app/routes.py` instead of creating a new routes module.

**Why it's slop**: `app/routes.py` is a protected legacy file. It must stay thin. Direct expansion makes it a god-file and breaks the layer boundary.

**Correct pattern**: New routes go in `app/web/<capability>_routes.py`. `app/routes.py` only includes the router.

---

### F-03: `any` type on stable typed contracts

**Observed**: Agent uses `dict[str, Any]` or untyped returns on pass outputs, commit candidates, or proposal options that have a defined `L3T` contract.

**Why it's slop**: Typed contracts exist in `L3T_TYPED_RUNTIME_CONTRACT_SPEC.md`. Using `Any` defeats schema validation and makes deterministic gate checks impossible.

**Correct pattern**: Check `L3T` for the typed contract. If the contract is missing, add it to `L3T` first, then implement.

---

### F-04: Deterministic layer rewriting LLM semantic judgment

**Observed**: Agent adds deterministic post-processing that silently overrides `action_taken`, `response_mode_hint`, `follow_up_needed`, `followup_question`, `exactness`, or `resolution_mode` after a pass completes.

**Why it's slop**: This violates `LLM_OWNERSHIP_RULE.md`. The deterministic layer may validate, reject, or request one bounded repair round. It may not silently substitute a new semantic judgment.

**Correct pattern**: If the LLM output is wrong, fix the prompt or add a bounded self-correction round. Do not patch it deterministically.

---

### F-05: Response-side distinction promoted to primary routing taxonomy

**Observed**: Agent encodes `inquiry vs explain`, tone, style, reluctance wording, or explanation density as a primary routing label or routing family.

**Why it's slop**: This violates `L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md` Section 3.3. These distinctions belong in response realization, not routing taxonomy.

**Correct pattern**: Only promote a distinction to primary routing if it changes target object attachment, workflow ownership, state mutation intent, or proposal/commit disposition.

---

### F-06: Spec consolidation that creates a second source of truth

**Observed**: Agent creates a new governance doc that "consolidates" content from existing specs, resulting in two documents that say slightly different things about the same rule.

**Why it's slop**: Consolidation docs drift. The original spec is the canonical source. A consolidation doc that paraphrases it will eventually contradict it.

**Correct pattern**: New governance docs should contain pointers and navigation, not paraphrased content. If a rule needs to change, change it in the canonical spec.

---

### F-07: Prompt fix targeting a single benchmark case

**Observed**: Agent modifies a prompt or evidence policy to fix one specific failing benchmark case (e.g., one SKU, one menu item, one utterance) without identifying the broader estimation family rule.

**Why it's slop**: This violates the `AGENTS.md` hard rule on prompt fixes. One-off patches accumulate and make prompts brittle.

**Correct pattern**: When a benchmark exposes a failure, identify the broader estimation-family rule that governs that case class. Fix the family rule, not the specific example.

---

### F-08: Rescue proposal embedded in intake reply

**Observed**: Agent generates a rescue proposal or rescue suggestion as part of the same reply that acknowledges a meal log.

**Why it's slop**: This violates `L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md` Section 4.0 and `L0_PRODUCT_CAPABILITY_SPEC.md`. Rescue must be a separate, independent chat message.

**Correct pattern**: Intake reply completes first. If rescue is warranted, it fires as a separate message from `ProactiveScheduler` or as a separate reactive response.

---

## Slop Log (Incident History)

Each entry records a specific observed incident with date and context.

Format:
```
### [DATE] [CASE-ID] Short description
**Slice**: which build slice this happened in
**What happened**: concrete description
**Root cause**: which forbidden pattern (F-XX) or new pattern
**Resolution**: what was done to fix it
```

---

### [2026-04-15] Routing taxonomy overreach in 2.7a/2.7b

**Slice**: 2.7a semantic routing eval, 2.7b drift hardening

**What happened**: Eval pack and routing prompt encoded `uncertain` and `no_action_soft_hold` as first-layer dispositions. This caused the LLM to route ambiguous utterances into a disposition bucket that changed no workflow effect, creating false precision in the taxonomy.

**Root cause**: F-05 (response-side distinction promoted to primary routing taxonomy). `uncertain` belongs to `routing_confidence` / `ambiguity_posture`. `no_action_soft_hold` belongs to response posture.

**Resolution**: L6F governance spec created. Eval foundation updated to demote these to secondary rubric. `routing_confidence` and `ambiguity_posture` extracted as independent fields.

---

### [2026-04-15] Rescue boundary: complaint ≠ reject

**Slice**: 2.5d rescue surface, 2.7d semantic routing hardening

**What happened**: LLM routed「這樣也太硬了吧」(complaint about rescue plan difficulty) as `disposition: reject`, closing the rescue proposal. Expected behavior is `answer_only` — the system should respond to the complaint without mutating proposal state.

**Root cause**: New pattern — complaint/frustration language was not distinguished from explicit rejection language in the routing spec.

**Resolution**: L3.4 Section 9.5A added: "抱怨語氣 ≠ Reject" with explicit examples of complaint vs. explicit rejection language.

---

### [2026-04-15] Topic reset not opening new workflow

**Slice**: 2.7d semantic routing hardening

**What happened**: LLM attached「剛剛那個先不管，我晚餐吃了咖哩飯」to the existing open meal_thread (805) instead of opening a new workflow. The explicit topic reset signal ("先不管") was ignored.

**Root cause**: New pattern — topic reset semantics were not defined in L3.1 Pass 1 boundary rules.

**Resolution**: L3.1 Section 4.5 updated with Topic Reset Semantics Rule: explicit topic reset + new food content → `create_new_meal` with `target_object_type: none`.

---

### [2026-04-15] Ambiguous utterance attached to wrong object

**Slice**: 2.7d semantic routing hardening

**What happened**: LLM routed「先這樣吧」(with both open rescue proposal and pending intake followup) to rescue proposal defer, mutating proposal state. Expected behavior is `answer_only` with no state mutation.

**Root cause**: New pattern — cross-workflow attachment priority when multiple open objects exist was not defined.

**Resolution**: L1 Section 4.10 added: Cross-Workflow Attachment Priority Rule with conservative default: ambiguous utterance → `answer_only`, no state mutation.

---

## How to Add a New Entry

When you observe a new slop pattern or incident:

1. If it's a new structural forbidden pattern, add it to the **Forbidden Patterns** section as `F-XX`
2. If it's a specific incident, add it to the **Slop Log** with date, slice, and resolution
3. If the incident reveals a spec gap, fix the spec first, then record the resolution here
4. Update `AGENTS.md` Hard Rules Summary if the pattern is important enough to be a repo-level hard rule

Do not add entries for hypothetical failures. Only record what actually happened.
