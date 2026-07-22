"""
Purpose:
  Build stable ticket identities for Wansoft detail rows.

Why is this in this project:
  Wansoft order_id values repeat across dates and branches.

Inputs:
  Detail DataFrame with pdv_txn_id or branch, operating date, and order id.

Outputs:
  A Series of tagged tuple keys, one per input row.

Side effects:
  None.

Failure behavior:
  Raises ValueError when no reliable ticket identity can be built.
"""

from __future__ import annotations

import pandas as pd

COMPOSITE_COLUMNS = ("sucursal", "operating_date", "order_id")


def _composite_key(row: pd.Series) -> tuple[object, ...]:
    return ("composite", *(row[column] for column in COMPOSITE_COLUMNS))


def ticket_key(df: pd.DataFrame) -> pd.Series:
    """Return collision-safe ticket keys aligned to ``df.index``."""
    missing = [column for column in COMPOSITE_COLUMNS if column not in df.columns]
    if missing:
        names = ", ".join(missing)
        raise ValueError(f"Missing ticket identity columns: {names}")
    keys: list[tuple[object, ...]] = []
    has_txn_id = "pdv_txn_id" in df.columns
    for _, row in df.iterrows():
        txn_id = row.get("pdv_txn_id") if has_txn_id else None
        if pd.notna(txn_id) and str(txn_id).strip():
            keys.append(("pdv_txn_id", txn_id))
        else:
            keys.append(_composite_key(row))
    return pd.Series(keys, index=df.index, name="_ticket_key", dtype=object)
