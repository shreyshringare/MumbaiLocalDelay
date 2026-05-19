"""Shared test fixtures for Mumbai Local delay project."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_data_dir() -> Path:
    """Path to sample data directory for tests."""
    return Path(__file__).parent.parent / "data" / "sample"


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Temporary directory for test data output."""
    (tmp_path / "raw").mkdir()
    (tmp_path / "processed").mkdir()
    return tmp_path
