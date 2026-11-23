"""Generates 5 diverse, production-grade test suites for Recon integration testing.

Each suite contains:
1. Source raw dataset in a specific format (CSV, Excel XLSX, JSONL, TSV, Multi-Table CSVs).
2. Target schema contract in standard JSON Schema format.
3. Scenario documentation and expected outcomes.
"""

from pathlib import Path
import json
import csv
import openpyxl

BASE_DIR = Path("D:/recon/demo_test_suites")
BASE_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_contract(c: dict) -> dict:
    """Ensures each field dictionary contains the required 'name' key."""
    for field_name, field_def in c.get("fields", {}).items():
        if "name" not in field_def:
            field_def["name"] = field_name
    return c



# ==============================================================================
# SUITE 1: Healthcare & Clinical Encounters (CSV -> Strict HIPAA-style Schema)
# ==============================================================================
suite1_dir = BASE_DIR / "01_healthcare_encounters_csv"
suite1_dir.mkdir(parents=True, exist_ok=True)

# Contract 1
contract_1 = {
    "contract_name": "healthcare_patient_encounter_contract",
    "version": "1.0.0",
    "description": "Standard schema for hospital patient admission and outpatient clinical encounters.",
    "fields": {
        "encounter_id": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "pattern": r"^ENC-[0-9]{6}$",
            "description": "Unique alphanumeric encounter identifier format ENC-######"
        },
        "patient_id": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "description": "Master patient index (MPI) identifier"
        },
        "admission_date": {
            "target_type": "datetime",
            "required": True,
            "nullable": False,
            "description": "Admission timestamp in ISO 8601 format"
        },
        "discharge_date": {
            "target_type": "datetime",
            "required": False,
            "nullable": True,
            "description": "Discharge timestamp if patient has been released"
        },
        "encounter_type": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "allowed_values": ["Inpatient", "Outpatient", "Emergency", "Urgent Care"],
            "description": "Clinical encounter classification"
        },
        "primary_icd10": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "pattern": r"^[A-Z][0-9]{2}(\.[0-9]{1,4})?$",
            "description": "Primary diagnosis ICD-10-CM code"
        },
        "total_billed_amount": {
            "target_type": "float",
            "required": True,
            "nullable": False,
            "description": "Total hospital billed charges in USD"
        },
        "copay_collected": {
            "target_type": "float",
            "required": False,
            "nullable": True,
            "description": "Upfront patient copay collected at triage"
        },
        "readmission_flag": {
            "target_type": "boolean",
            "required": True,
            "nullable": False,
            "description": "Flag indicating 30-day unplanned readmission"
        }
    }
}
with open(suite1_dir / "target_contract_healthcare.json", "w", encoding="utf-8") as f:
    json.dump(_normalize_contract(contract_1), f, indent=2)

