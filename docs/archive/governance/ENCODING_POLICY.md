# Encoding Policy

## Purpose

This repository treats document encoding as part of its context infrastructure.

Encoding drift causes:

- unreadable architecture docs
- broken patch anchors
- silent content-edit risk
- cross-agent handoff failures

## Required Encoding

For repository documentation files:

- all `docs/**/*.md` must be saved as `UTF-8 with BOM`
- [`AGENTS.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md) must also use `UTF-8 with BOM`
- `artifacts/docs-snapshots/**` is included because snapshot readability is part of the same context infrastructure

## Why UTF-8 with BOM

This policy is chosen for Windows-heavy workflows because it is the most stable option across:

- PowerShell
- mixed editor environments
- older Windows tooling
- cross-agent shell-based file reads

## Why This Differs From General Engineering Advice

In many modern toolchains, `UTF-8 without BOM` is the better default for source code and machine-consumed text formats.

That general advice is valid.

This repository is choosing a narrower, repo-specific exception:

- for markdown-heavy architecture, planning, and handoff documentation in a Windows-heavy multi-agent workflow, `UTF-8 with BOM` is used because it reduces shell/display mis-detection risk
- this is not a claim that all code, JSON, YAML, or all repositories should use BOM
- the main goal here is documentation stability and context preservation, not universal cross-language style purity
- this policy does not make all repo markdown BOM-governed; it only hard-governs `docs/**/*.md` and `AGENTS.md`

So the split is:

- general software-engineering default: often `UTF-8 without BOM`
- this repo's documentation policy: `UTF-8 with BOM` for markdown governance/spec docs on this Windows-centric workflow

## Shell Reading Rule

When reading Chinese markdown from the terminal, agents should assume UTF-8 and prefer explicit UTF-8 decoding / output settings instead of raw default shell behavior.

## Verification Rule

Before high-risk spec or documentation editing, agents should run:

- [`scripts/check_encoding.ps1`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/check_encoding.ps1)

This script is read-only and exists to detect markdown files that drift away from `UTF-8 with BOM`.

For explicit repair, use:

- [`scripts/normalize_encoding.ps1`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/normalize_encoding.ps1)

Formal modes:

- `-AuditDocsPolicy`
  - audits `docs/**/*.md` and `AGENTS.md`
- `-StagedOnly`
  - audits staged policy-scope markdown only
- `-AuditAll`
  - audits all repo markdown for diagnosis, but does not redefine the hard-gate scope

Normalization modes:

- `-DocsPolicy`
  - rewrites policy-scope markdown to `UTF-8 with BOM`
- `-StagedOnly`
  - rewrites only staged policy-scope markdown to `UTF-8 with BOM`

Canonical docs are also protected at commit time by:

- [`scripts/block_delete_recreate_specs.ps1`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/block_delete_recreate_specs.ps1)

## Editing Rule

Do not re-save markdown files in an unknown encoding.

If encoding is uncertain:

1. detect current file bytes first
2. normalize to `UTF-8 with BOM`
3. then perform content edits

## Preservation Rule

Encoding normalization is not permission to rewrite document structure.

If a file has encoding problems:

- fix encoding first
- do not delete-and-recreate the document
- do not silently compress sections while normalizing

## Scope

This policy applies to:

- product specs
- runtime specs
- memory / retrieval specs
- eval / benchmark / safety specs
- handoff docs
- `artifacts/docs-snapshots/**`
- [`AGENTS.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)

This policy does not hard-govern:

- `.venv/**`
- cache directories
- trash / scratch directories
- data-build artifacts outside `docs/**`

## Related Rules

- [`docs/governance/SPEC_EDITING_PROTOCOL.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/SPEC_EDITING_PROTOCOL.md)
- [`docs/references/context_memory_architecture.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/references/context_memory_architecture.md)
- [`AGENTS.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md)
- [`scripts/check_encoding.ps1`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/check_encoding.ps1)

## Appendix: Unicode-safe Testing

When testing Chinese food names or non-ASCII payloads from Windows PowerShell:

- do not assume inline Chinese literals are safe
- prefer Unicode escape literals such as `\\u70b8\\u6392\\u9aa8\\u4fbf\\u7576`
- or write the payload to a UTF-8 file first, then read and send that file
- when JSON fixtures fail because of a BOM mismatch, treat that as a harness encoding failure, not a product failure
- do not treat `????` transport corruption as a valid test run
