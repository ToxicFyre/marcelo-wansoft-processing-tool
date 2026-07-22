"""Behavioral tests for cross-sell Streamlit view formatting.

These cover the pure formatting helpers so operative copy and column layout
are protected without mocking Streamlit widgets.
"""

from __future__ import annotations

import pandas as pd

from wansoft_tool.streamlit_views import (
    _display_cross_sell_table,
    _rule_card_content,
)


def _rule(**overrides: object) -> pd.Series:
    base: dict[str, object] = {
        "antecedent": "pain au chocolat",
        "consequent": "oreja natural",
        "antecedent_tickets": 170,
        "co_tickets": 17,
        "confidence": 0.10,
        "base_rate": 0.036,
        "lift": 2.97,
        "confidence_lower_bound": 0.072,
        "eligible": True,
    }
    base.update(overrides)
    return pd.Series(base)


def test_display_table_surfaces_product_ticket_totals() -> None:
    rules = pd.DataFrame(
        [
            _rule(),
            _rule(consequent="croissant de berries", co_tickets=13, confidence=0.081),
        ]
    )

    table = _display_cross_sell_table(rules)

    assert list(table.columns) == [
        "ofrecer",
        "tickets del producto",
        "tickets con ambos",
        "confianza",
        "frecuencia base",
        "afinidad",
        "piso seguro",
    ]
    assert "cuando compran" not in table.columns
    assert table["tickets del producto"].iloc[0] == 170
    assert table["tickets con ambos"].iloc[0] == 17
    assert table["confianza"].iloc[0] == "10.0%"


def test_display_table_confidence_matches_ratio_of_ticket_columns() -> None:
    rules = pd.DataFrame(
        [_rule(antecedent_tickets=200, co_tickets=20, confidence=0.10)]
    )

    table = _display_cross_sell_table(rules)

    both = table["tickets con ambos"].iloc[0]
    total = table["tickets del producto"].iloc[0]
    assert both / total == 0.10
    assert table["confianza"].iloc[0] == "10.0%"


def test_rule_card_confidence_line_includes_product_ticket_count() -> None:
    content = _rule_card_content(
        _rule(
            antecedent="concha chocolate",
            consequent="concha vainilla",
            antecedent_tickets=290,
            confidence=0.403,
            lift=3.24,
            confidence_lower_bound=0.357,
        )
    )

    assert content["confidence_value"] == "40.3%"
    assert content["confidence_detail"] == "de esos 290 tickets"
    assert "3.24×" in content["lift_delta"]


def test_rule_card_flags_reliable_pairs_in_plain_language() -> None:
    eligible = _rule_card_content(_rule(eligible=True))
    weak = _rule_card_content(_rule(eligible=False))

    assert "piso seguro" in eligible["evidence"]
    assert "17 tickets con ambos" in eligible["evidence"]
    assert "por encima de lo normal" in eligible["evidence"]
    assert "por encima de lo normal" not in weak["evidence"]
