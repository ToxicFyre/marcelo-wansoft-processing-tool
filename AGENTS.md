# AGENTS.md

## Overview

`wansoft-tool` is Marcelo's Streamlit app for Wansoft **detalle de venta** analysis: fetch silver data via `pos-core-etl`, enrich product names (modifiers + delivery channels), run 80/20 Pareto, export Excel.

### Key dependency: `pos-core-etl`

`pos-core-etl` (imported as `pos_core`) is installed from GitHub via `pyproject.toml`. Source repo: https://github.com/ToxicFyre/pos-pipeline-core-etl

If the install fails:

```bash
pip install "pos-core-etl @ git+https://github.com/ToxicFyre/pos-pipeline-core-etl.git"
```

**pandas version:** pin `pandas>=1.3.0,<3`. pandas 3 breaks pos-core-etl `sales_cleaner.detect_header_row`.

### Validate

```bash
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check src tests --exclude .venv
ruff format --check src tests --exclude .venv
mypy src
archbrace check src
```

**Gotcha:** pass `--exclude .venv` to Ruff when needed.

### Environment secrets

Copy `secrets.env.example` to `secrets.env`. Required for live Wansoft download
and for regenerating test fixtures:

- `WS_BASE`, `WS_USER`, `WS_PASS`

### Test fixtures (live Wansoft only)

Committed `tests/fixtures/` must be generated with:

```bash
python tests/bootstrap_fixtures.py
```

That calls `pos_core.sales.core.fetch()` — **no copying CSVs from other repos**
and no local fallback when auth fails. `tests/test_fixtures_provenance.py`
enforces this. If bootstrap fails with `login form not found`, fix Wansoft auth;
do not defang tests with offline copies.

Pytest runs offline against the committed fixtures after they are regenerated.

### Run the app

```bash
streamlit run src/wansoft_tool/streamlit_app.py
```

While automatic Wansoft download is unavailable, use **Subir Excel bronze (manual)** in the
sidebar: upload `Detail_*.xlsx` from Wansoft; `bronze_upload.py` runs
`pos_core.etl.staging.sales_cleaner.transform_detalle_ventas()` then the usual enrichment pipeline.
