"""Data models for adapter validation and isolated test execution."""

from pydantic import BaseModel, Field
from typing import Any


class TestCaseResult(BaseModel):
    """Result of an individual synthetic test case executed against the adapter."""
    test_name: str
    passed: bool
    expected_behavior: str
    actual_behavior: str
    error_message: str | None = None


class ValidationResult(BaseModel):
    """Comprehensive outcome of adapter test execution and target contract validation."""
    adapter_name: str
    contract_name: str
    contract_version: str
    total_input_records: int
    valid_records_count: int
    quarantined_records_count: int
    contract_pass_rate: float
    sample_valid_output: list[dict[str, Any]] = Field(default_factory=list)
    sample_quarantined_records: list[dict[str, Any]] = Field(default_factory=list)
    test_case_results: list[TestCaseResult] = Field(default_factory=list)
    all_tests_passed: bool = False
    is_contract_valid: bool = False

    @property
    def is_ready(self) -> bool:
        """Adapter is ready only if all test cases pass and contract validation succeeds."""
        return self.all_tests_passed and self.is_contract_valid
