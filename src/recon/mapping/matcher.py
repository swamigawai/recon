"""Multi-Entity Table Matchmaker: Primary/Foreign Key Discovery, Join Compatibility, and Duplicate Detection."""

from enum import Enum
import re
from typing import List, Optional
from pydantic import BaseModel, Field

from recon.profiling.models import SourceProfile, ColumnProfile, InferredType


class JoinCardinality(str, Enum):
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:M"
    UNKNOWN = "UNKNOWN"


class KeyCandidate(BaseModel):
    """A candidate primary-foreign key relationship between two tables."""
    table_a_column: str
    table_b_column: str
    confidence: float
    cardinality: JoinCardinality
    value_overlap_ratio: float
    is_candidate_primary_key_a: bool
    is_candidate_primary_key_b: bool
    match_reasons: List[str] = Field(default_factory=list)


class TableMatchResult(BaseModel):
    """Complete evaluation of whether two tables can be joined or are duplicate."""
    table_a_name: str
    table_b_name: str
    is_identical: bool
    identical_reason: Optional[str] = None
    compatible_for_join: bool
    top_join_key: Optional[KeyCandidate] = None
    candidate_keys: List[KeyCandidate] = Field(default_factory=list)
    recommended_join_type: str = "NONE"  # "INNER", "LEFT", "NONE"
    orphan_risk_percentage: float = 0.0
    summary_message: str


def _normalize_name(name: str) -> str:
    """Normalizes column name for fuzzy semantic comparison."""
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", name.lower())
    # Strip common prefixes/suffixes for cross-system id mapping (e.g. tbl_customer_id -> customer)
    cleaned = re.sub(r"^(tbl|dim|fact|src|tgt)_?", "", cleaned)
    return cleaned


def _calculate_sample_overlap(samples_a: List[str], samples_b: List[str]) -> tuple[float, float]:
    """Calculates Jaccard overlap and containment ratio between two sample sets."""
    set_a = {str(s).strip().lower() for s in samples_a if s is not None and str(s).strip()}
    set_b = {str(s).strip().lower() for s in samples_b if s is not None and str(s).strip()}

    if not set_a or not set_b:
        return 0.0, 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    jaccard = intersection / union if union > 0 else 0.0
    containment = intersection / min(len(set_a), len(set_b)) if min(len(set_a), len(set_b)) > 0 else 0.0
    return jaccard, containment


def _is_primary_key(profile: SourceProfile, col: ColumnProfile) -> bool:
    """Checks if a column is a candidate primary key based on uniqueness and zero nulls."""
    if profile.total_rows <= 0 or col.null_count > 0:
        return False
    if profile.total_rows < 20:
        return col.distinct_count == profile.total_rows
    return (col.distinct_count / profile.total_rows) >= 0.98


