# Sprint A3 — Plugin Discovery, Vendor, and Runner Foundation

## Objective

Deliver the production-ready dual-client plugin shell: exact public discovery names, thin router skills and references, eight focused agent contracts, deterministic vendoring of the authoritative schema runtime, and one shared registry-enforcing agent runner with thin Claude/Codex adapters.

- Branch: `phase-a/03-plugin-foundation`
- Stack relation: `must_follow A2`
- Merge-forward trigger: A2 development is pushed; merge A2 into A3 before every development/fix round.
- PR-completion trigger: A2 PR merges first.

## Scope boundary

A3 makes plugin discovery, routing contracts, vendoring, dependency bootstrap, registry resolution, runtime response enforcement, and unsupported-route behavior operational. It does not implement Markdown/JSON/SQLite transformations; A4 activates those six agents/routes. It does not implement JSON→Markdown or semantic round-trip; A5 activates those two agents/routes. Dolt remains a documented future interface returning `RAPTOR.UNSUPPORTED.DOLT`.

Every authoritative deliverable must land production-ready for this foundation boundary. No manifest, skill, reference, agent contract, vendor check, runner behavior, or client adapter may be a shape-only placeholder.

Normative design reference: [`references/claude-code-skills-agents-guidelines-v0.7.md`](references/claude-code-skills-agents-guidelines-v0.7.md).

## Stable public surface and layout

Both clients expose exactly:

```text
/raptor:import
/raptor:export
/raptor:validate
/raptor:round-trip
```

```text
plugins/raptor/
  .claude-plugin/plugin.json
  .codex-plugin/plugin.json
  plugin-manifest.json
  skills/{import,export,validate,round-trip}/
  agents/
    registry.yaml
    markdown-json-import.md
    json-sqlite-import.md
    sqlite-json-export.md
    markdown-validate.md
    json-validate.md
    sqlite-validate.md
    json-markdown-export.md
    migration-round-trip.md
  scripts/
    _bootstrap.py
    agent_runner.py
    validate_plugin.py
    client_adapters/{claude.py,codex.py}
  _vendor/raptor_schema/
```

All four skills and eight agents have versioned YAML frontmatter. Skills are progressive-disclosure routers only. During A3, every product route returns a structured `RAPTOR.UNSUPPORTED.PHASE` naming A4 or A5, except Dolt references, which return `RAPTOR.UNSUPPORTED.DOLT`. Unsupported never reports success or delegates to a transformation agent.

## Authoritative vendor/bootstrap contract

- Source is exactly `schema/src/raptor_schema/` at the merged A2 commit. The vendor includes importable package files and declared package data; it excludes tests, `__pycache__`, `.pyc`, build output, and platform metadata.
- The refresh operation copies through a repository-root staging directory, deletes stale files, verifies, then atomically replaces `_vendor/raptor_schema/`. Interruption leaves the prior vendor intact.
- The tree hash is SHA-256 over each included file in lexicographic POSIX-path order, feeding `relative_path + NUL + file_bytes + NUL`. `plugin-manifest.json` records algorithm, tree hash, canonical schema version, `raptor_schema` package version, Python constraint, Pydantic constraint, and complete packaged inventory.
- Check mode independently hashes source and vendor, verifies byte equality/inventory/version metadata, and fails on missing, extra, stale, or hand-edited files. CI runs refresh followed by `git diff --exit-code` and check mode.
- `_bootstrap.py` verifies the manifest and vendor hash before import, rejects an already-loaded `raptor_schema` from another path, inserts `plugins/raptor/_vendor` ahead of site packages, imports the vendored package, and verifies package/schema versions. Vendored runtime always wins; there is no installed-package fallback.
- Third-party dependencies are not copied. The plugin declares the same Python/Pydantic constraints as `schema/pyproject.toml`, checks them before routing, and directs missing/incompatible dependencies to installation troubleshooting.
- A clean-environment test uses an empty `PYTHONPATH` and temporary environment containing only plugin-declared dependencies plus the plugin; importing from the source checkout or an installed `raptor_schema` is forbidden and tested.

## Authoritative shared runner/client-adapter contract

```python
class AgentBackend(Protocol):
    def invoke(self, *, agent_path: Path, prompt: str, timeout_s: int) -> str: ...

def run_agent(
    *, agent: str, params: Mapping[str, JsonValue],
    version_constraint: str | None = None,
    timeout_s: int = 120, correlation_id: str | None = None,
    backend: AgentBackend,
) -> AgentEnvelope: ...
```

The shared runner resolves only plugin-local `agents/registry.yaml`, enforces exact/`1.x` version constraints, canonicalizes and allowlists the registered path, computes its SHA-256 and matches the plugin manifest, constructs the agent prompt, invokes the selected backend with timeout, and accepts exactly one fenced JSON object matching the standard envelope. It returns `REGISTRY.RESOLUTION`, `REGISTRY.VERSION`, `REGISTRY.HASH`, `EXECUTION.TIMEOUT`, or `EXECUTION.RESPONSE` errors on failure, with no automatic retry unless `recoverable=true` and never more than once. It redacts secrets/tool traces and writes only the guideline-approved redacted audit fields under repository-local `.raptor/state/logs/` using atomic writes.

