from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from .models import (
    ArtifactKey,
    ArtifactTarget,
    DesignDocument,
    SourceDocument,
    TestPlan,
)


@dataclass(frozen=True)
class CanonicalReference:
    source: ArtifactKey
    relation: str
    target: ArtifactKey | str
    description: str | None
    json_pointer: str


def iter_canonical_references(
    document: SourceDocument,
) -> Iterator[CanonicalReference]:
    repository_id = document.provenance.origin.repository_id
    for artifact_index, artifact in enumerate(document.artifacts):
        source = ArtifactKey(
            repository_id=repository_id, artifact_id=artifact.id
        )
        for index, relationship in enumerate(artifact.relationships):
            target = relationship.target
            yield CanonicalReference(
                source=source,
                relation=relationship.relation.value,
                target=(
                    target.key()
                    if isinstance(target, ArtifactTarget)
                    else target.target_uri
                ),
                description=relationship.description,
                json_pointer=f"/artifacts/{artifact_index}/relationships/{index}/target",
            )
        if isinstance(artifact, DesignDocument):
            for component_index, component in enumerate(artifact.components):
                for dependency_index, dependency in enumerate(component.dependencies):
                    yield CanonicalReference(
                        source=source,
                        relation="depends_on",
                        target=dependency,
                        description=None,
                        json_pointer=(
                            f"/artifacts/{artifact_index}/components/{component_index}"
                            f"/dependencies/{dependency_index}"
                        ),
                    )
        if isinstance(artifact, TestPlan):
            for case_index, test_case in enumerate(artifact.test_cases):
                for target_index, verified_target in enumerate(test_case.verifies):
                    yield CanonicalReference(
                        source=source,
                        relation="verifies",
                        target=verified_target,
                        description=None,
                        json_pointer=(
                            f"/artifacts/{artifact_index}/test_cases/{case_index}"
                            f"/verifies/{target_index}"
                        ),
                    )


__all__ = ["CanonicalReference", "iter_canonical_references"]