# Source CSV 1 (25 records: 20 clean, 5 with realistic faults)
csv1_rows = [
    ["VisitRef", "PatMPI", "AdmitTime", "ReleaseTime", "VisitClass", "DiagCode", "GrossBilledUSD", "CopayUSD", "Is30dReadmit"],
    ["ENC-100001", "PT-88301", "2024-03-01T08:30:00Z", "2024-03-04T14:00:00Z", "Inpatient", "I10", "14500.50", "250.00", "false"],
    ["ENC-100002", "PT-94812", "2024-03-01T09:15:00Z", "2024-03-01T11:45:00Z", "Outpatient", "J02.9", "450.00", "25.00", "false"],
    ["ENC-100003", "PT-11204", "2024-03-01T11:00:00Z", "2024-03-01T18:20:00Z", "Emergency", "S52.501A", "3800.75", "100.00", "true"],
    ["ENC-100004", "PT-30918", "2024-03-02T07:45:00Z", "2024-03-06T12:00:00Z", "Inpatient", "E11.9", "18200.00", "500.00", "false"],
    ["ENC-100005", "PT-44821", "2024-03-02T13:20:00Z", "", "Inpatient", "K21.9", "9200.00", "0.00", "false"],
    ["ENC-100006", "PT-66102", "2024-03-03T10:10:00Z", "2024-03-03T12:30:00Z", "Urgent Care", "R05", "650.00", "50.00", "false"],
    ["ENC-100007", "PT-77123", "2024-03-03T14:00:00Z", "2024-03-03T16:00:00Z", "Outpatient", "Z00.00", "320.00", "20.00", "false"],
    ["ENC-100008", "PT-55291", "2024-03-04T02:15:00Z", "2024-03-04T08:00:00Z", "Emergency", "R10.9", "2400.00", "75.00", "false"],
    ["ENC-100009", "PT-99384", "2024-03-04T09:30:00Z", "2024-03-07T11:00:00Z", "Inpatient", "M54.5", "12800.25", "300.00", "true"],
    ["ENC-100010", "PT-22910", "2024-03-05T15:45:00Z", "2024-03-05T17:15:00Z", "Outpatient", "H10.9", "280.00", "15.00", "false"],
    ["ENC-100011", "PT-13924", "2024-03-06T08:00:00Z", "2024-03-08T16:30:00Z", "Inpatient", "J18.9", "16400.00", "400.00", "false"],
    ["ENC-100012", "PT-88192", "2024-03-06T11:30:00Z", "2024-03-06T13:00:00Z", "Urgent Care", "T14.90", "550.00", "45.00", "false"],
    ["ENC-100013", "PT-49201", "2024-03-07T06:45:00Z", "2024-03-07T14:20:00Z", "Emergency", "N39.0", "1950.00", "60.00", "false"],
    ["ENC-100014", "PT-73819", "2024-03-07T10:00:00Z", "2024-03-10T12:00:00Z", "Inpatient", "A41.9", "27500.00", "750.00", "true"],
    ["ENC-100015", "PT-31049", "2024-03-08T09:00:00Z", "2024-03-08T10:30:00Z", "Outpatient", "L03.90", "410.00", "30.00", "false"],
    # 5 Intentional Quarantine Faults:
    ["INVALID_ID_999", "PT-99991", "2024-03-08T14:00:00Z", "2024-03-08T16:00:00Z", "Outpatient", "I10", "500.00", "25.00", "false"], # Fault: Bad encounter regex
    ["ENC-100017", "", "2024-03-09T08:30:00Z", "2024-03-09T10:00:00Z", "Urgent Care", "J02.9", "450.00", "20.00", "false"], # Fault: Missing required patient_id
    ["ENC-100018", "PT-55219", "not_a_valid_date", "2024-03-09T18:00:00Z", "Emergency", "R10.9", "2100.00", "50.00", "false"], # Fault: Corrupted admit date
    ["ENC-100019", "PT-66381", "2024-03-10T09:00:00Z", "2024-03-10T11:00:00Z", "Telehealth_Unapproved", "Z00.00", "300.00", "15.00", "false"], # Fault: Invalid enum
    ["ENC-100020", "PT-77291", "2024-03-10T11:30:00Z", "2024-03-10T14:00:00Z", "Inpatient", "12345_BAD_ICD", "12000.00", "200.00", "false"], # Fault: Bad ICD regex
]
with open(suite1_dir / "source_healthcare_encounters.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(csv1_rows)


# ==============================================================================
# SUITE 2: E-Commerce & Retail Orders (Excel XLSX -> Shopify/Stripe Order Schema)
# ==============================================================================
suite2_dir = BASE_DIR / "02_ecommerce_orders_excel"
suite2_dir.mkdir(parents=True, exist_ok=True)

contract_2 = {
    "contract_name": "ecommerce_order_fulfillment_contract",
    "version": "1.0.0",
    "description": "Standard schema for retail shopping orders, payment capture, and delivery fulfillment.",
    "fields": {
        "order_id": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "pattern": r"^ORD-[0-9]{5}$",
            "description": "Standard order identifier"
        },
        "customer_email": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "description": "Purchaser email address"
        },
        "order_date": {
            "target_type": "datetime",
            "required": True,
            "nullable": False,
            "description": "Timestamp of order placement"
        },
        "order_status": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "allowed_values": ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"],
            "description": "Fulfillment lifecycle state"
        },
        "item_count": {
            "target_type": "integer",
            "required": True,
            "nullable": False,
            "description": "Total quantity of items in the order"
        },
        "order_total": {
            "target_type": "float",
            "required": True,
            "nullable": False,
            "description": "Final order amount in USD"
        },
        "shipping_country": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "allowed_values": ["US", "CA", "GB", "DE", "FR", "IN", "AU"],
            "description": "Two-letter ISO 3166-1 country code"
        },
        "is_priority_shipping": {
            "target_type": "boolean",
            "required": True,
            "nullable": False,
            "description": "Express or priority shipping selected"
        }
    }
}
with open(suite2_dir / "target_contract_ecommerce.json", "w", encoding="utf-8") as f:
    json.dump(_normalize_contract(contract_2), f, indent=2)

