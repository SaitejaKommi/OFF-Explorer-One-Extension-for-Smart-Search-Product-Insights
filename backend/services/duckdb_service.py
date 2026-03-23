"""
duckdb_service.py
-----------------
Manages a DuckDB connection and executes parameterised queries against
Open Food Facts parquet datasets.

The parquet files are expected at the path defined by settings.parquet_glob.
On first use the service registers the parquet glob as a view named `products`.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import duckdb

from backend.config import settings

logger = logging.getLogger(__name__)

# Columns we always SELECT (keeps memory usage low on wide parquet files)
PRODUCT_COLUMNS = [
    "code",
    "product_name",
    "categories_tags",
    "labels_tags",
    "nutriscore_grade",
    "nova_group",
    "energy_kcal_100g",
    "proteins_100g",
    "fat_100g",
    "saturated_fat_100g",
    "sugars_100g",
    "fiber_100g",
    "salt_100g",
    "carbohydrates_100g",
    "countries_tags",
    "allergens_tags",
]


class DuckDBService:
    """
    Thin wrapper around a DuckDB connection.
    Thread-safe via a single shared in-process connection (DuckDB supports this).
    """

    def __init__(self) -> None:
        self._con: duckdb.DuckDBPyConnection | None = None

    def _get_con(self) -> duckdb.DuckDBPyConnection:
        if self._con is None:
            self._con = duckdb.connect(settings.duckdb_path)
            self._register_parquet()
        return self._con

    def _register_parquet(self) -> None:
        con = self._con
        assert con is not None
        parquet_glob = settings.parquet_glob
        # Check if any matching files exist; if not, create an empty schema view
        matching = list(Path(".").glob(parquet_glob.replace("data/", "data/")))
        if matching:
            con.execute(
                f"CREATE OR REPLACE VIEW products AS SELECT * FROM read_parquet('{parquet_glob}')"
            )
            logger.info("Registered parquet view from glob: %s (%d files)", parquet_glob, len(matching))
        else:
            # Create an empty stub view so queries don't fail in test/dev mode
            cols = ", ".join(f"NULL::{t} AS {c}" for c, t in _EMPTY_SCHEMA.items())
            con.execute(f"CREATE OR REPLACE VIEW products AS SELECT {cols} WHERE 1=0")
            logger.warning(
                "No parquet files found at '%s'. Using empty stub view.", parquet_glob
            )

    def execute_search(self, where_clauses: list[str], limit: int = 20) -> list[dict[str, Any]]:
        """Execute a product search query and return rows as dicts."""
        con = self._get_con()
        columns = ", ".join(PRODUCT_COLUMNS)
        where = " AND ".join(where_clauses) if where_clauses else "1=1"
        # Always require a non-empty product name
        if where_clauses:
            where = f"(product_name IS NOT NULL AND product_name != '') AND ({where})"
        else:
            where = "product_name IS NOT NULL AND product_name != ''"
        sql = f"SELECT {columns} FROM products WHERE {where} LIMIT {int(limit)}"
        logger.debug("Executing SQL: %s", sql)
        result = con.execute(sql).fetchdf()
        return result.to_dict(orient="records")

    def fetch_product_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        """Fetch a single product by its barcode (code field)."""
        con = self._get_con()
        columns = ", ".join(PRODUCT_COLUMNS)
        # Sanitise: barcode should be numeric only
        safe_barcode = "".join(c for c in barcode if c.isdigit())
        sql = f"SELECT {columns} FROM products WHERE code = '{safe_barcode}' LIMIT 1"
        result = con.execute(sql).fetchdf()
        if result.empty:
            return None
        return result.iloc[0].to_dict()

    def fetch_alternatives(
        self,
        category_like: str,
        exclude_barcode: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Fetch products in the same category, excluding the current product."""
        con = self._get_con()
        columns = ", ".join(PRODUCT_COLUMNS)
        safe_exclude = "".join(c for c in exclude_barcode if c.isdigit())
        sql = (
            f"SELECT {columns} FROM products "
            f"WHERE categories_tags LIKE '%{category_like}%' "
            f"  AND code != '{safe_exclude}' "
            f"  AND product_name IS NOT NULL "
            f"  AND nutriscore_grade IS NOT NULL "
            f"LIMIT {int(limit * 5)}"  # fetch more, rank later
        )
        result = con.execute(sql).fetchdf()
        return result.to_dict(orient="records")

    def close(self) -> None:
        if self._con:
            self._con.close()
            self._con = None


# Stub schema used when no parquet files are present
_EMPTY_SCHEMA: dict[str, str] = {
    "code": "VARCHAR",
    "product_name": "VARCHAR",
    "categories_tags": "VARCHAR",
    "labels_tags": "VARCHAR",
    "nutriscore_grade": "VARCHAR",
    "nova_group": "INTEGER",
    "energy_kcal_100g": "DOUBLE",
    "proteins_100g": "DOUBLE",
    "fat_100g": "DOUBLE",
    "saturated_fat_100g": "DOUBLE",
    "sugars_100g": "DOUBLE",
    "fiber_100g": "DOUBLE",
    "salt_100g": "DOUBLE",
    "carbohydrates_100g": "DOUBLE",
    "countries_tags": "VARCHAR",
    "allergens_tags": "VARCHAR",
}


# Module-level singleton
duckdb_service = DuckDBService()
