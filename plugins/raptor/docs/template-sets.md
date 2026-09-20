# External template sets

Consumer repositories keep custom templates and fixtures in their own repository. Raptor does not copy consumer assets into the plugin.

Place a set under `.raptor/template-sets/<name>/`. Add exactly five entry templates and `template-set.json`:

```json
{
  "name": "example",
  "version": "1.0.0",
  "templates": {
    "requirement": "requirement.md.j2",
    "non_functional_requirement": "non-functional-requirement.md.j2",
    "architecture_decision": "architecture-decision.md.j2",
    "design_document": "design-document.md.j2",
    "test_plan": "test-plan.md.j2"
  },
  "sha256": {
    "requirement.md.j2": "<sha256>",
    "non-functional-requirement.md.j2": "<sha256>",
    "architecture-decision.md.j2": "<sha256>",
    "design-document.md.j2": "<sha256>",
    "test-plan.md.j2": "<sha256>"
  }
}
```

Each entry is a strict sc-compose template declaring `provenance_block`, `artifact_id`, `title`, and `body` as required variables. Paths must be direct children of the set directory, regular files, and not symlinks. Every digest is verified before rendering. Keep consumer-specific fixtures beside the consumer templates and test them in that repository.