wb = openpyxl.Workbook()
# Tabular sheet 1: Summary Dashboard (to test multi-sheet detection)
ws_dash = wb.active
ws_dash.title = "Executive_Summary"
ws_dash.append(["MONTHLY PERFORMANCE DASHBOARD", "Q1 2024", ""])
ws_dash.append(["Total Revenue", "$1,450,290", "Target Met: 104%"])
ws_dash.append(["Average Order Value", "$124.50", "+5.2% YoY"])
ws_dash.append([])

# Tabular sheet 2: Raw Orders (where actual data resides)
ws_orders = wb.create_sheet(title="Orders_Data")
excel_headers = ["OrderID", "ClientEmail", "PurchasedAt", "FulfillmentState", "UnitsBought", "TotalCostUSD", "DestCountry", "ExpressFlag"]
ws_orders.append(excel_headers)

orders_data = [
    ["ORD-50001", "sarah.j@example.com", "2024-03-01 10:14:22", "Delivered", 2, 89.90, "US", "true"],
    ["ORD-50002", "marcus.k@company.co.uk", "2024-03-01 11:30:15", "Shipped", 1, 45.00, "GB", "false"],
    ["ORD-50003", "ananya.r@mail.in", "2024-03-01 14:05:00", "Delivered", 5, 230.50, "IN", "true"],
    ["ORD-50004", "jean.dupont@paris.fr", "2024-03-02 08:22:45", "Processing", 3, 149.99, "FR", "false"],
    ["ORD-50005", "h.weber@berlin.de", "2024-03-02 12:40:10", "Delivered", 1, 35.00, "DE", "false"],
    ["ORD-50006", "liam.smith@toronto.ca", "2024-03-03 09:18:30", "Shipped", 4, 180.00, "CA", "true"],
    ["ORD-50007", "chloe.b@sydney.au", "2024-03-03 16:55:00", "Pending", 2, 95.20, "AU", "false"],
    ["ORD-50008", "david.m@example.com", "2024-03-04 10:02:11", "Delivered", 1, 29.99, "US", "false"],
    ["ORD-50009", "elena.v@example.com", "2024-03-04 13:45:20", "Shipped", 6, 310.00, "US", "true"],
    ["ORD-50010", "r.patel@mumbai.in", "2024-03-05 07:12:00", "Delivered", 2, 110.00, "IN", "false"],
    ["ORD-50011", "oliver.w@oxford.uk", "2024-03-05 15:30:40", "Processing", 1, 65.50, "GB", "false"],
    ["ORD-50012", "clara.m@munich.de", "2024-03-06 11:20:15", "Delivered", 3, 140.00, "DE", "true"],
    # 4 Intentional Faults
    ["BAD-ORDER-ID", "tester@test.com", "2024-03-06 14:00:00", "Pending", 1, 50.00, "US", "false"], # Fault: Bad pattern
    ["ORD-50014", "", "2024-03-07 09:10:00", "Shipped", 2, 75.00, "CA", "false"], # Fault: Missing email
    ["ORD-50015", "bob@example.com", "2024-03-07 10:20:00", "LostInTransit", 1, 40.00, "US", "false"], # Fault: Unknown status enum
    ["ORD-50016", "alex@example.com", "2024-03-08 11:00:00", "Delivered", 2, 80.00, "BRAZIL_INVALID", "false"], # Fault: Bad country enum
]
for r in orders_data:
    ws_orders.append(r)

