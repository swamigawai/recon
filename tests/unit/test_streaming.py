"""Unit tests for the high-performance chunked streaming engine (Polars/PyArrow/Fallback)."""

import csv
import json
from pathlib import Path
import pytest

from recon.ingestion.streaming import stream_dataset_chunks, stream_dataset_stats


def test_streaming_csv_chunks(tmp_path: Path):
    """Verifies that large CSV files are cleanly streamed in bounded chunks."""
    csv_file = tmp_path / "large_stream.csv"
    total_rows = 15000
    chunk_size = 5000

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "username", "value"])
        for i in range(1, total_rows + 1):
            writer.writerow([str(i), f"user_{i}", str(i * 10)])

    chunks = list(stream_dataset_chunks(csv_file, chunk_size=chunk_size))
    assert len(chunks) == 3
    assert len(chunks[0]) == 5000
    assert len(chunks[1]) == 5000
    assert len(chunks[2]) == 5000
    assert chunks[0][0]["id"] == "1"
    assert chunks[2][-1]["id"] == "15000"

    # Fast stats verification
    stats = stream_dataset_stats(csv_file)
    assert stats["row_count"] == total_rows
    assert "id" in stats["headers"]
    assert "username" in stats["headers"]
    assert "value" in stats["headers"]


def test_streaming_jsonl_chunks(tmp_path: Path):
    """Verifies that line-delimited JSON files stream in bounded chunks."""
    jsonl_file = tmp_path / "stream_data.jsonl"
    total_rows = 1200
    chunk_size = 500

    with open(jsonl_file, "w", encoding="utf-8") as f:
        for i in range(1, total_rows + 1):
            f.write(json.dumps({"record_id": i, "status": "active"}) + "\n")

    chunks = list(stream_dataset_chunks(jsonl_file, chunk_size=chunk_size))
    assert len(chunks) == 3
    assert len(chunks[0]) == 500
    assert len(chunks[1]) == 500
    assert len(chunks[2]) == 200
    assert chunks[0][0]["record_id"] == 1
    assert chunks[2][-1]["record_id"] == 1200
