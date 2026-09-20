from __future__ import annotations

import math
from typing import Annotated, Literal, TypeAlias, cast

from pydantic import Field, GetJsonSchemaHandler, JsonValue, StrictBool, StrictFloat, StrictInt, StrictStr, field_validator, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from .base import (
    EXTENSION_KEY_RE,
    ArtifactId,
    ContractModel,
    ExtensionKey,
    NonEmptyText,
    TestCaseId,
    Title,
    reject_non_finite,
)
from .common import (
    ArtifactKey,
    ArtifactRelationship,
    ArtifactType,
    LifecycleStatus,
    Priority,
    SourceLocation,
)

ScalarTarget: TypeAlias = StrictStr | StrictBool | StrictInt | StrictFloat
NumericTarget: TypeAlias = StrictInt | StrictFloat
MeasurementTarget: TypeAlias = ScalarTarget | tuple[NumericTarget, NumericTarget]


class Measurement(ContractModel):
    name: NonEmptyText
    comparator: Literal["eq", "ne", "lt", "lte", "gt", "gte", "range"]
    target: MeasurementTarget
    unit: NonEmptyText | None = None

    @model_validator(mode="after")
    def comparator_target_matrix(self) -> "Measurement":
        target = self.target
        if isinstance(target, tuple):
            if self.comparator != "range" or len(target) != 2:
                raise ValueError("array target is allowed only for range")
            left, right = target
            if isinstance(left, bool) or isinstance(right, bool) or type(left) is not type(right):
                raise ValueError("range endpoints must be homogeneous strict numeric values")
            if any(isinstance(item, float) and not math.isfinite(item) for item in target):
                raise ValueError("range endpoints must be finite")
            if left > right:
                raise ValueError("range lower endpoint may not exceed upper endpoint")
            return self
        if self.comparator == "range":
            raise ValueError("range requires exactly two numeric endpoints")
        if isinstance(target, float) and not math.isfinite(target):
            raise ValueError("measurement target must be finite")
        if self.comparator in {"lt", "lte", "gt", "gte"} and (
            isinstance(target, (str, bool))
        ):
            raise ValueError("ordered comparison requires a numeric target")
        if self.unit is not None and isinstance(target, (str, bool)):
            raise ValueError("unit is valid only for numeric targets")
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        result = handler(schema)
        scalar = {"type": ["string", "integer", "number", "boolean"]}
        numeric = {"type": ["integer", "number"]}
        homogeneous_range = {
            "oneOf": [
                {"type": "array", "prefixItems": [{"type": "integer"}, {"type": "integer"}], "minItems": 2, "maxItems": 2},
                {
                    "type": "array",
                    "prefixItems": [
                        {"type": "number", "not": {"type": "integer"}},
                        {"type": "number", "not": {"type": "integer"}},
                    ],
                    "minItems": 2,
                    "maxItems": 2,
                },
            ]
        }
        result["allOf"] = [
            {
                "if": {
                    "required": ["unit"],
                    "properties": {
                        "comparator": {"enum": ["eq", "ne"]},
                        "unit": {"type": "string"},
                    },
                },
                "then": {"properties": {"target": numeric}},
            },
            {"if": {"properties": {"comparator": {"enum": ["eq", "ne"]}}}, "then": {"properties": {"target": scalar}}},
            {"if": {"properties": {"comparator": {"enum": ["lt", "lte", "gt", "gte"]}}}, "then": {"properties": {"target": numeric}}},
            {"if": {"properties": {"comparator": {"const": "range"}}}, "then": {"properties": {"target": homogeneous_range}}},
        ]
        return result


