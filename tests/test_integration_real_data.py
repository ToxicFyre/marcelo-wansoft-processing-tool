"""End-to-end enrichment on full real branch-week silver files."""

from __future__ import annotations

from wansoft_tool.enrichment import enrich_detail
from wansoft_tool.modifier_config import load_modifier_config
from tests.helpers import load_raw_integration


def test_full_file_enrichment_revenue_invariant() -> None:
    raw = load_raw_integration()
    config = load_modifier_config()
    enriched = enrich_detail(raw, config, merge_delivery=True)
    raw_base = raw.loc[~raw["is_modifier"].astype(bool), "subtotal_item"].sum()
    enriched_base = enriched.loc[
        ~enriched["is_modifier"].astype(bool), "subtotal_item"
    ].sum()
    assert abs(raw_base - enriched_base) < 0.01


def test_full_file_preserves_column_count_or_adds_audit() -> None:
    raw = load_raw_integration()
    config = load_modifier_config()
    enriched = enrich_detail(raw, config, merge_delivery=True)
    assert len(enriched.columns) >= len(raw.columns)
    assert "sales_channel" in enriched.columns
    assert "original_item" in enriched.columns


def test_full_file_has_fewer_or_equal_rows_when_dropping_modifiers() -> None:
    raw = load_raw_integration()
    config = load_modifier_config()
    enriched = enrich_detail(raw, config, merge_delivery=True)
    assert len(enriched) <= len(raw)