Claude and Codex adapters contain only host invocation mechanics implementing `AgentBackend`; they do not resolve agents, interpret routes, validate envelopes, retry, transform artifacts, or alter errors. Both manifests invoke the same runner and registry.

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A3-D1 | Both manifests expose the exact four stable commands and package the same files. | discovery/package tests |
| A3-D2 | Four thin router skills, focused references, installation/troubleshooting pages, and structured A3/Dolt unsupported behavior. | complete skill inventory and routing tests |
| A3-D3 | Eight single-responsibility agent contracts with versioned frontmatter plus registry path/version constraints. | agent inventory, registry, validation |
| A3-D4 | Deterministic atomic schema-vendor refresh/check, complete manifest metadata, strict bootstrap/import precedence, and dependency checks. | vendor scripts, clean-environment tests |
| A3-D5 | Shared registry/hash/timeout/fencing/error/redaction/audit runner and logic-free Claude/Codex backend adapters. | runner/adapters and fault-injection tests |
| A3-D6 | CI validator for pinned guideline invariants, frontmatter, registry, manifests, inventories, links, response schemas, vendor, and package parity. | `validate_plugin.py` and CI gate |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A3-AC1 | Both clients resolve exactly the four public command names to matching skills and identical packaged inventory. |
| A3-AC2 | Skills load only selected references; all A3 product routes and all Dolt routes return their distinct structured unsupported errors without agent execution. |
| A3-AC3 | All eight agent files/registry entries are focused, version-compatible, hash-inventoried, and rejected on missing/extra/path/version/hash drift. |
| A3-AC4 | Refresh/check is deterministic and atomic; clean-env bootstrap imports only the verified vendor with exact schema/package/dependency versions and no fallback. |
| A3-AC5 | Runner tests cover successful resolution, unknown/path-escape/version/hash failures, timeout, malformed/unfenced/multiple envelopes, redaction, retry cap, and atomic audit. |
| A3-AC6 | Client adapters pass equivalent conformance fixtures and contain no registry, route, transformation, or response-policy logic. |
| A3-AC7 | No P3 asset, `NFT`, SQLx, Dolt implementation, product transformation script, or sc-compose template is added. |

## Authoritative validation

```sh
python -m pip install -e 'schema[test]'
python -m pytest plugins/raptor/tests/foundation plugins/raptor/tests/runner plugins/raptor/tests/vendor
python plugins/raptor/scripts/validate_plugin.py --guideline docs/plans/phase-a/references/claude-code-skills-agents-guidelines-v0.7.md --check-frontmatter --check-registry --check-manifests --check-inventory --check-vendor
git diff --exit-code -- plugins/raptor/_vendor/raptor_schema plugins/raptor/plugin-manifest.json
env -i PATH="$PATH" PYTHONPATH= python -m pytest plugins/raptor/tests/vendor/test_clean_environment.py
test ! -e schema/sql/dolt
test ! -e plugins/raptor/templates
rg -n 'p3-documentation|REQ-P3-|NFR-P3-|ADR-P3-|\bNFT\b|sqlx' plugins/raptor && exit 1 || true
```

## Traceability

| Deliverable | Phase requirements |
|---|---|
| A3-D1, A3-D2, A3-D3 | PA-REQ-006, PA-NFR-006 |
| A3-D4 | PA-REQ-001, PA-REQ-003, PA-REQ-005, PA-NFR-004, PA-NFR-005 |
| A3-D5, A3-D6 | PA-REQ-006, PA-NFR-001, PA-NFR-004 |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Vendor becomes a second authority | deterministic source hash, byte check, atomic refresh, no fallback, clean-env test. |
| Client behavior forks | adapters implement one protocol; shared runner owns every policy and conformance fixture. |
| Agent registry can be bypassed | manifests/skills call runner only; direct unregistered paths fail tests and inventory gates. |
| Foundation implies unfinished routes work | every route explicitly returns A4/A5/Dolt unsupported; activation belongs only to owning sprint. |

## Non-closure

- No implemented Markdown/JSON/SQLite route; A4 owns them.
- No JSON→Markdown, sc-compose template, or semantic round-trip; A5 owns them.
- No Dolt DDL, driver, connection, fixture, integration test, or placeholder directory.
- No consumer profile/fixture copied into Raptor.

## Handoff to A4

A4 consumes immutable public command names, skills/references, eight agent contracts, registry, runner, adapters, verified vendor/bootstrap, and manifest/inventory gates. It activates only Markdown/JSON/SQLite validate/import/export routes through shared scripts and six focused agents.
