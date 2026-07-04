"""
Purpose:
  Normalize silver detail DataFrame columns before enrichment.

Why is this in this project:
  pos-core-etl may emit item_key or clave_platillo; we need one canonical column.

Inputs:
  pandas DataFrame from silver CSV or sales_core.fetch.

Outputs:
  DataFrame with clave_platillo and validated required columns.

Side effects:
  None.

Failure behavior:
  Raises ValueError when required columns are missing.
"""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = (
    "item",
    "is_modifier",
    "order_id",
    "subtotal_item",
    "sucursal",
    "operating_date",
)


def normalize_detail_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(missing)}")
    out = df.copy()
    if "clave_platillo" not in out.columns and "item_key" in out.columns:
        out["clave_platillo"] = out["item_key"]
    elif "clave_platillo" not in out.columns:
        out["clave_platillo"] = ""
    out["clave_platillo"] = out["clave_platillo"].fillna("").astype(str)
    out["item"] = out["item"].fillna("").astype(str)
    if "modifier" not in out.columns:
        out["modifier"] = ""
    out["modifier"] = out["modifier"].fillna("").astype(str)
    return out


def sort_detail_rows(df: pd.DataFrame) -> pd.DataFrame:
    sort_cols = ["sucursal", "order_id"]
    if "captured_time" in df.columns:
        return df.sort_values(sort_cols + ["captured_time"], kind="stable")
    return df.sort_values(sort_cols, kind="stable")
