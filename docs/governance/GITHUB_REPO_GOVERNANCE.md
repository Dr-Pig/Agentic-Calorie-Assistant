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
- `pre-edd-readiness`
- `runtime-contract-tests`
- `wave1-phase-a-contracts`
- `wave1-phase-b-contracts`

If workflow job names change, this document must be updated in the same governance change.

Manual-only workflows are not required status checks:

- `wave1-runtime-smoke`
- `cd`

## Serial PR Delivery Policy

Default agent delivery is serial squash-merge, not long-lived stacked PR accumulation.
This avoids ancestry drift after GitHub squash merge rewrites branch lineage.

```yaml
agent_policy:
  low_risk_work:
    mode: auto_serial
    behavior:
      - open PR
      - run tests
      - verify CI green
      - verify mergeable clean
      - squash merge after the applicable human/review gate is satisfied
      - delete branch if it is not a stack base
      - refresh next branch from main
      - continue

  stacked_work:
    mode: allowed_with_self_retarget
    max_depth: 2
    behavior:
      - merge base PR first
      - retarget child PR to main
      - rerun CI
      - continue only if green and mergeable clean

  high_risk_work:
    mode: stop_for_human_gate
```

Low-risk diagnostic, docs, fixture, candidate, validator, and non-runtime-truth slices may proceed in one run as multiple serial PRs if each PR is opened, tested, CI-green, mergeable clean, and squash-merged before the next slice continues.

Stacking is allowed only as a short bridge with `max_depth: 2`. After the base PR merges, retarget the child PR to `main`, rerun CI, and continue only if the child remains green and mergeable clean.

High-risk work still stops for a human gate before merge or runtime activation. High-risk includes production DB work, user-facing rollout/readiness claims, mutation-authority changes, shared contract changes, live provider activation beyond diagnostic scope, and runtime-visible truth promotion without an approved promotion boundary.

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
