---
name: markdown-json-import
version: 1.0.0
description: Convert one validated Markdown source into one canonical Raptor JSON document.
---

# Markdown JSON Import

## Purpose
Perform only the Markdown-to-canonical-JSON operation activated by Sprint A4.

## Inputs
- `repository_root`, `repository_path`, and explicit profile identity.
- `apply`: false validates without writing; true permits the bounded output.

## Execution Steps
Validate inputs, use the registered profile, preserve provenance, and return the standard envelope.

## Output Format
Return exactly one fenced JSON standard envelope.

## Error Handling
Return namespaced validation or path errors without secrets or tool traces.

## Constraints
Do not discover profiles, write SQLite, render Markdown, or operate before A4 activation.
