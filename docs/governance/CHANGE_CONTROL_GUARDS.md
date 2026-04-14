# Change Control Guards

## Purpose

This document defines when a normal implementation task must stop and convert into replan, boundary review, or architecture review.

## Replan Triggers

Trigger replan when any of the following becomes true:

- the task needs a new slice that is not yet formalized
- the task crosses protected legacy files in a non-thin way
- the task touches freeze-growth files without a shrink-only or boundary-safe reason
- the ordering legality becomes ambiguous
- the write set expands beyond the declared boundary
- the harness can no longer prove the intended boundary safely

## Architecture Change Checks

Before making a structure-changing decision, answer:

1. is the target layer correct for the change reason?
2. is a new module family needed?
3. will the change create a new execution or semantic dependency?
4. does source-of-truth documentation need to change too?

## Safe Default

When in doubt, stop and make the boundary explicit in the active execution docs or a replan note before proceeding.