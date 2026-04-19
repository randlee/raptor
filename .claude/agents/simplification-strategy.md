---
name: simplification-strategy
version: 1.0.0
description: Template for repo simplification strategy. Replace with actual strategy before enabling simplification-reviewer.
---

# Simplification Strategy

> ⚠️ **MUST EDIT — Project-Specific Document**
> This file is a template. Replace all sections below with the actual
> simplification strategy for this repo before assigning simplification-reviewer tasks.

---

## Approved Direction

<!-- Document the high-level direction: what is being deleted, what is being
     converged, and what the end-state architecture looks like. -->

## Elimination Targets

<!-- List the concrete types, paths, flags, or abstractions that are approved
     for deletion. For each target, state the replacement owner (if any) or
     confirm that no replacement is needed. -->

## Sequencing Constraints

<!-- Identify any ordering dependencies — targets that cannot be deleted until
     another cleanup lands first. These are acceptable-temporary holds only if
     the sequencing reason is documented here. -->

## Hard Rules

<!-- State the invariants that simplification-reviewer enforces as FAIL conditions.
     Example: "No new discriminator fields may be added to carry a deleted concept." -->

## Review Standards

<!-- Reference or inline the review standards that govern classification rulings
     (dead-path, redundant-path, preserved-carrier, scope-creep, etc.) -->

---

# No Active Simplification Strategy

No simplification strategy has been defined for this repo yet.

**If you are an agent reading this file:** return the following verdict immediately without reviewing any code:

```json
{
  "verdict": "PASS",
  "items_reviewed": 0,
  "findings": [],
  "summary": "No simplification strategy configured for this repo. No items identified for simplification."
}
```
