"""
tests/conftest.py
-----------------
Shared fixtures for the test suite.
"""
import pytest


@pytest.fixture(autouse=True)
def reset_duckdb_service():
    """Reset the DuckDB singleton between tests to avoid state leakage."""
    from backend.services.duckdb_service import duckdb_service
    duckdb_service.close()
    yield
    duckdb_service.close()
