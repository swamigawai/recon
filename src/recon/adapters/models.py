"""Data models for generated integration adapters."""

from datetime import datetime
from pydantic import BaseModel, Field


class GeneratedAdapter(BaseModel):
    """Encapsulates generated Python transformation adapter code and metadata."""
    adapter_name: str
    source_fingerprint: str
    contract_name: str
    contract_version: str
    python_code: str
    invalid_record_policy: str = "quarantine"  # 'quarantine' or 'reject'
    generated_at: datetime = Field(default_factory=datetime.utcnow)
