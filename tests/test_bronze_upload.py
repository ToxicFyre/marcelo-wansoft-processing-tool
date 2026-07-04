"""Tests for manual bronze Excel upload → silver transform."""

from __future__ import annotations

from pathlib import Path

import pytest

from wansoft_tool.bronze_upload import bronze_xlsx_to_silver
from wansoft_tool.detail_columns import REQUIRED_COLUMNS

SAMPLE_BRONZE = (
    Path(__file__).resolve().parents[2]
    / "Main-ETL-Project"
    / "data"
    / "a_raw"
    / "sales"
    / "downloads-11-17"
    / "Detail_Kavia_2025-11-17_2025-11-23.xlsx"
)


@pytest.mark.skipif(not SAMPLE_BRONZE.exists(), reason="sample bronze xlsx not on disk")
def test_bronze_xlsx_to_silver_has_required_columns() -> None:
    content = SAMPLE_BRONZE.read_bytes()
    silver = bronze_xlsx_to_silver(content)
    assert not silver.empty
    for col in REQUIRED_COLUMNS:
        assert col in silver.columns


def test_bronze_xlsx_rejects_empty_bytes() -> None:
    with pytest.raises(ValueError, match="vacío"):
        bronze_xlsx_to_silver(b"")
