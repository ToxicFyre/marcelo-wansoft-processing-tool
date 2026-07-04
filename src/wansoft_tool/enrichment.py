"""
Purpose:
  Public API orchestrating modifier enrichment and channel normalization.

Why is this in this project:
  Marcelo and tests need one entry point for the full silver enrichment pass.

Inputs:
  Silver detail DataFrame, ModifierConfig, optional merge_delivery override.

Outputs:
  Enriched DataFrame with canonical item names and audit columns.

Side effects:
  None.

Failure behavior:
  Propagates ValueError from missing required columns.
"""

from __future__ import annotations

import pandas as pd

from wansoft_tool.channels import normalize_delivery_channels
from wansoft_tool.enricher import link_and_enrich_items
from wansoft_tool.modifier_config import ModifierConfig


def enrich_detail(
    df: pd.DataFrame,
    config: ModifierConfig,
    *,
    merge_delivery: bool | None = None,
) -> pd.DataFrame:
    enriched = link_and_enrich_items(df, config)
    merge = config.merge_delivery_channels if merge_delivery is None else merge_delivery
    return normalize_delivery_channels(enriched, config, merge)
