"""
Purpose:
  Export analysis DataFrames to Excel for Marcelo.

Why is this in this project:
  Marcelo works in Excel and needs one-click downloads from the app.

Inputs:
  pandas DataFrames and output path or bytes buffer.

Outputs:
  .xlsx file bytes or written file on disk.

Side effects:
  Writes Excel file when path is provided.

Failure behavior:
  Propagates openpyxl/pandas errors on invalid data.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Datos") -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()


def write_excel(df: pd.DataFrame, path: Path, sheet_name: str = "Datos") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
