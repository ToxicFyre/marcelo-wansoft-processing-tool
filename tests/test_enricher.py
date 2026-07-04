"""Enricher regression tests on real scenario slices."""

from __future__ import annotations

from tests.helpers import enrich_scenario


def test_cafe_refill_regular() -> None:
    enriched = enrich_scenario("cafe_refill_regular.csv")
    base = enriched.loc[~enriched["is_modifier"].astype(bool)]
    assert "cafe refill regular" in set(base["item"].str.lower())


def test_cafe_refill_descafeinado() -> None:
    enriched = enrich_scenario("cafe_refill_descafeinado.csv")
    base = enriched.loc[~enriched["is_modifier"].astype(bool)]
    assert "cafe refill descafeinado" in set(base["item"].str.lower())


def test_chilaquiles_excludes_egg_modifier() -> None:
    enriched = enrich_scenario("chilaquiles_salsa_verde_with_egg.csv")
    base = enriched.loc[~enriched["is_modifier"].astype(bool)]
    rows = base.loc[
        base["original_item"].astype(str).str.upper() == "CHILAQUILES PANEM"
    ]
    name = rows.iloc[0]["item"].lower()
    assert "salsa verde" in name
    assert "huevo" not in name


def test_concha_vainilla_instore() -> None:
    enriched = enrich_scenario("concha_vainilla_passthrough.csv")
    base = enriched.loc[~enriched["is_modifier"].astype(bool)]
    assert "concha vainilla" in set(base["item"].str.lower())