class DesignComponent(ContractModel):
    name: Title
    responsibility: NonEmptyText
    dependencies: list[ArtifactKey] = Field(default_factory=list)

    @field_validator("dependencies")
    @classmethod
    def unique_sorted_dependencies(cls, value: list[ArtifactKey]) -> list[ArtifactKey]:
        keys = [item.sort_key() for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate component dependency")
        return sorted(value, key=ArtifactKey.sort_key)


class DesignInterface(ContractModel):
    name: Title
    description: NonEmptyText
    participants: list[Title] = Field(min_length=2)


class TestCase(ContractModel):
    id: TestCaseId
    title: Title
    steps: list[NonEmptyText] = Field(min_length=1)
    expected_result: NonEmptyText
    verifies: list[ArtifactKey] = Field(min_length=1)

    @field_validator("verifies")
    @classmethod
    def unique_sorted_verifies(cls, value: list[ArtifactKey]) -> list[ArtifactKey]:
        keys = [item.sort_key() for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate verification key")
        return sorted(value, key=ArtifactKey.sort_key)


class ArtifactBase(ContractModel):
    artifact_type: ArtifactType
    id: ArtifactId
    title: Title
    status: LifecycleStatus
    summary: NonEmptyText | None = None
    relationships: list[ArtifactRelationship] = Field(default_factory=list)
    extensions: dict[ExtensionKey, JsonValue] = Field(
        default_factory=dict,
        json_schema_extra={"propertyNames": {"pattern": EXTENSION_KEY_RE}},
    )
    source_location: SourceLocation | None = None

    @field_validator("relationships")
    @classmethod
    def unique_sorted_relationships(
        cls, value: list[ArtifactRelationship]
    ) -> list[ArtifactRelationship]:
        keys = [item.sort_key() for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate artifact relationship")
        return sorted(value, key=ArtifactRelationship.sort_key)

    @field_validator("extensions")
    @classmethod
    def finite_extensions(cls, value: dict[ExtensionKey, JsonValue]) -> dict[ExtensionKey, JsonValue]:
        return cast(dict[ExtensionKey, JsonValue], reject_non_finite(value))

    @model_validator(mode="after")
    def matching_prefix(self) -> "ArtifactBase":
        expected = {
            ArtifactType.REQUIREMENT: "REQ-",
            ArtifactType.NON_FUNCTIONAL_REQUIREMENT: "NFR-",
            ArtifactType.ARCHITECTURE_DECISION: "ADR-",
            ArtifactType.DESIGN_DOCUMENT: "DES-",
            ArtifactType.TEST_PLAN: "TST-",
        }[self.artifact_type]
        if not self.id.startswith(expected):
            raise ValueError(f"artifact id must use {expected[:-1]} prefix")
        return self


class Requirement(ArtifactBase):
    artifact_type: Literal[ArtifactType.REQUIREMENT]
    statement: NonEmptyText
    acceptance_criteria: list[NonEmptyText] = Field(min_length=1)
    rationale: NonEmptyText | None = None
    priority: Priority | None = None


class NonFunctionalRequirement(ArtifactBase):
    artifact_type: Literal[ArtifactType.NON_FUNCTIONAL_REQUIREMENT]
    statement: NonEmptyText
    quality_attribute: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    measurement: Measurement
    acceptance_criteria: list[NonEmptyText] = Field(min_length=1)
    rationale: NonEmptyText | None = None
    priority: Priority | None = None


class ArchitectureDecision(ArtifactBase):
    artifact_type: Literal[ArtifactType.ARCHITECTURE_DECISION]
    context: NonEmptyText
    decision: NonEmptyText
    consequences: list[NonEmptyText] = Field(min_length=1)
    alternatives: list[NonEmptyText] = Field(default_factory=list)


class DesignDocument(ArtifactBase):
    artifact_type: Literal[ArtifactType.DESIGN_DOCUMENT]
    overview: NonEmptyText
    components: list[DesignComponent] = Field(min_length=1)
    interfaces: list[DesignInterface] = Field(default_factory=list)


class TestPlan(ArtifactBase):
    artifact_type: Literal[ArtifactType.TEST_PLAN]
    objective: NonEmptyText
    scope: NonEmptyText
    test_cases: list[TestCase] = Field(min_length=1)
    entry_criteria: list[NonEmptyText] = Field(default_factory=list)
    exit_criteria: list[NonEmptyText] = Field(default_factory=list)


Artifact = Annotated[
    Requirement
    | NonFunctionalRequirement
    | ArchitectureDecision
    | DesignDocument
    | TestPlan,
    Field(discriminator="artifact_type"),
]


__all__ = [
    "ArchitectureDecision",
    "Artifact",
    "ArtifactBase",
    "DesignComponent",
    "DesignDocument",
    "DesignInterface",
    "Measurement",
    "NonFunctionalRequirement",
    "Requirement",
    "TestCase",
    "TestPlan",
]
