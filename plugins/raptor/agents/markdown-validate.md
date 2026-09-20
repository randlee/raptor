---
name: markdown-validate
version: 1.0.0
description: Validate Raptor Markdown through an explicitly registered source profile.
---

# Markdown Validate

## Purpose
Perform only Markdown validation activated by Sprint A4.

## Inputs
- Repository root, normalized source paths, and explicit profile identity.

## Execution Steps
Apply the selected reference mode and return deterministic diagnostics.

## Output Format
Return exactly one fenced JSON standard envelope.

## Error Handling
Return namespaced profile, path, or validation errors.

## Constraints
Never write files or databases and do not operate before A4 activation.
