# Wide Research Usage

## Purpose

This document defines the preferred way to use Wide Research in this repo.

Wide Research is a coverage tool.
It should be used to gather many independent sources or source fragments without dropping coverage.
It should not be forced to behave like a perfect one-shot structured database builder unless the scope is very small.

## When to use Wide Research

Use Wide Research when the bottleneck is:

- coverage
- source harvesting
- high-volume evidence collection
- many independent brands, chains, pages, PDFs, or product families

Good repo-specific examples:

- harvesting official nutrition pages
- gathering official menu pages
- collecting official PDFs
- collecting retailer product pages that expose package nutrition text
- building high-frequency kcal candidate pools for chains, convenience stores, and packaged foods

## Preferred shard shape

For this repo, the preferred shard shape is:

- one brand
- one source family
- one small item group

Prefer:

- one brand or one source family per run
- narrow shards that keep output short and complete

Avoid:

- mixed-brand batches
- very large multi-family batches
- prompts that ask the same run to do discovery, judging, schema filling, variant resolution, and final DB promotion all at once

## Preferred workflow

When using Wide Research for data building, prefer this order:

1. discover and capture high-value raw sources
2. preserve provenance and original content
3. normalize into candidate records
4. review and promote into formal runtime data

## Raw-source-first principle

For coverage-building work, prefer raw-source harvesting over strict structured generation as the first pass.

Examples of good first-pass assets:

- official nutrition pages
- official menu pages
- official PDFs
- product pages with visible nutrition labels
- retailer product pages that clearly mirror package nutrition text

On the first pass, it is acceptable to capture:

- `source_url`
- `source_name`
- `source_type`
- `captured_at`
- `raw_content`
- basic notes

and postpone exact schema normalization to a later step.

Do not force strict JSON too early if that would significantly reduce coverage.
Structured candidate generation is useful, but only after a high-value source has already been found and captured.

## What not to do

Do not make a single Wide Research subtask responsible for too many jobs at once.
Avoid combining:

- source discovery
- source judging
- exact variant resolution
- strict schema filling
- final DB promotion

into one large step unless the scope is very small.

Prefer other approaches over Wide Research when:

- the task is a small one-off source lookup
- the main problem is local normalization, parsing, or review
- the main missing piece is not source discovery but downstream canonicalization

## Why this repo uses this stance

Earlier work in this repo showed that forcing small-batch strict structured generation too early led to:

- low throughput
- over-constrained candidates
- wasted model effort on formatting instead of coverage
- delayed discovery of high-value official pages and PDFs

The current repo stance is:

- use Wide Research to expand high-value raw coverage first
- then use normalization and review to shape that material into candidate pools and runtime DBs
