"""
Purpose:
  Derive reliable directional cross-selling rules from enriched sales detail.

Why is this in this project:
  Store managers need evidence-backed products to offer with a selected item.

Inputs:
  Enriched detail rows with product, purchase value, and ticket identity fields.

Outputs:
  Association-rule tables with volume, affinity, uncertainty, and eligibility.

Side effects:
  None.

Failure behavior:
  Raises ValueError for missing columns or invalid analysis parameters.
"""

from __future__ import annotations

from itertools import combinations
from math import ceil
from statistics import NormalDist

import pandas as pd

from wansoft_tool.ticket_identity import ticket_key

RULE_COLUMNS = [
    "antecedent",
    "consequent",
    "period_start",
    "period_end",
    "total_baskets",
    "antecedent_tickets",
    "consequent_tickets",
    "co_tickets",
    "support",
    "confidence",
    "base_rate",
    "lift",
    "leverage",
    "excess_baskets",
    "confidence_lower_bound",
    "conservative_uplift",
    "opportunity_score",
    "eligible",
]
REQUIRED_COLUMNS = ("item", "is_modifier", "subtotal_item")
SORT_COLUMNS = [
    "opportunity_score",
    "leverage",
    "co_tickets",
    "antecedent",
    "consequent",
]
SORT_ASCENDING = [False, False, False, True, True]


def _empty_rules() -> pd.DataFrame:
    return pd.DataFrame(columns=RULE_COLUMNS)


def _validate_input(
    df: pd.DataFrame,
    min_anchor_tickets: int,
    min_pair_tickets: int | None,
    confidence_level: float,
) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing cross-selling columns: {', '.join(missing)}")
    ticket_key(df)
    if min_anchor_tickets < 1:
        raise ValueError("min_anchor_tickets must be at least 1")
    if min_pair_tickets is not None and min_pair_tickets < 1:
        raise ValueError("min_pair_tickets must be at least 1")
    if not 0.5 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between 0.5 and 1.0")


def _purchased_lines(df: pd.DataFrame) -> pd.DataFrame:
    work = df.loc[~df["is_modifier"].astype(bool)].copy()
    revenue = pd.to_numeric(work["subtotal_item"], errors="coerce")
    work = work.loc[revenue > 0].copy()
    if "quantity" in work.columns:
        quantity = pd.to_numeric(work["quantity"], errors="coerce")
        work = work.loc[quantity > 0].copy()
    work["item"] = work["item"].astype(str).str.strip()
    return work.loc[work["item"] != ""]


def _basket_sets(df: pd.DataFrame) -> list[frozenset[str]]:
    purchased = _purchased_lines(df)
    if purchased.empty:
        return []
    purchased["_ticket_key"] = ticket_key(purchased)
    grouped = purchased.groupby("_ticket_key", sort=False)["item"]
    return [frozenset(items) for items in grouped.unique()]


def _period(df: pd.DataFrame) -> tuple[str, str]:
    if "operating_date" not in df.columns or df.empty:
        return "", ""
    dates = pd.to_datetime(df["operating_date"], errors="coerce").dropna()
    if dates.empty:
        return "", ""
    return dates.min().date().isoformat(), dates.max().date().isoformat()


def _count_items_and_pairs(
    baskets: list[frozenset[str]],
) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
    item_counts: dict[str, int] = {}
    pair_counts: dict[tuple[str, str], int] = {}
    for basket in baskets:
        for item in basket:
            item_counts[item] = item_counts.get(item, 0) + 1
        for pair in combinations(sorted(basket), 2):
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
    return item_counts, pair_counts


def _wilson_lower(successes: int, trials: int, confidence_level: float) -> float:
    proportion = successes / trials
    z = NormalDist().inv_cdf(confidence_level)
    z_squared = z * z
    center = proportion + z_squared / (2 * trials)
    spread = z * (
        (proportion * (1 - proportion) + z_squared / (4 * trials)) / trials
    ) ** 0.5
    return (center - spread) / (1 + z_squared / trials)


