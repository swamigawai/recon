"""Deterministic fingerprinting for target contracts and source schemas."""

import hashlib
import json
from typing import Any

from recon.contracts.models import TargetContract
from recon.profiling.models import SourceProfile


def compute_contract_fingerprint(contract: TargetContract) -> str:
    """Computes a deterministic SHA-256 fingerprint for a TargetContract.

    The fingerprint is invariant to field dictionary insertion order or extraneous formatting.
    """
    canonical_fields = []
    for field_name in sorted(contract.fields.keys()):
        field = contract.fields[field_name]
        allowed = sorted(field.allowed_values) if field.allowed_values is not None else None
        canonical_fields.append({
            "name": field.name,
            "target_type": field.target_type.value,
            "required": field.required,
            "nullable": field.nullable,
            "allowed_values": allowed,
            "pattern": field.pattern,
            "min_value": field.min_value,
            "max_value": field.max_value,
        })

    payload = {
        "contract_name": contract.contract_name,
        "version": contract.version,
        "fields": canonical_fields,
    }
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_source_schema_fingerprint(profile: SourceProfile) -> str:
    """Computes a deterministic SHA-256 fingerprint of the source dataset's column schema.

    Based on column names and inferred data types, invariant to row contents.
    """
    canonical_cols = []
    for col_name in sorted(profile.columns.keys()):
        col_prof = profile.columns[col_name]
        canonical_cols.append({
            "name": col_name,
            "inferred_type": col_prof.inferred_type.value,
        })

    canonical_json = json.dumps(canonical_cols, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
