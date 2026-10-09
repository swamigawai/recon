"""Target contract models and validation schema."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, field_validator


class ContractType(str, Enum):
    """Supported target contract data types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"


class TargetField(BaseModel):
    """Specification of an expected target field in the contract."""
    name: str
    target_type: ContractType
    required: bool = True
    nullable: bool = False
    allowed_values: list[str] | None = None
    pattern: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Field name cannot be empty or blank")
        return clean


class TargetContract(BaseModel):
    """Specification of the target system contract."""
    contract_name: str
    version: str = "1.0.0"
    description: str | None = None
    fields: dict[str, TargetField] = Field(default_factory=dict)

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, v: dict[str, TargetField]) -> dict[str, TargetField]:
        if not v:
            raise ValueError("Target contract must declare at least one target field.")
        return v

    def required_field_names(self) -> list[str]:
        """Returns names of all fields where required is True."""
        return [f.name for f in self.fields.values() if f.required]

    def non_nullable_field_names(self) -> list[str]:
        """Returns names of all fields where nullable is False."""
        return [f.name for f in self.fields.values() if not f.nullable]
