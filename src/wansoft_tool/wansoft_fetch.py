"""
Purpose:
  Fetch silver detalle de venta from Wansoft via pos-core-etl.

Why is this in this project:
  Marcelo needs live data download without manual Excel exports.

Inputs:
  secrets.env (WS_BASE, WS_USER, WS_PASS), date range, optional branch filter.

Outputs:
  pandas DataFrame at silver item-line grain.

Side effects:
  Loads dotenv, may download bronze Excel and write silver CSV under data/.

Failure behavior:
  Raises EnvironmentError if Wansoft credentials are missing; propagates pos_core errors.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pos_core import DataPaths
from pos_core.sales import core as sales_core

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUCURSALES = REPO_ROOT / "sucursales.json"
DEFAULT_DATA_ROOT = REPO_ROOT / "data"


def load_wansoft_env(env_path: Path | None = None) -> None:
    path = env_path or REPO_ROOT / "secrets.env"
    load_dotenv(path)
    missing = [key for key in ("WS_BASE", "WS_USER", "WS_PASS") if not os.getenv(key)]
    if missing:
        raise EnvironmentError(
            f"Faltan variables en secrets.env: {', '.join(missing)}. "
            "Copia secrets.env.example y pide los valores al administrador."
        )


def list_active_branches(sucursales_path: Path | None = None) -> list[str]:
    import json

    path = sucursales_path or DEFAULT_SUCURSALES
    with path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    return sorted(name for name in raw if not name.endswith("_OLD"))


def fetch_detail_sales(
    start: date,
    end: date,
    *,
    branches: list[str] | None = None,
    mode: str = "force",
    data_root: Path | None = None,
    sucursales_path: Path | None = None,
) -> pd.DataFrame:
    load_wansoft_env()
    root = data_root or DEFAULT_DATA_ROOT
    sucursales = sucursales_path or DEFAULT_SUCURSALES
    paths = DataPaths.from_root(root, sucursales)
    start_s = start.isoformat()
    end_s = end.isoformat()
    df = sales_core.fetch(paths, start_s, end_s, mode=mode)
    if df.empty:
        return df
    if branches and "sucursal" in df.columns:
        # Filter by short branch names appearing in Wansoft sucursal strings
        mask = (
            df["sucursal"]
            .astype(str)
            .apply(lambda s: any(branch.lower() in s.lower() for branch in branches))
        )
        df = df.loc[mask].copy()
    return df
