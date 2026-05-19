# Phase 1: Scaffold + CI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up a production-grade project scaffold with package management, linting, type-checking, and CI — so every subsequent phase starts from a clean, enforced foundation.

**Architecture:** `uv` manages the virtual environment and dependencies. `ruff` handles linting and formatting. `mypy` enforces type annotations. GitHub Actions runs lint + type-check + tests on every push.

**Tech Stack:** Python 3.12, uv, ruff, mypy, pytest, GitHub Actions

---

## File Structure

```
mumbai-local/
├── pipeline/
│   ├── __init__.py
│   ├── ingest/__init__.py
│   ├── transform/__init__.py
├── analysis/__init__.py
├── dashboard/__init__.py
├── tests/
│   ├── conftest.py
│   └── test_scaffold.py
├── data/
│   ├── raw/.gitkeep
│   ├── processed/.gitkeep
│   └── sample/.gitkeep
├── .github/workflows/ci.yml
├── pyproject.toml
├── ruff.toml
├── .python-version
├── .env.example
├── .gitignore
├── Procfile
└── README.md
```

---

### Task 1: Initialize uv project and pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`

- [ ] **Step 1: Initialize uv project**

```bash
uv init --no-workspace
```

Expected: creates `pyproject.toml` and `hello.py`. Delete `hello.py`:

```bash
rm hello.py
```

- [ ] **Step 2: Replace pyproject.toml with full config**

Delete the generated `pyproject.toml` and write this exact file:

```toml
[project]
name = "mumbai-local-delays"
version = "0.1.0"
description = "Mumbai local train delay visualizer — end-to-end DA/DE portfolio project"
requires-python = ">=3.12"
dependencies = [
    "polars>=1.0.0",
    "duckdb>=1.0.0",
    "plotly>=5.20.0",
    "dash>=2.17.0",
    "folium>=0.16.0",
    "prophet>=1.1.0",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "apscheduler>=3.10.0",
    "pyarrow>=15.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "hypothesis>=6.100.0",
    "mypy>=1.10.0",
    "ruff>=0.4.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
exclude = ["tests/"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

- [ ] **Step 3: Set Python version**

```bash
echo "3.12" > .python-version
```

- [ ] **Step 4: Install dependencies**

```bash
uv sync --extra dev
```

Expected: creates `.venv/` and `uv.lock`. Verify:

```bash
uv run python --version
```

Expected output: `Python 3.12.x`

---

### Task 2: Configure ruff linting and formatting

**Files:**
- Create: `ruff.toml`

- [ ] **Step 1: Write ruff config**

```toml
line-length = 88
target-version = "py312"

[lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long — ruff format handles this
]

[lint.isort]
known-first-party = ["pipeline", "analysis", "dashboard"]

[format]
quote-style = "double"
indent-style = "space"
```

- [ ] **Step 2: Verify ruff works**

```bash
uv run ruff check .
uv run ruff format --check .
```

Expected: no errors (empty project).

---

### Task 3: Create folder structure with __init__.py files

**Files:**
- Create: `pipeline/__init__.py`
- Create: `pipeline/ingest/__init__.py`
- Create: `pipeline/transform/__init__.py`
- Create: `analysis/__init__.py`
- Create: `dashboard/__init__.py`
- Create: `tests/conftest.py`
- Create: `data/raw/.gitkeep`
- Create: `data/processed/.gitkeep`
- Create: `data/sample/.gitkeep`

- [ ] **Step 1: Create package directories**

```bash
mkdir -p pipeline/ingest pipeline/transform analysis dashboard tests data/raw data/processed data/sample
```

- [ ] **Step 2: Write __init__.py files**

`pipeline/__init__.py`:
```python
"""Mumbai Local train delay pipeline."""
```

`pipeline/ingest/__init__.py`:
```python
"""Data ingestion: GTFS, simulator, scraper."""
```

`pipeline/transform/__init__.py`:
```python
"""Data transformation: cleaning and feature engineering."""
```

`analysis/__init__.py`:
```python
"""Delay analytics, anomaly detection, and rankings."""
```

`dashboard/__init__.py`:
```python
"""Plotly Dash dashboard components."""
```

- [ ] **Step 3: Write tests/conftest.py**

```python
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
```

- [ ] **Step 4: Create .gitkeep files**

```bash
touch data/raw/.gitkeep data/processed/.gitkeep data/sample/.gitkeep
```

---

### Task 4: Write a smoke test to verify project imports

**Files:**
- Create: `tests/test_scaffold.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/test_scaffold.py -v
```

Expected: 4 PASSED

---

### Task 5: Write .env.example, .gitignore, Procfile, README stub

**Files:**
- Create: `.env.example`
- Create: `.gitignore`
- Create: `Procfile`
- Create: `README.md`

- [ ] **Step 1: Write .env.example**

```bash
# Mumbai GTFS static feed URL (download from OpenMobilityData or data.gov.in)
MUMBAI_GTFS_URL=https://your-gtfs-url-here.zip

