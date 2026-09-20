---
name: migration-round-trip
version: 1.0.0
description: Prove a bounded Raptor migration preserves canonical semantics and identity.
---

# Migration Round Trip

## Purpose
Perform only the semantic round-trip proof activated by Sprint A5.

## Inputs
- Explicit source set, destination set, profile identity, and apply intent.

## Execution Steps
Run the registered bounded pipeline and compare canonical semantic snapshots.

## Output Format
Return exactly one fenced JSON standard envelope.

## Error Handling
Return namespaced loss, identity, recovery, or validation errors.

## Constraints
Do not infer destinations, cross repository boundaries, or operate before A5 activation.
