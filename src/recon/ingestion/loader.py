"""Unified dataset loader supporting CSV, TSV, and JSON formats."""

from pathlib import Path

from recon.exceptions import IngestionError
from recon.ingestion.csv_loader import load_csv
from recon.ingestion.json_loader import load_json
from recon.ingestion.models import IngestionConfig, RawDataset


def load_dataset(file_path: str | Path, config: IngestionConfig | None = None) -> RawDataset:
    """Loads a source dataset from disk, automatically detecting format (CSV or JSON).

    Raises:
        IngestionError: If the file does not exist, is unsupported, or fails format validation.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".json", ".jsonl"):
        return load_json(path, config=config)
    elif suffix in (".csv", ".tsv", ".txt"):
        return load_csv(path, config=config)
    else:
        # Fallback inspection: attempt JSON first, then CSV
        try:
            return load_json(path, config=config)
        except IngestionError:
            try:
                return load_csv(path, config=config)
            except IngestionError as exc:
                raise IngestionError(
                    f"Unsupported or unrecognized file format for {path.name}",
                    actionable_suggestion="Provide a valid .csv, .tsv, or .json file.",
                    context={"file_path": str(path)},
                ) from exc
