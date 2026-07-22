"""
Purpose:
  Build enriched item names from product rules and linked modifiers.

Why is this in this project:
  Folds item-defining modifiers into canonical product names for analysis.

Inputs:
  Silver detail DataFrame, ModifierConfig, linker pending-modifier map.

Outputs:
  DataFrame with enriched item names on base rows; optional row drops.

Side effects:
  None.

Failure behavior:
  Unconfigured products receive passthrough lowercase names when matched by rules.
"""

from __future__ import annotations

import re

import pandas as pd

from wansoft_tool.detail_columns import normalize_detail_columns, sort_detail_rows
from wansoft_tool.linker import link_ticket_modifiers
from wansoft_tool.modifier_config import ModifierConfig, ProductRule, find_product_rule
from wansoft_tool.name_helpers import extract_concha_flavor, to_output_case
from wansoft_tool.ticket_identity import ticket_key


def _first_modifier(modifiers: list[str]) -> str:
    return modifiers[0] if modifiers else ""


def _apply_template(
    rule: ProductRule,
    item: str,
    modifiers: list[str],
    output_case: str,
) -> str:
    modifier = _first_modifier(modifiers)
    flavor = extract_concha_flavor(item)
    tokens = {
        "modifier_lower": to_output_case(modifier, output_case),
        "flavor_lower": flavor or to_output_case(modifier, output_case),
        "item_lower": to_output_case(item, output_case),
    }
    name = rule.name_template
    for key, value in tokens.items():
        name = name.replace("{" + key + "}", value)
    name = re.sub(r"\s+", " ", name).strip()
    if not modifier and "{modifier_lower}" in rule.name_template:
        base = to_output_case(item, output_case)
        if rule.id == "chilaquiles_panem":
            return re.sub(
                r"\s+(uber|rappi|didi)$", "", base, flags=re.IGNORECASE
            ).strip()
    return to_output_case(name, output_case) if output_case == "lower" else name


def _enrich_base_row_name(
    row: pd.Series,
    rule: ProductRule | None,
    modifiers: list[str],
    config: ModifierConfig,
) -> str:
    item = str(row["item"])
    if rule is None:
        return to_output_case(item, config.output_case)
    return _apply_template(rule, item, modifiers, config.output_case)


def link_and_enrich_items(
    df: pd.DataFrame,
    config: ModifierConfig,
) -> pd.DataFrame:
    work = sort_detail_rows(normalize_detail_columns(df))
    drop_all: set[int] = set()
    enriched_names: dict[int, str] = {}
    grouped = work.groupby(ticket_key(work), sort=False)
    for _, ticket_df in grouped:
        pending, drops = link_ticket_modifiers(ticket_df, config)
        drop_all.update(drops)
        for idx, row in ticket_df.iterrows():
            if bool(row["is_modifier"]):
                continue
            item = str(row["item"])
            clave = str(row["clave_platillo"])
            rule = find_product_rule(config, item, clave)
            mods = pending.get(int(idx), [])
            enriched_names[int(idx)] = _enrich_base_row_name(row, rule, mods, config)
    out = work.drop(index=list(drop_all), errors="ignore").copy()
    for idx, name in enriched_names.items():
        if idx in out.index:
            out.at[idx, "original_item"] = out.at[idx, "item"]
            out.at[idx, "item"] = name
            if config.update_description and "description" in out.columns:
                out.at[idx, "description"] = name
    return out.reset_index(drop=True)