wb.save(suite2_dir / "source_retail_orders.xlsx")


# ==============================================================================
# SUITE 3: Financial B2B Invoices (JSON Lines -> Peppol/Stripe Standard Invoice)
# ==============================================================================
suite3_dir = BASE_DIR / "03_fintech_b2b_invoices_jsonl"
suite3_dir.mkdir(parents=True, exist_ok=True)

contract_3 = {
    "contract_name": "b2b_vendor_invoice_payable_contract",
    "version": "1.0.0",
    "description": "Standard schema for accounts payable supplier invoices and tax reconciliation.",
    "fields": {
        "invoice_number": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "pattern": r"^INV-[0-9]{5}$",
            "description": "Standard tax invoice identifier"
        },
        "vendor_id": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "description": "Vendor ERP account number"
        },
        "invoice_date": {
            "target_type": "datetime",
            "required": True,
            "nullable": False,
            "description": "Date invoice was issued"
        },
        "due_date": {
            "target_type": "datetime",
            "required": True,
            "nullable": False,
            "description": "Net payment due date"
        },
        "currency": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "allowed_values": ["USD", "EUR", "GBP", "INR"],
            "description": "Three-letter ISO currency code"
        },
        "subtotal": {
            "target_type": "float",
            "required": True,
            "nullable": False,
            "description": "Pre-tax amount"
        },
        "tax_amount": {
            "target_type": "float",
            "required": True,
            "nullable": False,
            "description": "Total calculated tax"
        },
        "total_amount": {
            "target_type": "float",
            "required": True,
            "nullable": False,
            "description": "Gross invoice total due"
        },
        "payment_status": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "allowed_values": ["Unpaid", "Paid", "Partially_Paid", "Overdue", "Disputed"],
            "description": "Payment settlement status"
        }
    }
}
with open(suite3_dir / "target_contract_b2b_invoice.json", "w", encoding="utf-8") as f:
    json.dump(_normalize_contract(contract_3), f, indent=2)

