"""Validate generated Star Wars dataset outputs."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from build_dataset import CSV_DIR, UNIQUE_KEYS, normalize


def validate_table(path: Path) -> list[str]:
    table_name = path.stem
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    errors: list[str] = []

    if not rows:
        errors.append(f"{table_name}: table is empty")
        return errors

    keys = UNIQUE_KEYS.get(table_name)
    if keys:
        counts = Counter(tuple(normalize(row.get(key)) for key in keys) for row in rows)
        duplicates = [key for key, count in counts.items() if count > 1]
        if duplicates:
            errors.append(f"{table_name}: duplicate keys found for {keys}: {duplicates[:5]}")

    if "id" in rows[0]:
        ids = [row.get("id", "") for row in rows]
        expected = [str(index) for index in range(1, len(rows) + 1)]
        if ids != expected:
            errors.append(f"{table_name}: ids are not sequential")

    return errors


def main() -> None:
    errors: list[str] = []
    for path in sorted(CSV_DIR.glob("*.csv")):
        errors.extend(validate_table(path))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    print("validation passed")


if __name__ == "__main__":
    main()
