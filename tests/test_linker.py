"""Linker regression tests on real Wansoft silver tickets."""

from __future__ import annotations

from tests.helpers import enrich_scenario, load_scenario, revenue_by_order


def test_non_adjacent_modifier_revenue_unchanged() -> None:
    raw = load_scenario("non_adjacent_modifier.csv")
    enriched = enrich_scenario("non_adjacent_modifier.csv")
    assert revenue_by_order(raw).sum() == revenue_by_order(enriched).sum()


def test_non_adjacent_modifier_enriches_cafe_refill() -> None:
    enriched = enrich_scenario("non_adjacent_modifier.csv")
    base = enriched.loc[~enriched["is_modifier"].astype(bool)]
    names = set(base["item"].str.lower())
    assert any("cafe refill" in name for name in names)
