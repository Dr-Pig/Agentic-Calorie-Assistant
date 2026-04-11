# Context and Memory Architecture

This document defines the pre-multi-turn context and memory design for the text meal agent.

## Memory layer responsibilities

### 1. State memory
Purpose: carry the current meal across nearby turns in the same session.

Fields:
- `active_meal_state`
- `pending_followup_state`
- `recent_corrections`
- `current_session_preferences_light`

Rules:
- session-scoped only
- no semantic retrieval
- runtime reads and writes this layer directly

### 2. Typed meal records
Purpose: persist meal facts that can be retrieved by date, meal type, brand, alias, and correction lineage.

Rules:
- structured retrieval before transcript retrieval
- time and category filters first
- transcript semantic search is not the primary access path

### 3. Transcript hybrid retrieval
Purpose: recover older, fuzzier historical mentions when state memory and typed meal records do not resolve the query.

Rules:
- third-layer fallback
- keyword-heavy for brand/item lookup
- more semantic when the user is recalling a vague historical conversation

## Meal record schema

Core identifiers:
- `meal_id`
- `session_id`
- `conversation_id`
- `user_id`

Lifecycle:
- `status`: `draft`, `needs_followup`, `finalized`, `corrected`
- `correction_parent_meal_id`
- `correction_note`

Time:
- `created_at_utc`
- `updated_at_utc`
- `occurred_at_utc`
- `occurred_at_local`
- `local_date`
- `timezone`
- `relative_time_label`

Meal facts:
- `meal_type`
- `user_input_raw`
- `normalized_user_input`
- `resolved_food_items`
- `estimated_kcal`
- `protein_g`
- `carb_g`
- `fat_g`
- `component_breakdown`
- `estimate_mode`
- `confidence`
- `evidence_ids_used`
- `evidence_summary`

Follow-up:
- `followup_status`
- `missing_slots`

Rules:
- never collapse correction lineage into an untraceable overwrite
- relative time labels are a read-time convenience; absolute timestamps remain the source of truth

## History retrieval router

Router order:
1. `state_memory`
2. `typed_meal_records`
3. `transcript_hybrid`

Routing rules:
- supplementing a previous answer or pending question -> `state_memory`
- explicit date, meal type, "today breakfast", "yesterday lunch", "last Tuesday dinner" -> `typed_meal_records`
- fuzzy historical recall without clear date or meal type -> `transcript_hybrid`

## Context pack composition

### Static system prompt
Should include:
- product role
- LLM ownership rules
- evidence hierarchy
- follow-up principles
- session continuity principles
- timezone policy

Should not include:
- current clock time
- per-turn evidence details
- long transcript dumps

### Dynamic context pack
Should include:
- `active_meal_summary`
- `active_meal_state`
- `pending_followup_state`
- `recent_relevant_turns`
- `retrieved_meal_records`
- `session_summary`
- `reasoning_state`
- `evidence_lane_summary`
- `observation_summary`
- absolute and relative time context

### Time format
Each time-aware dynamic section should expose:
- `absolute_date`
- `relative_label`
- `local_timestamp`

### Prompt cache rule
- keep the system prompt stable
- place high-churn state in the dynamic context pack
- inject current time as dynamic context, not by rewriting the system prompt

## Context Infrastructure Editing Rule

This repository treats context and memory documents as infrastructure, not disposable drafts.

Hard rule:

- do not delete-and-recreate existing context / memory / architecture spec files
- do not silently compress or rewrite a document without first checking semantic coverage
- prefer additive edits, explicit section patches, and content inventories
- do not allow context infrastructure docs to drift into mixed or unknown encodings
- treat encoding normalization as infrastructure maintenance, not as permission to rewrite content

If a document must be restructured:

- first inventory the existing content domains
- confirm the rewrite if coverage risk exists
- preserve all previously agreed concepts across the new structure

Encoding baseline:

- context / memory / architecture markdown should use `UTF-8 with BOM`
- shell-based reads should assume explicit UTF-8 handling
