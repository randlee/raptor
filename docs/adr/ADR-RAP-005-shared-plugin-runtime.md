# ADR-RAP-005 — Shared integration runtime

- Status: accepted

## Context

Claude and Codex need the same validation and conversion behavior but expose
different discovery and invocation mechanisms.

## Decision

A later plugin sprint will provide shared skills, agents, registry-enforcing
runner, vendored schema package, runtime, scripts, templates, and tests. Client
adapters remain thin. The canonical schema package is the upstream authority.

## Alternatives

- Maintain independent client plugins.
- Put conversion behavior directly in skill prose or shell wrappers.

## Consequences

- Behavior is tested once and client discovery is tested separately.
- Vendoring is deterministic and detects version/hash drift.
- A1 defines only the profile/model contract; plugin files remain out of scope.