invoices_jsonl = [
    {"InvoiceCode": "INV-70001", "SupplierRef": "VEND-101", "IssueDate": "2024-02-01", "DueDate": "2024-03-01", "BillingCurrency": "USD", "NetSubtotal": 5000.00, "VATAmt": 500.00, "GrossPayable": 5500.00, "SettlementStatus": "Paid"},
    {"InvoiceCode": "INV-70002", "SupplierRef": "VEND-204", "IssueDate": "2024-02-05", "DueDate": "2024-03-05", "BillingCurrency": "EUR", "NetSubtotal": 12000.00, "VATAmt": 2400.00, "GrossPayable": 14400.00, "SettlementStatus": "Unpaid"},
    {"InvoiceCode": "INV-70003", "SupplierRef": "VEND-101", "IssueDate": "2024-02-10", "DueDate": "2024-03-10", "BillingCurrency": "USD", "NetSubtotal": 3400.50, "VATAmt": 340.05, "GrossPayable": 3740.55, "SettlementStatus": "Paid"},
    {"InvoiceCode": "INV-70004", "SupplierRef": "VEND-309", "IssueDate": "2024-02-15", "DueDate": "2024-03-15", "BillingCurrency": "GBP", "NetSubtotal": 8500.00, "VATAmt": 1700.00, "GrossPayable": 10200.00, "SettlementStatus": "Partially_Paid"},
    {"InvoiceCode": "INV-70005", "SupplierRef": "VEND-412", "IssueDate": "2024-02-20", "DueDate": "2024-03-20", "BillingCurrency": "INR", "NetSubtotal": 250000.00, "VATAmt": 45000.00, "GrossPayable": 295000.00, "SettlementStatus": "Paid"},
    {"InvoiceCode": "INV-70006", "SupplierRef": "VEND-204", "IssueDate": "2024-02-25", "DueDate": "2024-03-25", "BillingCurrency": "EUR", "NetSubtotal": 6800.00, "VATAmt": 1360.00, "GrossPayable": 8160.00, "SettlementStatus": "Overdue"},
    {"InvoiceCode": "INV-70007", "SupplierRef": "VEND-515", "IssueDate": "2024-03-01", "DueDate": "2024-04-01", "BillingCurrency": "USD", "NetSubtotal": 14200.00, "VATAmt": 1420.00, "GrossPayable": 15620.00, "SettlementStatus": "Unpaid"},
    {"InvoiceCode": "INV-70008", "SupplierRef": "VEND-101", "IssueDate": "2024-03-05", "DueDate": "2024-04-05", "BillingCurrency": "USD", "NetSubtotal": 4900.00, "VATAmt": 490.00, "GrossPayable": 5390.00, "SettlementStatus": "Unpaid"},
    # 3 Intentional Faults:
    {"InvoiceCode": "BAD_INVOICE_NUM", "SupplierRef": "VEND-999", "IssueDate": "2024-03-06", "DueDate": "2024-04-06", "BillingCurrency": "USD", "NetSubtotal": 1000.00, "VATAmt": 100.00, "GrossPayable": 1100.00, "SettlementStatus": "Unpaid"}, # Fault: Bad regex pattern
    {"InvoiceCode": "INV-70010", "SupplierRef": "VEND-204", "IssueDate": "2024-03-07", "DueDate": "2024-04-07", "BillingCurrency": "YEN_INVALID", "NetSubtotal": 50000.00, "VATAmt": 5000.00, "GrossPayable": 55000.00, "SettlementStatus": "Unpaid"}, # Fault: Invalid currency enum
    {"InvoiceCode": "INV-70011", "SupplierRef": "", "IssueDate": "2024-03-08", "DueDate": "2024-04-08", "BillingCurrency": "EUR", "NetSubtotal": 2000.00, "VATAmt": 400.00, "GrossPayable": 2400.00, "SettlementStatus": "Unpaid"}, # Fault: Missing required supplier ref
]
with open(suite3_dir / "source_vendor_invoices.jsonl", "w", encoding="utf-8") as f:
    for item in invoices_jsonl:
        f.write(json.dumps(item) + "\n")


# ==============================================================================
# SUITE 4: Logistics & Freight Shipping Manifests (TSV -> Global Carrier Schema)
# ==============================================================================
suite4_dir = BASE_DIR / "04_logistics_freight_manifest_tsv"
suite4_dir.mkdir(parents=True, exist_ok=True)

contract_4 = {
    "contract_name": "logistics_freight_dispatch_contract",
    "version": "1.0.0",
    "description": "Standard schema for intermodal freight consignments, weight verification, and hazmat compliance.",
    "fields": {
        "consignment_id": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "pattern": r"^CON-[0-9]{6}$",
            "description": "Unique consignment tracking reference"
        },
        "carrier_code": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "allowed_values": ["FEDEX", "DHL", "UPS", "MAERSK", "DB_SCHENKER"],
            "description": "Accredited freight carrier"
        },
        "dispatch_timestamp": {
            "target_type": "datetime",
            "required": True,
            "nullable": False,
            "description": "Warehouse dock release timestamp"
        },
        "gross_weight_kg": {
            "target_type": "float",
            "required": True,
            "nullable": False,
            "description": "Certified scale weight in kilograms"
        },
        "pallet_count": {
            "target_type": "integer",
            "required": True,
            "nullable": False,
            "description": "Total standardized pallet units"
        },
        "destination_hub": {
            "target_type": "string",
            "required": True,
            "nullable": False,
            "description": "Destination container freight station code"
        },
        "hazardous_material": {
            "target_type": "boolean",
            "required": True,
            "nullable": False,
            "description": "Flag for hazardous cargo requiring placarding"
        }
    }
}
with open(suite4_dir / "target_contract_freight.json", "w", encoding="utf-8") as f:
    json.dump(_normalize_contract(contract_4), f, indent=2)

