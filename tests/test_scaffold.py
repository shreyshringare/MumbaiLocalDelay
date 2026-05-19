"""Smoke tests: verify all packages import correctly."""


def test_polars_import() -> None:
    import polars as pl

    df = pl.DataFrame({"a": [1, 2, 3]})
    assert len(df) == 3


def test_duckdb_import() -> None:
    import duckdb

    result = duckdb.sql("SELECT 42 AS answer").fetchone()
    assert result is not None
    assert result[0] == 42


def test_httpx_import() -> None:
    import httpx

    assert httpx.__version__ is not None


def test_polars_version() -> None:
    import polars as pl

    major = int(pl.__version__.split(".")[0])
    assert major >= 1, f"Need Polars >=1.0, got {pl.__version__}"
