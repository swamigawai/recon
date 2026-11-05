"""Unified dataset loader supporting CSV, TSV, JSON, and Excel formats."""

from pathlib import Path

from recon.exceptions import IngestionError
from recon.ingestion.csv_loader import load_csv
from recon.ingestion.excel_loader import load_excel
from recon.ingestion.json_loader import load_json
from recon.ingestion.models import IngestionConfig, RawDataset


def load_dataset(file_path: str | Path, config: IngestionConfig | None = None) -> RawDataset:
    """Loads a source dataset from disk, automatically detecting format (CSV, JSON, or Excel).

    Raises:
        IngestionError: If the file does not exist, is unsupported, or fails format validation.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".json", ".jsonl"):
        return load_json(path, config=config)
    elif suffix in (".csv", ".tsv", ".txt"):
        return load_csv(path, config=config)
    elif suffix in (".xlsx", ".xlsm"):
        return load_excel(path, config=config)
    elif suffix == ".xls":
        raise IngestionError(
            f"Legacy Excel (.xls) file format is not supported: {path.name}",
            actionable_suggestion="Convert the legacy .xls workbook to modern .xlsx format in Excel or LibreOffice.",
            context={"file_path": str(path)},
        )
    else:
        # Fallback inspection: attempt JSON first, then CSV, then Excel
        try:
            return load_json(path, config=config)
        except IngestionError:
            try:
                return load_csv(path, config=config)
            except IngestionError:
                try:
                    return load_excel(path, config=config)
                except IngestionError as exc:
                    raise IngestionError(
                        f"Unsupported or unrecognized file format for {path.name}",
                        actionable_suggestion="Provide a valid .csv, .tsv, .json, or .xlsx file.",
                        context={"file_path": str(path)},
                    ) from exc
