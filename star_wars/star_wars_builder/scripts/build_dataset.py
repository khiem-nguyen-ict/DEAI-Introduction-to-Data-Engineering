"""Build cleaned and extended Star Wars dataset outputs."""

from __future__ import annotations

import csv
import sqlite3
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "data" / "seed"
OVERLAY_DIR = ROOT / "data" / "overlays"
DIST_DIR = ROOT / "dist"
CSV_DIR = DIST_DIR / "csv"
PARQUET_DIR = DIST_DIR / "parquet_files"

UNIQUE_KEYS = {
    "battles": ("name", "date"),
    "characters": ("name",),
    "cities": ("name", "planet"),
    "droids": ("name",),
    "events": ("event_name", "date"),
    "films": ("title",),
    "music": ("title", "associated_with"),
    "organizations": ("name",),
    "planets": ("name",),
    "quotes": ("character_name", "quote", "source"),
    "species": ("name",),
    "starships": ("name", "model"),
    "timeline": ("event", "year"),
    "vehicles": ("name", "model"),
    "weapons": ("name", "model"),
}


def normalize(value: str | None) -> str:
    return (value or "").strip().casefold()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def row_key(table_name: str, row: dict[str, str]) -> tuple[str, ...]:
    keys = UNIQUE_KEYS.get(table_name)
    if not keys:
        return tuple(normalize(row.get(column)) for column in row)
    return tuple(normalize(row.get(column)) for column in keys)


def merge_rows(table_name: str, seed_rows: list[dict[str, str]], overlay_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: OrderedDict[tuple[str, ...], dict[str, str]] = OrderedDict()
    for row in seed_rows:
        merged.setdefault(row_key(table_name, row), row)
    for row in overlay_rows:
        key = row_key(table_name, row)
        if key in merged:
            merged[key].update({name: value for name, value in row.items() if value not in ("", None)})
        else:
            merged[key] = row

    rows = list(merged.values())
    if rows and "id" in rows[0]:
        for index, row in enumerate(rows, start=1):
            row["id"] = str(index)
    return rows


def load_table(table_path: Path) -> tuple[str, list[str], list[dict[str, str]]]:
    table_name = table_path.stem
    columns, seed_rows = read_csv(table_path)
    overlay_path = OVERLAY_DIR / table_path.name
    overlay_rows: list[dict[str, str]] = []
    if overlay_path.exists():
        overlay_columns, overlay_rows = read_csv(overlay_path)
        for column in overlay_columns:
            if column not in columns:
                columns.append(column)
    return table_name, columns, merge_rows(table_name, seed_rows, overlay_rows)


def load_new_overlay(table_path: Path) -> tuple[str, list[str], list[dict[str, str]]]:
    table_name = table_path.stem
    columns, rows = read_csv(table_path)
    return table_name, columns, rows


def write_sqlite(tables: dict[str, tuple[list[str], list[dict[str, str]]]]) -> None:
    db_path = DIST_DIR / "star_wars.db"
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as conn:
        for table_name, (columns, rows) in tables.items():
            quoted_columns = ", ".join(f'"{column}" TEXT' for column in columns)
            conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            conn.execute(f'CREATE TABLE "{table_name}" ({quoted_columns})')
            if rows:
                placeholders = ", ".join("?" for _ in columns)
                conn.executemany(
                    f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                    [[row.get(column, "") for column in columns] for row in rows],
                )


def write_optional_parquet_and_duckdb(tables: dict[str, tuple[list[str], list[dict[str, str]]]]) -> None:
    try:
        import pandas as pd
    except ImportError:
        print("pandas is not installed; skipping parquet and duckdb outputs")
        return

    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    frames = {}
    for table_name, (columns, rows) in tables.items():
        frame = pd.DataFrame(rows, columns=columns)
        frames[table_name] = frame
        try:
            frame.to_parquet(PARQUET_DIR / f"{table_name}.parquet", index=False)
        except ImportError:
            print("pyarrow is not installed; skipping parquet outputs")
            break

    try:
        import duckdb
    except ImportError:
        print("duckdb is not installed; skipping duckdb output")
        return

    duckdb_path = DIST_DIR / "star_wars.duckdb"
    if duckdb_path.exists():
        duckdb_path.unlink()
    with duckdb.connect(str(duckdb_path)) as conn:
        for table_name, frame in frames.items():
            conn.register("frame", frame)
            conn.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM frame')
            conn.unregister("frame")


def build() -> None:
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    tables: dict[str, tuple[list[str], list[dict[str, str]]]] = {}

    for seed_path in sorted(SEED_DIR.glob("*.csv")):
        table_name, columns, rows = load_table(seed_path)
        tables[table_name] = (columns, rows)

    for overlay_path in sorted(OVERLAY_DIR.glob("*.csv")):
        if overlay_path.name in {f"{name}.csv" for name in tables}:
            continue
        table_name, columns, rows = load_new_overlay(overlay_path)
        tables[table_name] = (columns, rows)

    for table_name, (columns, rows) in sorted(tables.items()):
        write_csv(CSV_DIR / f"{table_name}.csv", columns, rows)
        print(f"wrote {table_name}: {len(rows)} rows")

    write_sqlite(tables)
    write_optional_parquet_and_duckdb(tables)


if __name__ == "__main__":
    build()