tsv_rows = [
    ["ShipmentRef\tCarrierName\tDepartureTime\tActualWeightKg\tPallets\tDestStation\tIsHazmat"],
    ["CON-800001\tDHL\t2024-03-01T04:30:00Z\t1250.50\t4\tHUB-FRA\tfalse"],
    ["CON-800002\tFEDEX\t2024-03-01T06:15:00Z\t420.00\t2\tHUB-ORD\tfalse"],
    ["CON-800003\tMAERSK\t2024-03-01T09:00:00Z\t18400.00\t22\tHUB-ROT\ttrue"],
    ["CON-800004\tUPS\t2024-03-02T03:45:00Z\t680.20\t3\tHUB-DFW\tfalse"],
    ["CON-800005\tDB_SCHENKER\t2024-03-02T11:20:00Z\t3400.00\t8\tHUB-SIN\tfalse"],
    ["CON-800006\tDHL\t2024-03-03T05:10:00Z\t890.00\t3\tHUB-LHR\tfalse"],
    ["CON-800007\tFEDEX\t2024-03-03T08:30:00Z\t550.75\t2\tHUB-JFK\tfalse"],
    ["CON-800008\tMAERSK\t2024-03-04T02:00:00Z\t21500.00\t26\tHUB-DXB\ttrue"],
    # 3 Intentional Faults:
    ["INVALID_TRACKING\tDHL\t2024-03-04T07:00:00Z\t400.00\t1\tHUB-FRA\tfalse"], # Fault: Bad pattern
    ["CON-800010\tUNKNOWN_CARRIER_XYZ\t2024-03-04T10:00:00Z\t1200.00\t4\tHUB-LAX\tfalse"], # Fault: Unknown carrier enum
    ["CON-800011\tUPS\tnot_a_valid_date\t350.00\t1\tHUB-ATL\tfalse"], # Fault: Invalid date format
]
with open(suite4_dir / "source_freight_manifest.tsv", "w", encoding="utf-8") as f:
    for line in tsv_rows:
        f.write(line[0] + "\n")


# ==============================================================================
# SUITE 5: Relational Multi-Table (Customers + Orders for Matchmaker testing)
# ==============================================================================
suite5_dir = BASE_DIR / "05_relational_customers_and_orders_multitable"
suite5_dir.mkdir(parents=True, exist_ok=True)