def _directional_row(
    antecedent: str,
    consequent: str,
    counts: tuple[int, int, int, int],
    period: tuple[str, str],
    thresholds: tuple[int, int, float],
) -> dict[str, object]:
    total, antecedent_n, consequent_n, co_n = counts
    min_anchor, min_pair, confidence_level = thresholds
    support = co_n / total
    confidence = co_n / antecedent_n
    base_rate = consequent_n / total
    lift = confidence / base_rate
    leverage = support - (antecedent_n / total) * base_rate
    lower = _wilson_lower(co_n, antecedent_n, confidence_level)
    uplift = max(0.0, lower - base_rate)
    eligible = (
        antecedent_n >= min_anchor
        and co_n >= min_pair
        and lift > 1.0
        and leverage > 0.0
        and lower > base_rate
    )
    return {
        "antecedent": antecedent,
        "consequent": consequent,
        "period_start": period[0],
        "period_end": period[1],
        "total_baskets": total,
        "antecedent_tickets": antecedent_n,
        "consequent_tickets": consequent_n,
        "co_tickets": co_n,
        "support": support,
        "confidence": confidence,
        "base_rate": base_rate,
        "lift": lift,
        "leverage": leverage,
        "excess_baskets": total * leverage,
        "confidence_lower_bound": lower,
        "conservative_uplift": uplift,
        "opportunity_score": antecedent_n * uplift,
        "eligible": eligible,
    }


def association_rules(
    df: pd.DataFrame,
    *,
    min_anchor_tickets: int = 30,
    min_pair_tickets: int | None = None,
    confidence_level: float = 0.95,
) -> pd.DataFrame:
    """Calculate all observed directional item-pair rules."""
    if df.empty:
        return _empty_rules()
    _validate_input(df, min_anchor_tickets, min_pair_tickets, confidence_level)
    baskets = _basket_sets(df)
    if not baskets:
        return _empty_rules()
    item_counts, pair_counts = _count_items_and_pairs(baskets)
    total = len(baskets)
    pair_floor = min_pair_tickets or max(5, ceil(total * 0.001))
    period = _period(_purchased_lines(df))
    thresholds = (min_anchor_tickets, pair_floor, confidence_level)
    rows = []
    for (left, right), co_n in pair_counts.items():
        rows.append(
            _directional_row(
                left,
                right,
                (total, item_counts[left], item_counts[right], co_n),
                period,
                thresholds,
            )
        )
        rows.append(
            _directional_row(
                right,
                left,
                (total, item_counts[right], item_counts[left], co_n),
                period,
                thresholds,
            )
        )
    return pd.DataFrame(rows, columns=RULE_COLUMNS).sort_values(
        SORT_COLUMNS, ascending=SORT_ASCENDING, ignore_index=True
    )


def top_cross_sell_rules(
    rules: pd.DataFrame,
    *,
    n: int = 3,
    antecedent: str | None = None,
) -> pd.DataFrame:
    """Return the strongest eligible rules, optionally for one anchor item."""
    if rules.empty or n < 1:
        return rules.iloc[0:0].copy()
    candidates = rules.loc[rules["eligible"].astype(bool)].copy()
    if antecedent is not None:
        candidates = candidates.loc[candidates["antecedent"] == antecedent]
    candidates = candidates.sort_values(
        SORT_COLUMNS, ascending=SORT_ASCENDING, ignore_index=True
    )
    if antecedent is not None:
        return candidates.head(n).reset_index(drop=True)
    selected: list[int] = []
    seen_pairs: set[frozenset[str]] = set()
    for index, row in candidates.iterrows():
        pair = frozenset((str(row["antecedent"]), str(row["consequent"])))
        if pair in seen_pairs:
            continue
        selected.append(index)
        seen_pairs.add(pair)
        if len(selected) == n:
            break
    return candidates.loc[selected].reset_index(drop=True)
