"""Data models for deterministic dataset profiling."""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class InferredType(str, Enum):
    """Inferred primitive or semantic type for a column."""
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    STRING = "string"


class ColumnProfile(BaseModel):
    """Deterministic profile statistics for a single dataset column."""
    name: str
    inferred_type: InferredType
    total_count: int
    null_count: int
    null_percentage: float
    distinct_count: int
    min_value: Any | None = None
    max_value: Any | None = None
    sample_values: list[str] = Field(default_factory=list)
    is_constant: bool = False
    has_whitespace_anomalies: bool = False
    format_patterns: list[str] = Field(default_factory=list)
    type_distribution: dict[str, int] = Field(default_factory=dict)


class SourceProfile(BaseModel):
    """Complete deterministic profile of an ingested source dataset."""
    source_name: str
    fingerprint: str
    total_rows: int
    total_columns: int
    duplicate_rows_count: int
    columns: dict[str, ColumnProfile]
    profiling_timestamp: datetime = Field(default_factory=datetime.utcnow)
    skipped_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def get_column(self, name: str) -> ColumnProfile | None:
        """Retrieves profile for a specific column by name."""
        return self.columns.get(name)
