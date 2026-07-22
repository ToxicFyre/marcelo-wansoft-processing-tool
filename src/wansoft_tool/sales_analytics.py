"""
Purpose:
  Aggregate enriched sales by product and compute 80/20 Pareto splits.

Why is this in this project:
  Marcelo needs top-product analysis without Excel pivot tables.

Inputs:
  Enriched silver DataFrame with item and subtotal_item columns.

Outputs:
  Aggregation table and top/rest split for Pareto 80/20 display.

Side effects:
  None.

Failure behavior:
  Returns empty DataFrames when input has no base-item rows.
"""

from __future__ import annotations

import pandas as pd

from wansoft_tool.ticket_identity import ticket_key


def _base_items(df: pd.DataFrame) -> pd.DataFrame:
    if "is_modifier" in df.columns:
        return df.loc[~df["is_modifier"].astype(bool)].copy()
    return df.copy()


def aggregate_by_item(df: pd.DataFrame) -> pd.DataFrame:
    base = _base_items(df)
    if base.empty:
        return pd.DataFrame(
            columns=[
                "item",
                "quantity",
                "revenue",
                "ticket_count",
                "pct_of_total",
                "cum_pct",
            ]
        )
    base["_ticket_key"] = ticket_key(base)
    qty_col = "quantity" if "quantity" in base.columns else None
    grouped = base.groupby("item", as_index=False).agg(
        revenue=("subtotal_item", "sum"),
        ticket_count=("_ticket_key", "nunique"),
        **({"quantity": (qty_col, "sum")} if qty_col else {}),
    )
    if qty_col is None:
        grouped["quantity"] = 0.0
    total = grouped["revenue"].sum()
    grouped = grouped.sort_values("revenue", ascending=False).reset_index(drop=True)
    if total > 0:
        grouped["pct_of_total"] = grouped["revenue"] / total * 100.0
    else:
        grouped["pct_of_total"] = 0.0
    grouped["cum_pct"] = grouped["pct_of_total"].cumsum()
    return grouped[
        ["item", "quantity", "revenue", "ticket_count", "pct_of_total", "cum_pct"]
    ]


def pareto_80_20(agg: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if agg.empty:
        return agg.copy(), agg.copy()
    top_mask = agg["cum_pct"] <= 80.0
    if not top_mask.any():
        top = agg.iloc[:1].copy()
    else:
        top = agg.loc[top_mask].copy()
        if top["cum_pct"].iloc[-1] < 80.0 and len(top) < len(agg):
            next_idx = len(top)
            top = pd.concat([top, agg.iloc[[next_idx]]], ignore_index=True)
    rest = agg.loc[~agg.index.isin(top.index)].copy()
    return top, rest