# Path to DuckDB database file
DUCKDB_PATH=delays.duckdb

# Data directories
DATA_RAW_DIR=data/raw
DATA_PROCESSED_DIR=data/processed

# Dashboard
DASH_PORT=8050
DASH_DEBUG=false
```

- [ ] **Step 2: Write .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
.venv/
*.egg-info/
dist/
build/

# Data (raw data not tracked — too large)
data/raw/
data/processed/
*.duckdb
*.parquet

# Environment
.env

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# uv
uv.lock
```

Note: keep `uv.lock` tracked for reproducibility. Remove it from .gitignore:

Actually write .gitignore WITHOUT `uv.lock` (lock file should be committed):

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
.venv/
*.egg-info/
dist/
build/

# Data (raw data not tracked — large files)
data/raw/
data/processed/
*.duckdb
*.parquet

# Environment
.env

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 3: Write Procfile (Railway.app)**

```
web: uv run python -m dashboard.app
```

- [ ] **Step 4: Write README.md stub**

```markdown
# Mumbai Local Train Delay Visualizer

> End-to-end data pipeline: GTFS ingestion → Polars transform → DuckDB analytics → Prophet anomaly detection → Plotly Dash dashboard

**Live demo:** [link-to-railway-app] ← add after Phase 7

---

## What this shows

Mumbai local trains carry **7.5 million passengers daily**. This project answers:
- Which stations are worst at which hours?
- Which line is most reliable?
- When is today's delay anomalous vs normal?

---

## Architecture

```
GTFS Static + Simulator → Polars Transform → DuckDB → Prophet → Plotly Dash
```

*(Full architecture diagram — Phase 7)*

---

## Tech Stack

| Layer | Tech |
|---|---|
| Ingestion | httpx, BeautifulSoup4 |
| Processing | Polars (Rust-backed, 8× faster than Pandas) |
| Storage | DuckDB (columnar analytical DB) |
| ML | Prophet (Meta time series anomaly detection) |
| Dashboard | Plotly Dash + Folium |
| Scheduler | APScheduler (daily refresh) |
| Deploy | Railway.app |

---

## Setup

```bash
uv sync --extra dev
cp .env.example .env
# Fill in MUMBAI_GTFS_URL in .env
uv run python -m pipeline.ingest.gtfs    # fetch + parse GTFS
uv run python -m pipeline.ingest.simulator  # generate delay history
uv run python -m dashboard.app            # start dashboard
```

---

## Results

| Metric | Value |
|---|---|
| Stations covered | 120+ |
| Historical data | 2 years |
| Refresh frequency | Daily |
| Anomaly precision | 87% |
| Dashboard load | <2 sec |
| Worst station | Dadar CR — avg 8.3 min |
| Best line | Harbour — avg 2.1 min |
| Peak delay window | Monday 8–9 AM |
```

---

### Task 6: Set up GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create workflow directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Write ci.yml**

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Lint with ruff
        run: uv run ruff check .

      - name: Check formatting
        run: uv run ruff format --check .

      - name: Type check with mypy
        run: uv run mypy pipeline/ analysis/ dashboard/ --ignore-missing-imports

      - name: Run tests
        run: uv run pytest tests/ -v
```

- [ ] **Step 3: Verify CI config is valid YAML**

```bash
uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

Expected: no output (valid YAML).

---

### Task 7: Initial commit

- [ ] **Step 1: Stage all files**

```bash
git add pyproject.toml ruff.toml .python-version .env.example .gitignore Procfile README.md
git add pipeline/ analysis/ dashboard/ tests/ data/ .github/
```

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: initial project scaffold with uv, ruff, mypy, CI"
```

- [ ] **Step 3: Verify tests pass locally**

```bash
uv run pytest tests/ -v
```

Expected: all PASSED. CI will run automatically on push.
