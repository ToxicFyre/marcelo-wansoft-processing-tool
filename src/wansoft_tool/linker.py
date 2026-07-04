"""
Purpose:
  Match modifier rows to parent base items within each ticket.

Why is this in this project:
  Wansoft stores modifiers as separate rows; linking is required before renaming.

Inputs:
  Ticket-ordered rows with item, modifier, is_modifier, clave_platillo.

Outputs:
  Per-row metadata: matched product rule and collected defining modifiers.

Side effects:
  None.

Failure behavior:
  Unmatched modifier rows pass through without parent linkage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from wansoft_tool.modifier_config import (
    ModifierConfig,
    ModifierSpec,
    ProductRule,
    find_product_rule,
)


@dataclass
class BaseState:
    row_index: int
    item: str
    rule_id: str | None = None
    pending_modifiers: list[str] = field(default_factory=list)


def _modifier_matches(spec: ModifierSpec, modifier: str, clave: str) -> bool:
    if spec.clave_platillo and clave.upper() == spec.clave_platillo.upper():
        return True
    if spec.match_modifier and modifier.upper() == spec.match_modifier.upper():
        return True
    return False


def _is_excluded_modifier(
    rule_exclude: list[ModifierSpec],
    modifier: str,
    clave: str,
) -> bool:
    return any(_modifier_matches(spec, modifier, clave) for spec in rule_exclude)


def _is_defining_modifier(
    rule_modifiers: list[ModifierSpec],
    modifier: str,
    clave: str,
) -> bool:
    return any(_modifier_matches(spec, modifier, clave) for spec in rule_modifiers)


def _find_parent_index(
    bases: list[BaseState],
    item: str,
) -> int | None:
    for state in reversed(bases):
        if state.item.upper() == item.upper():
            return state.row_index
    return None


def _register_base_row(
    idx: int,
    item: str,
    clave: str,
    config: ModifierConfig,
    pending_by_row: dict[int, list[str]],
) -> BaseState:
    rule = find_product_rule(config, item, clave)
    pending_by_row[int(idx)] = []
    return BaseState(row_index=int(idx), item=item, rule_id=rule.id if rule else None)


def _maybe_drop_modifier_row(
    idx: int,
    config: ModifierConfig,
    drop_rows: set[int],
) -> None:
    if not config.keep_modifier_rows:
        drop_rows.add(int(idx))


def _resolve_parent_rule(
    bases: list[BaseState],
    item: str,
    config: ModifierConfig,
) -> tuple[int | None, ProductRule | None]:
    parent_idx = _find_parent_index(bases, item)
    if parent_idx is None:
        return None, None
    parent_state = next(s for s in bases if s.row_index == parent_idx)
    rule = next((r for r in config.products if r.id == parent_state.rule_id), None)
    return parent_idx, rule


def _process_modifier_row(
    idx: int,
    row: pd.Series,
    bases: list[BaseState],
    config: ModifierConfig,
    pending_by_row: dict[int, list[str]],
    drop_rows: set[int],
) -> None:
    parent_idx, rule = _resolve_parent_rule(bases, str(row["item"]), config)
    if parent_idx is None or rule is None:
        return
    modifier = str(row.get("modifier", ""))
    mod_clave = str(row["clave_platillo"])
    if _is_excluded_modifier(rule.exclude_modifiers, modifier, mod_clave):
        return
    if not _is_defining_modifier(rule.defining_modifiers, modifier, mod_clave):
        return
    pending_by_row.setdefault(parent_idx, []).append(modifier)
    _maybe_drop_modifier_row(idx, config, drop_rows)


def link_ticket_modifiers(
    ticket_df: pd.DataFrame,
    config: ModifierConfig,
) -> tuple[dict[int, list[str]], set[int]]:
    bases: list[BaseState] = []
    pending_by_row: dict[int, list[str]] = {}
    drop_rows: set[int] = set()
    for idx, row in ticket_df.iterrows():
        item = str(row["item"])
        clave = str(row["clave_platillo"])
        if not bool(row["is_modifier"]):
            state = _register_base_row(idx, item, clave, config, pending_by_row)
            bases = [state]
            continue
        _process_modifier_row(idx, row, bases, config, pending_by_row, drop_rows)
    return pending_by_row, drop_rows
