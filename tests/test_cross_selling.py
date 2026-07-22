"""Behavioral tests for ticket-safe cross-selling recommendations."""

from __future__ import annotations

import pandas as pd
import pytest

from wansoft_tool.cross_selling import association_rules, top_cross_sell_rules
from wansoft_tool.enrichment import enrich_detail
from wansoft_tool.modifier_config import load_modifier_config
from wansoft_tool.ticket_identity import ticket_key
from tests.helpers import load_raw_integration


def _rows(baskets: list[list[str]]) -> pd.DataFrame:
    rows = []
    for order_id, items in enumerate(baskets, start=1):
        for item in items:
            rows.append(
                {
                    "sucursal": "CENTRO",
                    "operating_date": "2026-07-01",
                    "order_id": order_id,
                    "item": item,
                    "is_modifier": False,
                    "quantity": 1,
                    "subtotal_item": 10.0,
                }
            )
    return pd.DataFrame(rows)


def test_ticket_key_uses_transaction_id_and_composite_fallback() -> None:
    frame = pd.DataFrame(
        {
            "pdv_txn_id": ["txn-1", None, None],
            "sucursal": ["A", "A", "B"],
            "operating_date": ["2026-01-01", "2026-01-01", "2026-01-01"],
            "order_id": [7, 7, 7],
        }
    )

    keys = ticket_key(frame)

    assert keys.nunique() == 3
    assert keys.iloc[0] == ("pdv_txn_id", "txn-1")
    assert keys.iloc[1] != keys.iloc[2]


def test_association_metrics_are_directional_and_exact() -> None:
    frame = _rows([["cafe", "concha"], ["cafe", "concha"], ["cafe"], ["te"]])

    rules = association_rules(
        frame,
        min_anchor_tickets=1,
        min_pair_tickets=1,
        confidence_level=0.80,
    )
    cafe_concha = rules.query(
        "antecedent == 'cafe' and consequent == 'concha'"
    ).iloc[0]
    concha_cafe = rules.query(
        "antecedent == 'concha' and consequent == 'cafe'"
    ).iloc[0]

    assert cafe_concha["total_baskets"] == 4
    assert cafe_concha["co_tickets"] == 2
    assert cafe_concha["support"] == pytest.approx(0.5)
    assert cafe_concha["confidence"] == pytest.approx(2 / 3)
    assert cafe_concha["base_rate"] == pytest.approx(0.5)
    assert cafe_concha["lift"] == pytest.approx(4 / 3)
    assert cafe_concha["leverage"] == pytest.approx(0.125)
    assert cafe_concha["excess_baskets"] == pytest.approx(0.5)
    assert concha_cafe["confidence"] == pytest.approx(1.0)


def test_baskets_deduplicate_lines_and_exclude_non_purchases() -> None:
    frame = _rows([["cafe", "cafe", "concha"], ["cafe", "te"]])
    frame.loc[len(frame)] = {
        "sucursal": "CENTRO",
        "operating_date": "2026-07-01",
        "order_id": 1,
        "item": "leche",
        "is_modifier": True,
        "quantity": 1,
        "subtotal_item": 5.0,
    }
    frame.loc[len(frame)] = {
        "sucursal": "CENTRO",
        "operating_date": "2026-07-01",
        "order_id": 1,
        "item": "cortesia",
        "is_modifier": False,
        "quantity": 1,
        "subtotal_item": 0.0,
    }
    frame.loc[len(frame)] = {
        "sucursal": "CENTRO",
        "operating_date": "2026-07-01",
        "order_id": 1,
        "item": "anulado",
        "is_modifier": False,
        "quantity": 0,
        "subtotal_item": 20.0,
    }

    rules = association_rules(
        frame,
        min_anchor_tickets=1,
        min_pair_tickets=1,
        confidence_level=0.80,
    )

    assert set(rules["antecedent"]) == {"cafe", "concha", "te"}
    cafe_concha = rules.query(
        "antecedent == 'cafe' and consequent == 'concha'"
    ).iloc[0]
    assert cafe_concha["antecedent_tickets"] == 2
    assert cafe_concha["co_tickets"] == 1


def test_rules_keep_weak_evidence_but_mark_it_ineligible() -> None:
    frame = _rows(
        [["cafe", "concha"]] * 4
        + [["cafe"]] * 6
        + [["concha"]] * 6
        + [["te"]] * 4
    )

    rules = association_rules(frame, min_anchor_tickets=30, min_pair_tickets=5)
    rule = rules.query("antecedent == 'cafe' and consequent == 'concha'").iloc[0]

    assert not bool(rule["eligible"])
    assert top_cross_sell_rules(rules).empty


def test_top_rules_are_deterministic_and_suppress_reverse_pairs() -> None:
    frame = _rows(
        [["cafe", "concha"]] * 40
        + [["cafe", "galleta"]] * 20
        + [["te", "pastel"]] * 35
        + [["solo"]] * 100
    )
    rules = association_rules(
        frame,
        min_anchor_tickets=5,
        min_pair_tickets=5,
        confidence_level=0.80,
    )

    top = top_cross_sell_rules(rules, n=3)

    unordered_pairs = top.apply(
        lambda row: frozenset((row["antecedent"], row["consequent"])), axis=1
    )
    assert unordered_pairs.nunique() == len(top)
    expected = top.sort_values(
        ["opportunity_score", "leverage", "co_tickets", "antecedent", "consequent"],
        ascending=[False, False, False, True, True],
    )
    pd.testing.assert_frame_equal(
        top.reset_index(drop=True),
        expected.reset_index(drop=True),
    )


def test_product_specific_top_rules_retain_direction() -> None:
    frame = _rows(
        [["cafe", "concha"]] * 40
        + [["cafe", "galleta"]] * 30
        + [["cafe"]] * 10
        + [["solo"]] * 100
    )
    rules = association_rules(
        frame,
        min_anchor_tickets=5,
        min_pair_tickets=5,
        confidence_level=0.80,
    )

    top = top_cross_sell_rules(rules, n=3, antecedent="cafe")

    assert set(top["antecedent"]) == {"cafe"}
    assert list(top["consequent"]) == ["concha", "galleta"]


def test_empty_and_missing_columns_have_explicit_contracts() -> None:
    empty = _rows([])
    rules = association_rules(empty)
    assert rules.empty
    assert "eligible" in rules.columns

    with pytest.raises(ValueError, match="subtotal_item"):
        association_rules(pd.DataFrame({"item": ["cafe"], "is_modifier": [False]}))


def test_rules_integrate_with_enriched_wansoft_detail() -> None:
    raw = load_raw_integration()
    enriched = enrich_detail(raw, load_modifier_config(), merge_delivery=True)

    rules = association_rules(enriched)

    assert not rules.empty
    assert rules["eligible"].any()
    assert rules["total_baskets"].nunique() == 1
    assert rules["period_start"].iloc[0] <= rules["period_end"].iloc[0]
