"""
Storage writer — saves scraper results as CSV or JSON.

Handles directory creation, field ordering, and format auto-detection
from filename extension.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.models.base import BaseScrapedItem

_LOG_NAME = "scrapers.storage"


def _ensure_dir(path: Path) -> None:
    """Create directory and all parents if they don't exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


def save_csv(items: Iterable[BaseModel], filename: str | Path) -> Path:
    """
    Write a list of Pydantic models to a CSV file.

    Args:
        items: Iterable of BaseModel instances
        filename: Output file path

    Returns:
        The resolved Path of the file written.
    """
    path = Path(filename).expanduser().resolve()
    _ensure_dir(path)

    items_list = list(items)
    if not items_list:
        _write_empty_csv(path)
        return path

    model = items_list[0]
    fieldnames = list(model.model_fields.keys())

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in items_list:
            row = item.to_csv_dict()
            # Only include known fieldnames
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    return path


def _write_empty_csv(path: Path) -> None:
    """Write a minimal CSV with just the header when no data."""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        f.write("\n")


def save_json(items: Iterable[BaseModel], filename: str | Path, indent: int = 2) -> Path:
    """
    Write a list of Pydantic models to a JSON file.

    Args:
        items: Iterable of BaseModel instances
        filename: Output file path
        indent: JSON indentation spaces (default 2)

    Returns:
        The resolved Path of the file written.
    """
    path = Path(filename).expanduser().resolve()
    _ensure_dir(path)

    data = [item.model_dump(mode="json") for item in items]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)

    return path


def save_any(
    items: Iterable[Any],
    filename: str | Path,
    format: str | None = None,
) -> Path:
    """
    Auto-detect format from filename extension and write accordingly.

    Args:
        items: Iterable of items (Pydantic models or dicts)
        filename: Output file path
        format: Override format ('csv' or 'json'), otherwise inferred from extension

    Returns:
        The resolved Path of the file written.
    """
    path = Path(filename).expanduser().resolve()

    if format is None:
        ext = path.suffix.lower()
        format = "csv" if ext in (".csv",) else "json"

    items_list = list(items)

    # Normalize to Pydantic models if raw dicts are passed
    if items_list and isinstance(items_list[0], dict):
        # We can't determine the model, use raw dict writing
        if format == "csv":
            return _save_dicts_csv(items_list, path)
        else:
            return _save_dicts_json(items_list, path)

    # Use the Pydantic path
    if format == "csv":
        return save_csv(items_list, path)
    else:
        return save_json(items_list, path)


def _save_dicts_csv(rows: list[dict[str, Any]], path: Path) -> Path:
    """Write a list of plain dicts as CSV."""
    if not rows:
        _write_empty_csv(path)
        return path

    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    return path


def _save_dicts_json(rows: list[dict[str, Any]], path: Path) -> Path:
    """Write a list of plain dicts as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return path