def match_tables(profile_a: SourceProfile, profile_b: SourceProfile) -> TableMatchResult:
    """Analyzes two tables to detect join keys, cardinality, compatibility, or duplicate schemas."""
    # 1. Exact Fingerprint Duplicate Check
    if profile_a.fingerprint and profile_a.fingerprint == profile_b.fingerprint:
        return TableMatchResult(
            table_a_name=profile_a.source_name,
            table_b_name=profile_b.source_name,
            is_identical=True,
            identical_reason="Exact cryptographic SHA-256 fingerprint match. Tables are 100% byte-for-byte identical.",
            compatible_for_join=False,
            summary_message="Identical duplicate tables detected. Merging is redundant.",
        )

    # 2. Structural & Content Duplicate Check
    cols_a = {k.lower(): v for k, v in profile_a.columns.items()}
    cols_b = {k.lower(): v for k, v in profile_b.columns.items()}

    if set(cols_a.keys()) == set(cols_b.keys()) and len(cols_a) > 0:
        high_overlap_cols = 0
        for col_name, c_a in cols_a.items():
            c_b = cols_b[col_name]
            _, containment = _calculate_sample_overlap(c_a.sample_values, c_b.sample_values)
            if containment >= 0.8:
                high_overlap_cols += 1

        if high_overlap_cols == len(cols_a):
            return TableMatchResult(
                table_a_name=profile_a.source_name,
                table_b_name=profile_b.source_name,
                is_identical=True,
                identical_reason="All columns share identical names, data types, and record samples.",
                compatible_for_join=False,
                summary_message="Identical tables detected. Every column matches between Table A and Table B.",
            )

    # 3. Candidate Key Discovery
    candidates: List[KeyCandidate] = []

    for name_a, col_a in profile_a.columns.items():
        is_pk_a = _is_primary_key(profile_a, col_a)
        norm_a = _normalize_name(name_a)

        for name_b, col_b in profile_b.columns.items():
            is_pk_b = _is_primary_key(profile_b, col_b)
            norm_b = _normalize_name(name_b)

            confidence = 0.0
            reasons = []

            # Factor A: Name similarity
            if name_a.lower() == name_b.lower():
                confidence += 0.40
                reasons.append(f"Exact column name match '{name_a}'")
            elif norm_a == norm_b or norm_a in norm_b or norm_b in norm_a:
                confidence += 0.30
                reasons.append(f"Fuzzy name similarity ('{name_a}' ≈ '{name_b}')")

            # Factor B: Common key indicators (id, key, code, no, num)
            key_pattern = r"(id|key|code|num|no|pk|fk)$"
            if re.search(key_pattern, norm_a) and re.search(key_pattern, norm_b):
                confidence += 0.15
                reasons.append("Identified identifier tokens (e.g., 'id', 'key', 'code')")

            # Factor C: Type compatibility
            if col_a.inferred_type == col_b.inferred_type:
                confidence += 0.15
                reasons.append(f"Matching data type: {col_a.inferred_type.value}")

            # Factor D: Sample value overlap
            jaccard, containment = _calculate_sample_overlap(col_a.sample_values, col_b.sample_values)
            if containment > 0.0:
                confidence += min(0.30, containment * 0.30)
                reasons.append(f"Sample value containment: {int(containment * 100)}%")

            # Determine Cardinality
            if is_pk_a and is_pk_b:
                cardinality = JoinCardinality.ONE_TO_ONE
            elif is_pk_a and not is_pk_b:
                cardinality = JoinCardinality.ONE_TO_MANY
            elif not is_pk_a and is_pk_b:
                cardinality = JoinCardinality.MANY_TO_ONE
            else:
                cardinality = JoinCardinality.MANY_TO_MANY

            # Threshold for candidacy
            if confidence >= 0.45 or (name_a.lower() == name_b.lower() and (is_pk_a or is_pk_b)):
                candidates.append(
                    KeyCandidate(
                        table_a_column=name_a,
                        table_b_column=name_b,
                        confidence=round(min(confidence, 1.0), 2),
                        cardinality=cardinality,
                        value_overlap_ratio=round(containment, 2),
                        is_candidate_primary_key_a=is_pk_a,
                        is_candidate_primary_key_b=is_pk_b,
                        match_reasons=reasons,
                    )
                )

    # Sort candidates by confidence descending
    candidates.sort(key=lambda c: c.confidence, reverse=True)

    if not candidates:
        return TableMatchResult(
            table_a_name=profile_a.source_name,
            table_b_name=profile_b.source_name,
            is_identical=False,
            compatible_for_join=False,
            summary_message="No compatible join keys found between Table A and Table B.",
        )

    top_key = candidates[0]
    compatible = top_key.confidence >= 0.50

    # Determine recommended join type and orphan risk
    orphan_risk = 0.0
    if top_key.value_overlap_ratio > 0:
        orphan_risk = round(max(0.0, 1.0 - top_key.value_overlap_ratio) * 100, 1)

    rec_join = "INNER" if orphan_risk < 5.0 else "LEFT"

    summary = (
        f"Compatible for {top_key.cardinality.value} JOIN on '{top_key.table_a_column}' = '{top_key.table_b_column}' "
        f"with {int(top_key.confidence * 100)}% confidence."
    )

    return TableMatchResult(
        table_a_name=profile_a.source_name,
        table_b_name=profile_b.source_name,
        is_identical=False,
        compatible_for_join=compatible,
        top_join_key=top_key,
        candidate_keys=candidates[:5],
        recommended_join_type=rec_join,
        orphan_risk_percentage=orphan_risk,
        summary_message=summary,
    )
