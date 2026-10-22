"""
Baseline implementations for Gate 18 Comparative Benchmark.
Implements:
1. Baseline A: Direct Schema Validation (jsonschema-style validator on raw records)
2. Baseline B: Typical Custom Ad-Hoc Python ETL Script (dict-based mapping + type casts)
"""
from typing import Any, Dict, List, Tuple
from datetime import datetime

class BaselineDirectSchemaValidator:
    """Baseline A: Direct Schema Validation against raw input.
    Simulates validating unmapped raw data directly with a schema validator.
    """
    def __init__(self, contract_def: Dict[str, Any]):
        self.contract_def = contract_def
        self.fields = contract_def.get("fields", {})

    def evaluate_batch(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validates records directly against target schema."""
        if not records:
            return {"valid_count": 0, "rejected_count": 0, "detected_hazards": [], "data_loss": 0}

        valid_records = []
        rejected_records = []
        detected_hazards = []

        for idx, rec in enumerate(records):
            errors = []
            # Check required fields exist in raw record
            for f_name, f_def in self.fields.items():
                if f_def.get("required") and f_name not in rec:
                    errors.append(f"Missing required field '{f_name}'")
                elif f_name in rec:
                    val = rec[f_name]
                    # Check nullability
                    if val is None and not f_def.get("nullable", True):
                        errors.append(f"Field '{f_name}' cannot be null")
                    # Check allowed values
                    allowed = f_def.get("allowed_values")
                    if allowed and val not in allowed:
                        errors.append(f"Field '{f_name}' value '{val}' not in {allowed}")

            if errors:
                rejected_records.append({"record_index": idx, "errors": errors})
                for err in errors:
                    if err not in detected_hazards:
                        detected_hazards.append(err)
            else:
                valid_records.append(rec)

        return {
            "valid_count": len(valid_records),
            "rejected_count": len(rejected_records),
            "detected_hazards": detected_hazards,
            "can_propose_mappings": False,
            "can_detect_ambiguity": False,
            "can_generate_adapter": False,
            "zero_loss_balanced": True,
        }


class BaselineCustomEtlScript:
    """Baseline B: Typical Custom Ad-Hoc Python Script.
    Simulates a standard hand-rolled integration script written by a developer.
    Typically:
    - Uses a hardcoded mapping dict.
    - Attempts type casting with try/except.
    - Often silently drops unparseable records or crashes on unmapped required fields.
    """
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
                    # In a typical script, missing required mapping crashes or fails
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
                "can_propose_mappings": False,
                "can_detect_ambiguity": False,
                "zero_loss_balanced": False,
            }

        # Process records
        for idx, rec in enumerate(records):
            transformed = {}
            row_failed = False
            for target_field, src_field in self.mapping_dict.items():
                val = rec.get(src_field)
                f_def = self.fields.get(target_field, {})
                t_type = f_def.get("target_type")

                # Try casting
                try:
                    if t_type == "float":
                        val = float(val) if val is not None else None
                    elif t_type == "integer":
                        val = int(val) if val is not None else None
                    elif t_type == "datetime":
                        if val is not None:
                            val = datetime.fromisoformat(val.replace("Z", "+00:00")).isoformat()
                    transformed[target_field] = val
                except (ValueError, TypeError) as e:
                    row_failed = True
                    detected_hazards.append(f"Cast failure on {target_field}: {e}")
                    break

                # Check enum
                allowed = f_def.get("allowed_values")
                if allowed and val not in allowed:
                    row_failed = True
                    detected_hazards.append(f"Enum mismatch on {target_field}: '{val}' not in {allowed}")
                    break

            if row_failed:
                # Custom scripts typically drop the record without balanced quarantine tracking
                dropped_records.append(rec)
            else:
                valid_records.append(transformed)

        return {
            "valid_count": len(valid_records),
            "dropped_count": len(dropped_records),
            "detected_hazards": list(set(detected_hazards)),
            "crashed": False,
            "crash_reason": None,
            "can_propose_mappings": False,
            "can_detect_ambiguity": False,
            "zero_loss_balanced": (len(valid_records) + len(dropped_records) == len(records)),
        }