# Master Customers table (Source A)
cust_rows = [
    ["cust_id", "full_name", "email_address", "country_code", "created_at"],
    ["C101", "Emma Watson", "emma@example.com", "GB", "2023-01-15"],
    ["C102", "Rajesh Sharma", "rajesh@example.in", "IN", "2023-02-20"],
    ["C103", "Lucas Dupont", "lucas@example.fr", "FR", "2023-03-10"],
    ["C104", "Sophia Miller", "sophia@example.com", "US", "2023-04-05"],
    ["C105", "Max Schmidt", "max@example.de", "DE", "2023-05-12"],
]
with open(suite5_dir / "table_a_customers_master.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(cust_rows)

# Child Orders table (Source B - Foreign key: customer_ref -> cust_id)
orders_rel_rows = [
    ["order_id", "customer_ref", "order_date", "total_usd", "fulfillment_status"],
    ["ORD-901", "C101", "2024-03-01", "120.00", "Delivered"],
    ["ORD-902", "C101", "2024-03-05", "45.50", "Delivered"],
    ["ORD-903", "C102", "2024-03-02", "310.00", "Shipped"],
    ["ORD-904", "C103", "2024-03-03", "85.20", "Delivered"],
    ["ORD-905", "C104", "2024-03-04", "210.00", "Processing"],
    ["ORD-906", "C104", "2024-03-06", "95.00", "Delivered"],
    ["ORD-907", "C105", "2024-03-07", "140.00", "Shipped"],
]
with open(suite5_dir / "table_b_orders_transactions.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(orders_rel_rows)

# Consolidated Data Warehouse Target Contract
contract_5 = {
    "contract_name": "enterprise_warehouse_orders_contract",
    "version": "1.0.0",
    "description": "Unified analytics warehouse schema consolidating orders and customer attribution.",
    "fields": {
        "order_id": {"target_type": "string", "required": True, "nullable": False, "description": "Unique transaction ID"},
        "customer_id": {"target_type": "string", "required": True, "nullable": False, "description": "Attributed customer ID"},
        "order_date": {"target_type": "datetime", "required": True, "nullable": False, "description": "Transaction date"},
        "total_amount": {"target_type": "float", "required": True, "nullable": False, "description": "Total order amount in USD"},
        "status": {"target_type": "string", "required": True, "nullable": False, "allowed_values": ["Delivered", "Shipped", "Processing", "Cancelled"], "description": "Fulfillment status"}
    }
}
with open(suite5_dir / "target_contract_warehouse.json", "w", encoding="utf-8") as f:
    json.dump(_normalize_contract(contract_5), f, indent=2)


# ==============================================================================
# MASTER README: Documentation for testing
# ==============================================================================
readme_content = """# Recon Integration Test Suites (5 Comprehensive Scenarios)

These benchmark test suites are engineered for verifying Recon's data readiness, schema alignment, and zero-loss quarantine capabilities across diverse file formats and enterprise domains.

---

### Suite Overview

| # | Suite Directory | Raw Source Format | Target Schema | Key Features Tested |
| :---: | :--- | :--- | :--- | :--- |
| **01** | `01_healthcare_encounters_csv/` | **CSV** (`.csv`) | HIPAA Clinical Encounter JSON Schema | Regex patterns (`ENC-######`, ICD-10), ISO-8601 timestamps, enum enforcement, billing float precision. (20 clean rows, 5 intentional quarantine faults). |
| **02** | `02_ecommerce_orders_excel/` | **Excel** (`.xlsx`) | Shopify/Stripe Fulfillment Schema | **Multi-sheet workbook detection** (automatically selects raw orders tab over summary dashboard), currency amounts, country codes, boolean flags. (12 clean, 4 faults). |
| **03** | `03_fintech_b2b_invoices_jsonl/` | **JSON Lines** (`.jsonl`) | Peppol B2B Vendor Invoice Schema | Key-value mapping, currency code enums (`USD`, `EUR`, `GBP`, `INR`), subtotal/tax float calculation, status enums. (8 clean, 3 faults). |
| **04** | `04_logistics_freight_manifest_tsv/` | **Tab-Separated** (`.tsv`) | Global Carrier Dispatch Schema | Automatic tab delimiter detection, carrier enums (`FEDEX`, `DHL`, `UPS`, `MAERSK`), weight in kg, hazmat booleans. (8 clean, 3 faults). |
| **05** | `05_relational_customers_and_orders_multitable/` | **Multi-Table CSVs** | Consolidated Analytics Warehouse Schema | **Multi-Entity Table Matchmaker** (Primary Key / Foreign Key detection `C101` across `table_a_customers_master.csv` and `table_b_orders_transactions.csv`, 1:N cardinality). |

---

### How to Test Any Suite in Recon

1. Open your live Recon application on Render (or localhost:8000).
2. Go to **Stage 01 (Intake Cockpit)**.
3. In **Port 1 (Source Raw Data)**: Upload the `source_*` file from any suite.
4. In **Port 2 (Target Contract)**: Upload the matching `target_contract_*.json` from the same suite.
5. Click **"Run Preflight Assessment"**.
6. Review:
   - **Stage 02 (Profile Matrix):** Observe 100% columnar statistics and type inference.
   - **Stage 03 (Mapping Studio):** See semantic auto-matching and SVG flow lines.
   - **Stage 04 (Risk Radar):** Notice how Recon catches the intentional faults (bad regex patterns, missing required IDs).
   - **Stage 06 & 07 (Validation & Export):** Download both the **Clean Valid Records CSV** and the **Quarantined Records CSV** with exact line-level diagnostic justifications!
"""

with open(BASE_DIR / "README.md", "w", encoding="utf-8") as f:
    f.write(readme_content)

print(f"Successfully generated all 5 test suites in: {BASE_DIR}")
