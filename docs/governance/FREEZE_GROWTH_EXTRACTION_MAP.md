# Freeze-Growth Extraction Map

## Purpose

This document is the file-level extraction map for current freeze-growth and watchlist modules.

It complements, but does not replace:

- [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
- [Build File Placement Rules](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/BUILD_FILE_PLACEMENT_RULES.md)
- [Layer Dependency Rules](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/LAYER_DEPENDENCY_RULES.md)

Use this when a task needs to touch one of the large guarded modules below.

## Status Model

- `freeze-growth`: may shrink or stay flat, but must not take new responsibilities
- `watchlist`: may still move, but should be reviewed before accepting new responsibilities
- `extract now`: preferred first split when the next task touches this area
- `extract later`: valid target, but wait for a task that creates clear pressure

## app/application/evidence_assembly.py

Current role mix:

- evidence merge and dedupe
- evidence lane classification
- source tier classification
- candidate normalization and shaping
- tool request / tool result packaging
- calibration and local retrieval packet bridging

Target split:

- `app/application/evidence_selector.py`
  - lane split, rank hints, selection caps, exact-vs-anchor filtering
- `app/application/evidence_normalizer.py`
  - canonical item shaping, source tier fields, lookup-key-safe payload normalization
- `app/application/tool_evidence_policy.py`
  - tool request assembly, tool availability reasoning, tool result packet shaping

Extract now:

- evidence normalization helpers
- selector / ranking / lane split logic

Extract later:

- calibration packet bridging if a later calibration slice needs its own module family

Trigger to split now:

- any task touching both retrieval ranking and tool packet shaping
- any task adding a new evidence lane or source tier
- any task increasing this file while it is already frozen

## app/application/context_assembly.py

Current role mix:

- text normalization and lookup tokenization
- planner context payload assembly
- context pack shaping
- route / pass specific payload formatting
- turn-state shaping and response-adjacent assembly

Target split:

- `app/application/context_normalizer.py`
  - text normalization, lookup key, lookup tokens, portion clue extraction
- `app/application/planner_context_assembler.py`
  - planner payload, boundary payload, conversation-state prompt-facing assembly
- `app/application/context_pack_builder.py`
  - dynamic context pack, trace-facing context shaping, compact chunk/open-meal projection

Extract now:

- normalization / tokenization helpers
- chunk and context-pack compaction helpers

Extract later:

- planner payload and route-specific assembly, once the next planning slice clarifies the contract boundary

Trigger to split now:

- any task touching both lookup normalization and planner payload assembly
- any new route-specific shaping added to this file
- any change that introduces another context consumer with different payload needs

## app/agent/knowledge_packets.py

Current role mix:

- local knowledge loading and caching
- lookup normalization and key generation
- exact item lane packet construction
- anchor / risk / local knowledge retrieval
- source metadata shaping

Target split:

- `app/agent/knowledge_loader.py`
  - JSON load, cache, repository-local knowledge file access
- `app/agent/knowledge_lookup_normalizer.py`
  - normalize, canonicalize, tokenization, lookup-key logic
- `app/agent/exact_item_packets.py`
  - exact lane packet assembly and exact candidate shaping
- `app/agent/local_knowledge_selector.py`
  - risk packet selection, anchor selection, bounded local retrieval

Extract now:

- normalization / token helpers
- exact item packet assembly

Extract later:

- risk and anchor selection, when retrieval or risk-gate work touches those families directly

Trigger to split now:

- any task that touches exact-item lane and generic local search in the same change
- any task that adds a new knowledge file family
- any task that needs packet shaping independent from file loading

## app/agent/nutrition_engine.py

Status:

- `watchlist`

Current role mix:

- macro profile registry
- alias registry
- heuristic ratio policy
- lookup result shaping
- nutrition estimation support logic

Target split:

- `app/agent/nutrition_profiles.py`
  - static alias tables, default macro profiles, food-specific ratio maps
- `app/agent/nutrition_lookup_policy.py`
  - bounded lookup rules, evidence-role assignment, confidence tier decisions
- `app/agent/nutrition_estimation_support.py`
  - result shaping and estimation support helpers

Extract now:

- static profile and alias tables, if the next task touches registry growth

Extract later:

- lookup policy, once a future nutrition-resolution slice changes confidence or evidence-role rules

Trigger to freeze formally:

- this file grows again
- a task mixes static profile registry work with runtime lookup policy changes

## Execution Rule

When a freeze-growth file is touched:

1. do not add a new responsibility to the existing file
2. prefer the `extract now` target if the task crosses more than one current role
3. if the task is bug-fix-only and fully bounded to one existing role, keep the file flat or smaller
4. update the task artifact with `actual_touch_files[]` and note whether extraction was intentionally deferred

## Practical Default

Do not schedule a full multi-file extraction only because a file is large.

Do schedule extraction when:

- the next slice must touch the frozen file
- the change crosses more than one role listed above
- review/debug cost is already visible
