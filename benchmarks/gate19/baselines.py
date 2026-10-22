"""
Standardized Baseline Implementations for Gate 19 Benchmark.
1. Baseline A: Direct Schema Validation (Validates raw records directly against target contract)
2. Baseline B: Standard Ad-Hoc Python ETL Script (Manual dictionary mapping + python type casts)
"""
import re
from typing import Any, Dict, List
from datetime import datetime

class BaselineDirectSchemaValidator:
    """Baseline A: Direct Schema Validation against raw input."""
    def __init__(self, contract_def: Dict[str, Any]):
        self.contract_def = contract_def
        self.fields = contract_def.get("fields", {})

    def evaluate_batch(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not records:
            return {"valid_count": 0, "rejected_count": 0, "detected_hazards": []}

        valid_records = []
        rejected_records = []
        detected_hazards = []

        for idx, rec in enumerate(records):
            errors = []
            for f_name, f_def in self.fields.items():
                req = f_def.get("required", False)
                nullable = f_def.get("nullable", True)
                t_type = f_def.get("target_type")
                allowed = f_def.get("allowed_values")
                pattern = f_def.get("pattern")

                if req and f_name not in rec:
                    errors.append(f"Missing required field '{f_name}'")
                elif f_name in rec:
                    val = rec[f_name]
                    if val is None or str(val).strip().lower() in ("", "none", "null", "nan"):
                        if not nullable:
                            errors.append(f"Non-nullable field '{f_name}' is null or empty")
                    else:
                        # Type checks
                        val_str = str(val).strip()
                        if t_type == "float":
                            try:
                                float(val_str)
                            except ValueError:
                                errors.append(f"Invalid float for '{f_name}': {val_str}")
                        elif t_type == "integer":
                            try:
                                int(val_str)
                            except ValueError:
                                errors.append(f"Invalid integer for '{f_name}': {val_str}")
                        elif t_type == "datetime":
                            try:
                                datetime.fromisoformat(val_str.replace("Z", "+00:00"))
                            except ValueError:
                                errors.append(f"Invalid datetime for '{f_name}': {val_str}")

                        # Enum checks
                        if allowed and val_str not in allowed:
                            errors.append(f"Value '{val_str}' for '{f_name}' not in allowed domain {allowed}")

                        # Pattern checks
                        if pattern and not re.match(pattern, val_str):
                            errors.append(f"Value '{val_str}' for '{f_name}' does not match pattern '{pattern}'")

            if errors:
                rejected_records.append({"record_index": idx, "errors": errors})
                for e in errors:
                    if e not in detected_hazards:
                        detected_hazards.append(e)
            else:
                valid_records.append(rec)

        return {
            "valid_count": len(valid_records),
            "rejected_count": len(rejected_records),
            "detected_hazards": detected_hazards,
            "can_preflight_map": False,
        }


class BaselineCustomEtlScript:
    """Baseline B: Standard Ad-Hoc Python ETL Script."""
    def __init__(self, mapping_dict: Dict[str, str], contract_def: Dict[str, Any]):
        self.mapping_dict = mapping_dict  # target_field -> source_field
        self.contract_def = contract_def
        self.fields = contract_def.get("fields", {})

    def run(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not records:
            return {"valid_count": 0, "dropped_count": 0, "detected_hazards": [], "crashed": False}

        valid_records = []
        dropped_records = []
        detected_hazards = []
        crashed = False
        crash_reason = None

        # Check required fields mapped
        for f_name, f_def in self.fields.items():
            if f_def.get("required"):
                if f_name not in self.mapping_dict or not self.mapping_dict[f_name]:
                    detected_hazards.append(f"Missing mapping for required field '{f_name}'")
                    crashed = True
                    crash_reason = f"KeyError: Required field '{f_name}' has no mapped source column"
                    break

        if crashed:
            return {
                "valid_count": 0,
                "dropped_count": len(records),
                "detected_hazards": detected_hazards,
                "crashed": True,
                "crash_reason": crash_reason,
            }

        # Process records
        for idx, rec in enumerate(records):
            transformed = {}
            row_failed = False
            for target_field, src_field in self.mapping_dict.items():
                raw_val = rec.get(src_field)
                f_def = self.fields.get(target_field, {})
                t_type = f_def.get("target_type")
                nullable = f_def.get("nullable", True)
                req = f_def.get("required", False)
                allowed = f_def.get("allowed_values")
                pattern = f_def.get("pattern")

                if raw_val is None or str(raw_val).strip().lower() in ("", "null", "none", "nan"):
                    if req and not nullable:
                        row_failed = True
                        detected_hazards.append(f"Null passed into non-nullable '{target_field}'")
                        break
                    transformed[target_field] = None
                    continue

                val_str = str(raw_val).strip()

                try:
                    if t_type == "float":
                        transformed[target_field] = float(val_str)
                    elif t_type == "integer":
                        transformed[target_field] = int(val_str)
                    elif t_type == "datetime":
                        transformed[target_field] = datetime.fromisoformat(val_str.replace("Z", "+00:00")).isoformat()
                    else:
                        transformed[target_field] = val_str
                except (ValueError, TypeError) as exc:
                    row_failed = True
                    detected_hazards.append(f"Cast failure on '{target_field}': {exc}")
                    break

                if allowed and val_str not in allowed:
                    row_failed = True
                    detected_hazards.append(f"Enum mismatch on '{target_field}': '{val_str}' not in {allowed}")
                    break

                if pattern and not re.match(pattern, val_str):
                    row_failed = True
                    detected_hazards.append(f"Pattern violation on '{target_field}': does not match {pattern}")
                    break

            if row_failed:
                dropped_records.append(rec)
            else:
                valid_records.append(transformed)

        return {
            "valid_count": len(valid_records),
            "dropped_count": len(dropped_records),
            "detected_hazards": list(set(detected_hazards)),
            "crashed": False,
            "crash_reason": None,
        }
