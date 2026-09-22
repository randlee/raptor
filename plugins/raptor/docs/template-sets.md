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

The built-in `raptor` template set is the default selected by JSON-to-Markdown
operations and is the reference layout used by the round-trip proof. Its five
strict sc-compose templates require `document` and `artifacts`: `document.segments`
is the ordered envelope, and every artifact supplies `id`, `title`, `artifact_type`,
`status`, `domain`, `source`, `content`, `relationships`, and `subsections`.
`document.metadata` supplies the tenth record field at document scope. The removed
`provenance_block` and synthetic `body` inputs are not part of this contract.
Requirement, NFR, and ADR templates render the ordered envelope segments. The
design-document and test-plan templates render their one routed whole-document
record's verbatim `content`; their envelope is empty. A design record uses its
registered document ID. A test-plan record uses the declared bold `Test Plan ID`
when it is a valid single TEST ID or range start; the full range is retained in
`document.metadata.id_range`. Whole-document status is the first valid preamble
bold Status, or null when absent or off-list.

External sets use the same projection. Paths must be direct children of the set
directory, regular files, and not symlinks. Every digest is verified before
rendering. Keep consumer-specific fixtures beside the consumer templates and test
them in that repository.
