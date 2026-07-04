"""Channel normalization tests on real delivery scenario slices."""

from __future__ import annotations

import pandas as pd

from tests.helpers import enrich_scenario


def _base_item_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[~df["is_modifier"].astype(bool)]


def _row_by_original(df: pd.DataFrame, item: str) -> pd.Series:
    if "original_item" in df.columns:
        mask = df["original_item"].astype(str).str.upper() == item.upper()
        rows = _base_item_rows(df).loc[mask]
        if not rows.empty:
            return rows.iloc[0]
    rows = _base_item_rows(df).loc[df["item"].astype(str).str.upper() == item.upper()]
    return rows.iloc[0]


def test_concha_uber_chocolate_canonical_name() -> None:
    uber = enrich_scenario("concha_uber_chocolate.csv", merge_delivery=True)
    mask = (uber["original_item"].astype(str).str.upper() == "CONCHA UBER") & ~uber[
        "is_modifier"
    ].astype(bool)
    names = set(uber.loc[mask, "item"].str.lower())
    assert "concha chocolate" in names


def test_concha_rappi_vainilla() -> None:
    enriched = enrich_scenario("concha_rappi_vainilla.csv", merge_delivery=True)
    row = _row_by_original(enriched, "CONCHA RAPPI")
    assert row["item"] == "concha vainilla"


def test_chilaquiles_uber_strips_channel() -> None:
    enriched = enrich_scenario("chilaquiles_uber_salsa_verde.csv", merge_delivery=True)
    row = _row_by_original(enriched, "CHILAQUILES PANEM UBER")
    assert "uber" not in row["item"]
    assert "salsa verde" in row["item"]


def test_bundle_keeps_channel_token() -> None:
    enriched = enrich_scenario("caja_10_conchas_uber.csv", merge_delivery=True)
    row = _row_by_original(enriched, "CAJA 10 CONCHAS UBER")
    assert "uber" in row["item"].lower()


def test_merge_off_keeps_channel_in_name() -> None:
    enriched = enrich_scenario("concha_uber_chocolate.csv", merge_delivery=False)
    mask = (
        enriched["original_item"].astype(str).str.upper() == "CONCHA UBER"
    ) & ~enriched["is_modifier"].astype(bool)
    assert any("uber" in name for name in enriched.loc[mask, "item"].str.lower())


def test_delivery_passthrough_latte() -> None:
    enriched = enrich_scenario("delivery_passthrough_latte.csv", merge_delivery=True)
    row = _row_by_original(enriched, "LATTE 16OZ UBER")
    assert row["item"] == "latte 16oz"
