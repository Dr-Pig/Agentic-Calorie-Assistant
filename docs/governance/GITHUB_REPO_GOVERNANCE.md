# GitHub Repo Governance

## Purpose

This document records the GitHub platform settings that must be enabled outside the repository so repo-level checks actually gate merges.

Repo files can define workflows and scripts, but they cannot enforce branch protection by themselves.

## Required Branch Protection

Apply these settings to the default protected branch, expected to be `main`:

- require a pull request before merging
- require approval reviews before merging
- require conversation resolution before merging
- disallow merges that bypass required status checks
- disallow direct pushes except for approved administrators if your org policy requires it

## Required Status Checks

The following check names must be required:

- `repo-hygiene-and-architecture`
- `runtime-contract-tests`
- `product-pages-browser-e2e`

If workflow job names change, this document must be updated in the same governance change.

Advisory-only workflows are not required status checks:

- `merge-governance`
- `ci-advisory`
- `wave1-runtime-smoke`
- `cd`

Minimal policy for this repo:

- required checks should stay small, stable, and merge-group safe
- browser verification is kept because it validates user-visible CurrentShell behavior
- the required browser wall must validate user-visible product surfaces and required read-model sync only; hidden readiness markers, debug panels, and trace panels are not merge-path pass criteria
- merge-governance reports remain available for manual review, but they do not block merges
- deep environment, MVP, and phase-labeled audit walls live in `ci-advisory` and are manual-only
- broad candidate-bundle, EDD, or phase-labeled audit packs should not sit on the required merge path unless they directly prove merge safety
- merge governance advisory reports are diagnostic-only; no legacy debt-matrix verdict engine should sit on the merge path
- Q-owner queue artifacts are retired; the only main promotion path is the official GitHub Merge Queue plus human review

## Merge Queue Delivery Policy

Default agent delivery is GitHub Merge Queue serial delivery from latest `origin/main`, not manual merging or long-lived stacked PR accumulation.
This avoids ancestry drift and lets branch protection/merge-group checks arbitrate stale bases and failed checks.

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

Low-risk diagnostic, docs, fixture, candidate, validator, and non-runtime-truth slices may proceed in one run as multiple serial PRs if each PR is opened, tested, checks-green, added to GitHub Merge Queue, merged, and verified on main before the next slice continues.

Dependent child PRs are allowed only when the next slice truly depends on the parent. A child PR must not enter Merge Queue until the parent is merged; after the parent merges, refresh the child on `main`, rerun checks, then add it to Merge Queue.

Branch cleanup is allowed only after the PR is merged, local status is clean, and the remote branch has been pruned or confirmed gone.

High-risk work still stops for a human gate before merge or runtime activation. High-risk includes production DB work, user-facing rollout/readiness claims, mutation-authority changes, shared contract changes, live provider activation beyond diagnostic scope, and runtime-visible truth promotion without an approved promotion boundary.

## CurrentShell Canonical Track Rules

Current-shell machine-facing governance now uses:

```yaml
track: CurrentShell
owner_lane: ManagerRuntime | AppShell | SharedCurrentShell
```

Hard rules:

- `CurrentShell` is the canonical top-level machine track for current-shell work.
- `ManagerRuntime`, `AppShell`, and `SharedCurrentShell` are owner lanes, not top-level tracks.
- `owner_lane` is the machine-facing ownership field for `CurrentShell` PR metadata and queue/readiness checks.
- `FoodDB` remains an independent truth-owner track.
- legacy `PLCE` / `PL+CE` / `PL_CE` / `ProductLoop` wording may remain only as temporary compatibility vocabulary for older paths, artifacts, and cutover aliases.
- no new PR should open with canonical `track: PLCE` after the CurrentShell governance cutover lands.

## Platform-Level Hygiene

Enable or confirm:

- Dependabot version updates
- Dependabot updates for GitHub Actions
- pull request review workflow for repo changes that affect governance or CI

## Repo Relationship

This document complements:

- [`AGENTS.md`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/AGENTS.md)
- [`docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)
- [`docs/governance/TASK_CHECKIN_PROTOCOL.md`](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/governance/TASK_CHECKIN_PROTOCOL.md)

It does not replace repo-local gates; it ensures they become merge requirements instead of advisory automation.
