"""
Purpose:
  Convert manually downloaded Wansoft bronze Excel files to silver DataFrames.

Why is this in this project:
  Automatic Wansoft download may be unavailable; Marcelo can upload Detail_*.xlsx.

Inputs:
  Raw Excel bytes or paths (Wansoft "Detalle de Ventas" export).

Outputs:
  Silver fact_sales_item_line DataFrames from pos_core sales_cleaner.

Side effects:
  Writes temporary files during transform; removes them after processing.

Failure behavior:
  Raises ValueError for empty input or non-Excel files; propagates pos_core errors.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from pos_core.etl.staging.sales_cleaner import transform_detalle_ventas

from wansoft_tool.detail_columns import normalize_detail_columns


def _write_temp_xlsx(content: bytes) -> Path:
    if not content:
        raise ValueError("El archivo Excel está vacío.")
    handle = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    try:
        handle.write(content)
        handle.flush()
        return Path(handle.name)
    finally:
        handle.close()


def bronze_xlsx_to_silver(content: bytes) -> pd.DataFrame:
    if not content:
        raise ValueError("El archivo Excel está vacío.")
    if content[:2] != b"PK":
        raise ValueError(
            "El archivo no parece un Excel válido (.xlsx). "
            "Descarga el reporte Detalle de Ventas desde Wansoft."
        )
    temp_path = _write_temp_xlsx(content)
    try:
        silver = transform_detalle_ventas(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)
    if silver.empty:
        raise ValueError("El Excel no contiene filas de detalle de ventas.")
    return normalize_detail_columns(silver)


def bronze_upload_to_silver(upload: BinaryIO, filename: str) -> pd.DataFrame:
    lower = filename.lower()
    if not lower.endswith((".xlsx", ".xls")):
        raise ValueError("Solo se aceptan archivos Excel bronze (.xlsx).")
    return bronze_xlsx_to_silver(upload.read())


def bronze_uploads_to_silver(uploads: list[tuple[str, BinaryIO]]) -> pd.DataFrame:
    if not uploads:
        raise ValueError("Selecciona al menos un archivo Excel bronze.")
    frames = [bronze_upload_to_silver(handle, name) for name, handle in uploads]
    if len(frames) == 1:
        return frames[0]
    return pd.concat(frames, ignore_index=True)
