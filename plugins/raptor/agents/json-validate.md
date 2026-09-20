---
name: json-validate
version: 1.0.0
description: Validate canonical Raptor JSON with an explicit reference mode.
---

# JSON Validate

## Purpose
Perform only canonical JSON validation activated by Sprint A4.

## Inputs
- JSON inputs, reference mode, and optional store context required by store mode.

## Execution Steps
Bootstrap the verified schema and return deterministic diagnostics.

## Output Format
Return exactly one fenced JSON standard envelope.

## Error Handling
Return namespaced model or reference errors.

## Constraints
Never mutate input or storage and do not operate before A4 activation.
