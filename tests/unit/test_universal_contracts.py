"""Unit tests for Universal Target Contract Ingestion (JSON Schema Draft-07, 2020-12, OpenAPI 3.x)."""

import json
from pathlib import Path
import pytest

from recon.contracts.fingerprint import compute_contract_fingerprint
from recon.contracts.loader import load_target_contract
from recon.contracts.models import ContractType
from recon.contracts.universal import (
    ContractFormat,
    detect_contract_format,
    parse_json_schema,
    parse_openapi_contract,
    resolve_local_ref,
)
from recon.exceptions import ContractError


def test_native_contract_detection_and_loading() -> None:
    """Verifies existing Native Recon contracts are detected and loaded with stable fingerprint."""
    native_data = {
        "contract_name": "native_order_contract",
        "version": "1.2.0",
        "description": "Standard native order model",
        "fields": {
            "order_id": {
                "name": "order_id",
                "target_type": "string",
                "required": True,
                "pattern": r"^[A-Z0-9-]+$",
            },
            "amount": {
                "name": "amount",
                "target_type": "float",
                "required": True,
                "min_value": 0.0,
            },
        },
    }
    fmt, desc = detect_contract_format(native_data)
    assert fmt == ContractFormat.NATIVE
    assert "Native" in desc

    contract = load_target_contract(native_data)
    assert contract.contract_name == "native_order_contract"
    assert contract.version == "1.2.0"
    assert len(contract.fields) == 2
    assert contract.fields["order_id"].required is True
    assert contract.fields["order_id"].target_type == ContractType.STRING
    assert contract.fields["amount"].target_type == ContractType.FLOAT
    assert len(contract.fingerprint) == 64


def test_json_schema_draft_07_ingestion() -> None:
    """Verifies standard JSON Schema Draft-07 document ingestion."""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "VendorInvoiceDraft07",
        "description": "Enterprise vendor invoice standard",
        "type": "object",
        "required": ["invoice_no", "total_due", "issue_date"],
        "properties": {
            "invoice_no": {
                "type": "string",
                "pattern": "^INV-[0-9]{5}$",
                "description": "Unique invoice tracking code",
            },
            "total_due": {
                "type": "number",
                "minimum": 0.01,
            },
            "line_count": {
                "type": "integer",
                "minimum": 1,
            },
            "issue_date": {
                "type": "string",
                "format": "date-time",
            },
            "status": {
                "type": "string",
                "enum": ["ISSUED", "PAID", "VOID"],
            },
            "memo": {
                "type": "string",
                "nullable": True,
            },
        },
    }

    fmt, _ = detect_contract_format(schema)
    assert fmt == ContractFormat.JSON_SCHEMA_DRAFT_07

    contract = load_target_contract(schema)
    assert contract.contract_name == "VendorInvoiceDraft07"
    assert len(contract.fields) == 6

    # Verify field properties
    inv = contract.fields["invoice_no"]
    assert inv.required is True
    assert inv.target_type == ContractType.STRING
    assert inv.pattern == "^INV-[0-9]{5}$"

    due = contract.fields["total_due"]
    assert due.required is True
    assert due.target_type == ContractType.FLOAT
    assert due.min_value == 0.01

    lines = contract.fields["line_count"]
    assert lines.required is False
    assert lines.target_type == ContractType.INTEGER

    dt = contract.fields["issue_date"]
    assert dt.required is True
    assert dt.target_type == ContractType.DATETIME

    status = contract.fields["status"]
    assert status.required is False
    assert status.allowed_values == ["ISSUED", "PAID", "VOID"]

    memo = contract.fields["memo"]
    assert memo.required is False
    assert memo.nullable is True


def test_json_schema_2020_12_type_unions() -> None:
    """Verifies JSON Schema 2020-12 nullability through type unions (e.g. ['string', 'null'])."""
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CustomerProfile2020",
        "type": "object",
        "required": ["customer_id"],
        "properties": {
            "customer_id": {
                "type": "string",
            },
            "tax_id": {
                "type": ["string", "null"],
                "description": "Optional tax identification number",
            },
            "credit_score": {
                "type": ["integer", "null"],
            },
        },
    }

    fmt, _ = detect_contract_format(schema)
    assert fmt == ContractFormat.JSON_SCHEMA_2020_12

    contract = load_target_contract(schema)
    assert contract.fields["customer_id"].required is True
    assert contract.fields["customer_id"].nullable is False

    assert contract.fields["tax_id"].required is False
    assert contract.fields["tax_id"].nullable is True
    assert contract.fields["tax_id"].target_type == ContractType.STRING

    assert contract.fields["credit_score"].nullable is True
    assert contract.fields["credit_score"].target_type == ContractType.INTEGER


def test_openapi_3_single_schema() -> None:
    """Verifies OpenAPI 3.x document with a single component schema auto-selects model."""
    openapi_doc = {
        "openapi": "3.0.3",
        "info": {
            "title": "Logistics API",
            "version": "2.1.0",
            "description": "Logistics tracking microservice",
        },
        "components": {
            "schemas": {
                "Waybill": {
                    "type": "object",
                    "required": ["waybill_number", "weight_kg"],
                    "properties": {
                        "waybill_number": {"type": "string"},
                        "weight_kg": {"type": "number", "minimum": 0.1},
                        "is_express": {"type": "boolean"},
                    },
                }
            }
        },
    }

    fmt, desc = detect_contract_format(openapi_doc)
    assert fmt == ContractFormat.OPENAPI_3
    assert "OpenAPI 3.0.3" in desc

    contract = load_target_contract(openapi_doc)
    assert contract.contract_name == "Waybill"
    assert contract.version == "2.1.0"
    assert contract.fields["waybill_number"].required is True
    assert contract.fields["weight_kg"].target_type == ContractType.FLOAT
    assert contract.fields["is_express"].target_type == ContractType.BOOLEAN


