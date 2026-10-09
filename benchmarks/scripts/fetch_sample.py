"""Fetch a reproducible 5,000-row real NYC 311 sample from NYC Open Data."""

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv?$limit=5000"
OUTPUT_FILE = Path("D:/recon/benchmarks/fixtures/nyc_311_5k_real.csv")
META_FILE = Path("D:/recon/benchmarks/fixtures/nyc_311_5k_provenance.json")


def fetch_and_save() -> None:
    print(f"Downloading 5,000 real NYC 311 records from {DATA_URL}...")
    req = urllib.request.Request(
        DATA_URL,
        headers={"User-Agent": "Recon-Integrations-Engine/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        content = resp.read()

    # Calculate sha256
    sha256 = hashlib.sha256(content).hexdigest()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "wb") as f:
        f.write(content)

    # Count rows
    lines = content.decode("utf-8", errors="replace").splitlines()
    total_lines = len(lines)
    header = lines[0] if lines else ""

    metadata = {
        "dataset_name": "NYC 311 Service Requests (Real 5k Slice)",
        "source_url": DATA_URL,
        "retrieval_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sha256_fingerprint": sha256,
        "file_size_bytes": len(content),
        "total_lines_including_header": total_lines,
        "estimated_data_rows": total_lines - 1,
        "header_columns_count": len(header.split(",")),
    }

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved {len(content):,} bytes to {OUTPUT_FILE}")
    print(f"SHA-256: {sha256}")
    print(f"Lines: {total_lines}")
    print(f"Provenance saved to {META_FILE}")


if __name__ == "__main__":
    fetch_and_save()
