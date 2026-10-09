"""Data ingestion module for Recon."""

from recon.ingestion.models import IngestionConfig, RawDataset
from recon.ingestion.csv_loader import load_csv, calculate_file_hash, detect_file_encoding
from recon.ingestion.json_loader import load_json, flatten_json_record, extract_records_from_json
from recon.ingestion.loader import load_dataset

__all__ = [
    "IngestionConfig",
    "RawDataset",
    "load_csv",
    "load_json",
    "load_dataset",
    "calculate_file_hash",
    "detect_file_encoding",
    "flatten_json_record",
    "extract_records_from_json",
]