def test_openapi_3_multi_schema_selection() -> None:
    """Verifies explicit schema model selection when OpenAPI document has multiple schemas."""
    openapi_doc = {
        "openapi": "3.1.0",
        "info": {"title": "E-Commerce Suite", "version": "1.0.0"},
        "components": {
            "schemas": {
                "Customer": {
                    "type": "object",
                    "required": ["cust_id", "email"],
                    "properties": {
                        "cust_id": {"type": "string"},
                        "email": {"type": "string"},
                    },
                },
                "Order": {
                    "type": "object",
                    "required": ["order_id", "total"],
                    "properties": {
                        "order_id": {"type": "string"},
                        "total": {"type": "number"},
                    },
                },
            }
        },
    }

    # Calling without schema_name on multi-schema must raise ContractError requesting selection
    with pytest.raises(ContractError) as exc_info:
        load_target_contract(openapi_doc)
    assert "Multiple schemas found in OpenAPI document" in str(exc_info.value)
    assert "Customer" in str(exc_info.value)
    assert "Order" in str(exc_info.value)

    # Calling with invalid schema name raises error
    with pytest.raises(ContractError) as exc_info:
        load_target_contract(openapi_doc, schema_name="NonExistent")
    assert "Requested schema model 'NonExistent' not found" in str(exc_info.value)

    # Calling with valid schema selection succeeds
    order_contract = load_target_contract(openapi_doc, schema_name="Order")
    assert order_contract.contract_name == "Order"
    assert "order_id" in order_contract.fields
    assert "total" in order_contract.fields
    assert "cust_id" not in order_contract.fields


def test_openapi_local_ref_resolution() -> None:
    """Verifies local $ref resolution across component schemas."""
    openapi_doc = {
        "openapi": "3.0.0",
        "components": {
            "schemas": {
                "Address": {
                    "type": "object",
                    "properties": {
                        "postal_code": {"type": "string", "pattern": "^[0-9]{5,6}$"},
                    },
                },
                "Shipment": {
                    "type": "object",
                    "required": ["tracking_id", "delivery_zip"],
                    "properties": {
                        "tracking_id": {"type": "string"},
                        "delivery_zip": {"$ref": "#/components/schemas/Address/properties/postal_code"},
                    },
                },
            }
        },
    }

    contract = load_target_contract(openapi_doc, schema_name="Shipment")
    assert "delivery_zip" in contract.fields
    zip_field = contract.fields["delivery_zip"]
    assert zip_field.required is True
    assert zip_field.target_type == ContractType.STRING
    assert zip_field.pattern == "^[0-9]{5,6}$"


def test_openapi_circular_ref_detection() -> None:
    """Verifies cycle detection prevents infinite recursion on circular $ref pointers."""
    openapi_doc = {
        "openapi": "3.0.0",
        "components": {
            "schemas": {
                "ModelWithCycle": {
                    "type": "object",
                    "properties": {
                        "item": {"$ref": "#/components/schemas/TypeA"},
                    },
                },
                "TypeA": {"$ref": "#/components/schemas/TypeB"},
                "TypeB": {"$ref": "#/components/schemas/TypeA"},
            }
        },
    }

    with pytest.raises(ContractError) as exc_info:
        load_target_contract(openapi_doc, schema_name="ModelWithCycle")
    assert "Circular $ref reference detected" in str(exc_info.value)


def test_openapi_remote_ref_rejection() -> None:
    """Verifies remote URLs in $ref are rejected for security."""
    openapi_doc = {
        "openapi": "3.0.0",
        "components": {
            "schemas": {
                "InsecureModel": {
                    "type": "object",
                    "properties": {
                        "external": {"$ref": "https://attacker.example.com/schema.json"},
                    },
                }
            }
        },
    }

    with pytest.raises(ContractError) as exc_info:
        load_target_contract(openapi_doc, schema_name="InsecureModel")
    assert "Remote $ref references are forbidden" in str(exc_info.value)


def test_contract_fingerprint_stability() -> None:
    """Verifies that contract fingerprint is deterministic and invariant to field key declaration order."""
    c1 = {
        "contract_name": "TestFingerprint",
        "version": "1.0.0",
        "fields": {
            "alpha": {"name": "alpha", "target_type": "string", "required": True},
            "beta": {"name": "beta", "target_type": "integer", "required": False},
        },
    }
    c2 = {
        "contract_name": "TestFingerprint",
        "version": "1.0.0",
        "fields": {
            "beta": {"name": "beta", "target_type": "integer", "required": False},
            "alpha": {"name": "alpha", "target_type": "string", "required": True},
        },
    }

    contract1 = load_target_contract(c1)
    contract2 = load_target_contract(c2)

    assert contract1.fingerprint == contract2.fingerprint
    assert len(contract1.fingerprint) == 64


def test_unsupported_nested_type_raises_actionable_error() -> None:
    """Verifies unsupported nested structures (array, object as field type) produce clear diagnostics."""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "NestedSchema",
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
    }
    with pytest.raises(ContractError) as exc_info:
        load_target_contract(schema)
    assert "Complex nested type 'array' on field 'tags' is not supported" in str(exc_info.value)
    assert "scalar types" in exc_info.value.actionable_suggestion
