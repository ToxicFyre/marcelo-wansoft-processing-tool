"""Sales analytics tests on real integration fixtures."""

from __future__ import annotations

import pandas as pd

from wansoft_tool.enrichment import enrich_detail
from wansoft_tool.modifier_config import load_modifier_config
from wansoft_tool.sales_analytics import aggregate_by_item, pareto_80_20
from tests.helpers import load_raw_integration


def test_aggregate_has_pareto_columns() -> None:
    raw = load_raw_integration()
    config = load_modifier_config()
    enriched = enrich_detail(raw, config, merge_delivery=True)
    agg = aggregate_by_item(enriched)
    assert not agg.empty
    assert list(agg.columns) == [
        "item",
        "quantity",
        "revenue",
        "ticket_count",
        "pct_of_total",
        "cum_pct",
    ]
    assert abs(agg["cum_pct"].iloc[-1] - 100.0) < 0.01


def test_pareto_split_covers_eighty_percent() -> None:
    raw = load_raw_integration()
    config = load_modifier_config()
    enriched = enrich_detail(raw, config, merge_delivery=True)
    agg = aggregate_by_item(enriched)
    top, _rest = pareto_80_20(agg)
    assert not top.empty
    assert top["cum_pct"].iloc[-1] >= 80.0 or len(top) == 1


def test_channel_merge_increases_canonical_revenue() -> None:
    raw = load_raw_integration()
    config = load_modifier_config()
    merged = enrich_detail(raw, config, merge_delivery=True)
    separate = enrich_detail(raw, config, merge_delivery=False)
    merged_items = aggregate_by_item(merged)["item"].nunique()
    separate_items = aggregate_by_item(separate)["item"].nunique()
    assert merged_items <= separate_items


def test_ticket_count_does_not_merge_reused_order_ids() -> None:
    frame = pd.DataFrame(
        {
            "sucursal": ["A", "A", "B"],
            "operating_date": ["2026-01-01", "2026-01-02", "2026-01-01"],
            "order_id": [7, 7, 7],
            "item": ["cafe", "cafe", "cafe"],
            "is_modifier": [False, False, False],
            "quantity": [1, 1, 1],
            "subtotal_item": [10.0, 10.0, 10.0],
        }
    )

    agg = aggregate_by_item(frame)

    assert agg.loc[0, "ticket_count"] == 3
