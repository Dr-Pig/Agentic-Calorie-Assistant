# Spec Editing Protocol

## Purpose

This protocol exists to prevent silent content loss during architecture and specification work.

Entry and loading context:

- [AGENTS.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/AGENTS.md) is the only root agent bootstrap
- [docs/DOC_INDEX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/DOC_INDEX.md) is the active docs map
- [AGENTS.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/AGENTS.md) defines the default progressive reading path into the active docs taxonomy and current-shell truth

It applies to:

- product specs
- runtime specs
- memory / retrieval specs
- eval / benchmark / safety specs
- any durable architecture document

## Hard Rules

- Do not delete-and-recreate an existing spec file.
- Do not silently rewrite a full document when the request was only to update or align it.
- Prefer minimal additive edits and section-level patches.
- Protected entrypoint and governance docs are also subject to rewrite-churn blocking; near-total staged rewrites should be treated as violations unless an approved rewrite path exists.
- If patch anchors fail more than twice, stop and switch to preservation mode.
- If the file is not in git history or has no reliable prior version, treat it as high-risk and do not rewrite it.

## Preservation Mode

When direct patching is hard, follow this order:

1. Build a content inventory.
2. Record the current section map.
3. Mark what will be added.
4. Mark what will remain unchanged.
5. Mark any section that may be restructured.
6. Confirm with the user if semantic coverage could change.

## Required Pre-Edit Checklist

Before any high-risk spec edit:

- capture a snapshot of the file
- capture the line count
- capture the heading list
- note whether the file exists in git history
- note whether the change is additive, surgical, or approved rewrite

## Approved Rewrite Rule

An approved rewrite is only allowed when:

- the user explicitly approves a rewrite
- a content inventory exists
- the previous section coverage is preserved or intentionally changed with explicit acknowledgement

## Required Post-Edit Check

After editing a spec file:

- compare heading coverage against the pre-edit snapshot
- check whether any semantic domain was dropped
- summarize what was added, preserved, and intentionally changed

## Recommended Tooling

Use the repository snapshot script before high-risk edits:

- [`scripts/spec_snapshot.ps1`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/scripts/spec_snapshot.ps1)

This script creates:

- a timestamped file snapshot
- a heading inventory
- a line-count record

## Escalation Rule

If content-preservation risk remains high:

- do not continue editing
- surface the risk
- ask for confirmation before restructuring
