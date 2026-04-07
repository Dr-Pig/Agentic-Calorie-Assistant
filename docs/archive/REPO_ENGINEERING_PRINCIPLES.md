# Repo Engineering Principles

## Goal

This repo is an isolated canary for text meal estimation.
The goal is to shape a reasoning path that generalizes, instead of hand-coding many food answers.
The product goal is accurate food calorie estimation, with ingredient-level composition resolved first and calories derived from that composition as reliably as possible.

## Default design stance

- Prefer prompt design over hard rules.
- Prefer reasoning steps over case lists.
- Prefer minimal guardrails over category-based routing tables.
- Prefer natural user-facing language over expert-system phrasing.
- Prefer stronger general judgment over food-by-food rule patching.
- Prefer better knowledge grounding and retrieval over accumulating special-case templates.

## Generalization-first policy

This harness should improve by strengthening broad capability, not by collecting many narrow food exceptions.

Default direction:

- improve the model's general judgment
- improve knowledge coverage and retrieval quality
- improve evidence selection and evidence consistency
- improve uncertainty handling through general mechanisms

Avoid treating one-off food heuristics as the main path.
Do not solve repeated misses by growing a large catalog of food-specific rules unless there is a clear, durable reason to encode that knowledge as data.

Prefer changes that generalize across many foods at once, such as:

- stronger item identity preservation
- stronger variant consistency
- better uncertainty-driver selection
- better grounding from larger and cleaner knowledge sources
- better structured output contracts

Treat food-specific templates, checklists, or heuristics as secondary tools.
They may be useful as narrow support, but they should not become the primary reasoning system.

## Core reasoning path

The model should follow this path:

1. Resolve what the meal is.
2. Resolve the meal components.
3. If components are missing, decide whether the missing composition should come from:
   - the user
   - or external evidence
4. Once components are available, estimate component-level macros.
5. Derive total kcal from macros.
6. If macros are usable, answer.
7. If macros are usable but uncertain, answer first and then explain the uncertainty naturally.

Treat composition resolution and macro estimation as separate stages.

## Implementation approach

- Keep the decision path simple and explicit.
- Use prompts to define the reasoning order, the model's responsibility, and the answer style.
- Use code mainly to wire stages together, normalize outputs, and add small defensive guardrails.
- Prefer prompt changes that improve many similar cases at once.
- Prefer natural follow-up wording that directly asks for the missing food information.
- Prefer the smallest prompt and schema that still preserve reasoning quality and observability.
- Avoid over-engineering the control layer around the model when a clearer prompt or a simpler stage boundary can solve the same problem.

## Lightweight guardrails

Use small guardrails only when they clearly prevent bad behavior:

- return a user-facing answer or a concrete follow-up instead of a raw failure
- treat weak external matches as weak evidence, not final truth
- treat private or home-cooked meals as user-known composition first
- ask one follow-up question at a time

Keep guardrails narrow and defensive. Let the prompt remain the main decision engine.

Do not rely on canned default follow-up questions as the main solution.
When clarification is needed, let the model ask a context-aware question that matches the user's actual input.
Do not patch missing follow-up quality by silently injecting an unrelated default question from code.

## Deterministic boundary

Deterministic logic should only do work that is highly certain, easily testable, and low ambiguity.

Prefer deterministic code for:

- schema and format validation
- request and trace correlation
- explicit gate conditions
- strong-match or strong-mismatch checks
- narrow defensive checks that prevent system-level failures
- evidence identity protection
- variant consistency checks
- alignment checks between selected uncertainty drivers and generated follow-up questions

Do not use deterministic code for:

- fuzzy semantic judgment
- deciding what the food "really is" when the answer is ambiguous
- deciding whether a meal is private-only from weak clues
- inferring the best ingredient composition from partial user language
- acting like a smaller rule-based model beside the main model
- replacing weak model judgment with a growing list of food-by-food exception rules

When the task depends on interpretation, uncertain categorization, food origin judgment, composition understanding, or clarification strategy, prefer letting the model decide.

Use deterministic code to constrain the system, not to replace the model's reasoning.

## Prompt defaults

When adjusting prompts:

- make the reasoning path clearer
- state what the model should do, in order
- make the output responsibility clearer
- remove unnecessary fields before adding new ones
- prefer fewer stronger instructions over many brittle instructions

Prompt updates should mostly do one of these:

- improve component resolution
- improve the choice between user clarification vs external evidence
- improve macro estimation from known components
- improve natural answer style

Treat prompts as the primary interface contract for the model.

When writing or revising prompts:

- use positive instructions as the main guidance
- tell the model what to do, in order
- define the expected output shape before asking for the task result
- keep each prompt responsible for one job
- separate stable template text from dynamic context
- prefer a small number of strong instructions over many brittle rules
- keep few-shot examples high quality and representative
- remove repetition and low-value wording before removing important rules or examples

Do not make negative wording the main control mechanism.
Negative constraints may be used as supporting guardrails, but the prompt should mainly describe the desired behavior in affirmative terms.

Prompt structure should usually be explicit:

- task and goal
- decision responsibility
- output format
- examples
- injected context

If the parser or downstream harness expects a stable shape, the prompt must ask for that exact shape clearly and directly.

Reference material:

- OpenAI prompt engineering best practices: https://help.openai.com/en/articles/6654000-prompt-engineering-best-practices-for-chatgpt
- OpenAI prompting guide: https://platform.openai.com/docs/guides/prompting
- Anthropic prompt engineering overview: https://docs.anthropic.com/en/docs/prompt-engineering
- Google Gemini prompt best practices: https://ai.google.dev/guide/prompt_best_practices

## User-facing answer style

- Sound like a helpful assistant, not a nutrition report generator.
- If asking, ask concretely for what is missing.
- If answering with uncertainty, answer first, then explain what part may move the numbers.
- If the user does not need to be blocked, keep the flow moving with an estimate plus a natural uncertainty note.

## Evaluation priority

Judge changes by these questions:

1. Did the model resolve components more correctly?
2. Did it choose the right information source when components were missing?
3. Did it derive macro estimates from components instead of skipping straight to calories?
4. Did it answer naturally?
5. Did the change improve the path without adding brittle rules or unnecessary special cases?
