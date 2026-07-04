"""
Purpose:
  Strip delivery channel tokens and set sales_channel audit column.

Why is this in this project:
  Uber/Rappi/DiDi SKUs must merge with in-store names for menu analysis.

Inputs:
  Enriched base rows with original_item column and ModifierConfig.

Outputs:
  DataFrame with normalized item names and sales_channel values.

Side effects:
  None.

Failure behavior:
  Excluded bundle items keep channel tokens in the final name.
"""

from __future__ import annotations

import re

import pandas as pd

from wansoft_tool.modifier_config import ChannelNormalization, ModifierConfig
from wansoft_tool.name_helpers import to_output_case

CHANNEL_SUFFIX = re.compile(r"\s+(UBER|RAPPI|DIDI)$", re.IGNORECASE)
CHANNEL_PREFIX = re.compile(r"^(UBER|RAPPI|DIDI)\s+", re.IGNORECASE)
GROUP_CHANNEL = re.compile(r"\b(UBER|RAPPI|DIDI)\b", re.IGNORECASE)
CLAVE_CHANNEL = re.compile(
    r"^(UDP|RPD|UD|RD|UC|RC|UCBC|RCBC|UJBF|RJBF|DPD|DC|DR)",
    re.IGNORECASE,
)


def _channel_from_item_name(item: str) -> str | None:
    match = CHANNEL_SUFFIX.search(item) or CHANNEL_PREFIX.search(item)
    return match.group(1).lower() if match else None


def _channel_from_group(group: str) -> str | None:
    match = GROUP_CHANNEL.search(str(group))
    return match.group(1).lower() if match else None


def _channel_from_clave(clave: str) -> str | None:
    if not CLAVE_CHANNEL.match(str(clave)):
        return None
    prefix = str(clave)[:4].upper()
    if prefix.startswith(("UDP", "UD", "UC")):
        return "uber"
    if prefix.startswith(("RPD", "RD", "RC")):
        return "rappi"
    if prefix.startswith(("DPD", "DC", "DR")):
        return "didi"
    return None


def _detect_channel(item: str, group: str, clave: str) -> str:
    return (
        _channel_from_item_name(item)
        or _channel_from_group(group)
        or _channel_from_clave(clave)
        or "in_store"
    )


def _is_excluded_from_strip(name: str, channel_cfg: ChannelNormalization) -> bool:
    upper = name.upper()
    if upper in channel_cfg.exclude_items:
        return True
    if channel_cfg._exclude_pattern and channel_cfg._exclude_pattern.match(upper):
        return True
    return False


def _strip_channel_tokens(name: str, channel_cfg: ChannelNormalization) -> str:
    result = name
    result = re.sub(
        channel_cfg.strip_prefix_regex, "", result, flags=re.IGNORECASE
    ).strip()
    result = re.sub(channel_cfg.strip_regex, "", result, flags=re.IGNORECASE).strip()
    alias = channel_cfg.aliases.get(result.upper())
    return alias if alias else result


def _reinject_channel_name(item: str, original_item: str, channel: str) -> str:
    if channel == "in_store":
        return item
    token = channel.lower()
    lower_item = item.lower()
    if token in lower_item:
        return item
    if original_item.upper().endswith(f" {token.upper()}"):
        return f"{lower_item} {token}"
    return lower_item


def normalize_delivery_channels(
    df: pd.DataFrame,
    config: ModifierConfig,
    merge_delivery: bool,
) -> pd.DataFrame:
    out = df.copy()
    if "sales_channel" not in out.columns:
        out["sales_channel"] = "in_store"
    if "original_item" not in out.columns:
        out["original_item"] = out["item"]
    channel_cfg = config.channel_normalization
    for idx, row in out.iterrows():
        if bool(row.get("is_modifier", False)):
            continue
        item = str(row["item"])
        original = str(row.get("original_item", item))
        group = str(row.get("group", ""))
        clave = str(row.get("clave_platillo", ""))
        channel = _detect_channel(original, group, clave)
        out.at[idx, "sales_channel"] = channel
        if not merge_delivery:
            final = _reinject_channel_name(item, original, channel)
            out.at[idx, "item"] = to_output_case(final, config.output_case)
            continue
        if _is_excluded_from_strip(item, channel_cfg):
            out.at[idx, "item"] = to_output_case(item, config.output_case)
            continue
        stripped = _strip_channel_tokens(item, channel_cfg)
        out.at[idx, "item"] = to_output_case(stripped, config.output_case)
    return out
