"""Shared helpers for enrichment regression tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from wansoft_tool.enrichment import enrich_detail
from wansoft_tool.modifier_config import load_modifier_config

FIXTURES = Path(__file__).parent / "fixtures"
SCENARIOS = FIXTURES / "scenarios"
RAW = FIXTURES / "raw"


def load_scenario(name: str) -> pd.DataFrame:
    return pd.read_csv(SCENARIOS / name)


def load_raw_integration() -> pd.DataFrame:
    files = list(RAW.glob("detail_*.csv"))
    if not files:
        raise FileNotFoundError("No integration fixture in tests/fixtures/raw/")
    return pd.read_csv(files[0])


def enrich_scenario(name: str, *, merge_delivery: bool = True) -> pd.DataFrame:
    config = load_modifier_config()
    return enrich_detail(load_scenario(name), config, merge_delivery=merge_delivery)


def revenue_by_order(df: pd.DataFrame) -> pd.Series:
    return df.groupby("order_id")["subtotal_item"].sum()
