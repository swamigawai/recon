"""Data models for raw dataset ingestion."""

from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


class IngestionConfig(BaseModel):
    """Configuration options for dataset ingestion."""
    max_file_size_bytes: int = 100 * 1024 * 1024  # 100 MB default ceiling
    max_rows: int | None = None
    strict_row_counts: bool = True  # Reject rows whose column count does not match header count
    encoding: str | None = None  # Explicit encoding override, or None for auto-detection


class RawDataset(BaseModel):
    """Immutable representation of an ingested raw dataset."""
    file_path: str
    file_name: str
    fingerprint: str  # SHA-256 hash of the raw input file
    file_size_bytes: int
    encoding: str
    headers: list[str]
    row_count: int
    rows: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def preview(self, n: int = 5) -> list[dict[str, Any]]:
        """Returns first n rows for preview."""
        return self.rows[:n]
