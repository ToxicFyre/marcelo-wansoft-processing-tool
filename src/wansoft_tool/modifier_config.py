"""
Purpose:
  Load and validate modifier product YAML configuration.

Why is this in this project:
  Product matching rules must be editable without code changes.

Inputs:
  Path to modifier_products.yaml.

Outputs:
  ModifierConfig dataclass with defaults, channel rules, and product rules.

Side effects:
  Reads YAML file from disk.

Failure behavior:
  Raises FileNotFoundError or ValueError on missing file or invalid schema.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("config/modifier_products.yaml")


@dataclass
class ModifierSpec:
    match_modifier: str | None = None
    clave_platillo: str | None = None


@dataclass
class ProductRule:
    id: str
    match_item: str | None = None
    match_item_regex: str | None = None
    match_clave_platillo: str | None = None
    defining_modifiers: list[ModifierSpec] = field(default_factory=list)
    exclude_modifiers: list[ModifierSpec] = field(default_factory=list)
    multi_defining_policy: str = "first"
    name_template: str = "{item_lower}"
    _item_pattern: re.Pattern[str] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.match_item_regex:
            self._item_pattern = re.compile(self.match_item_regex, re.IGNORECASE)


@dataclass
class ChannelNormalization:
    strip_regex: str = r"\s+(UBER|RAPPI|DIDI)$"
    strip_prefix_regex: str = r"^(UBER|RAPPI|DIDI)\s+"
    exclude_items: list[str] = field(default_factory=list)
    exclude_item_regex: str = ""
    aliases: dict[str, str] = field(default_factory=dict)
    _exclude_pattern: re.Pattern[str] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.exclude_item_regex:
            self._exclude_pattern = re.compile(self.exclude_item_regex, re.IGNORECASE)


@dataclass
class ModifierConfig:
    version: int
    output_case: str
    keep_modifier_rows: bool
    update_description: bool
    merge_delivery_channels: bool
    delivery_channels: list[str]
    channel_normalization: ChannelNormalization
    products: list[ProductRule]


def _parse_modifier_list(raw: list[dict[str, Any]] | None) -> list[ModifierSpec]:
    if not raw:
        return []
    return [
        ModifierSpec(
            match_modifier=item.get("match_modifier"),
            clave_platillo=str(item["clave_platillo"])
            if item.get("clave_platillo")
            else None,
        )
        for item in raw
    ]


def _parse_product(raw: dict[str, Any]) -> ProductRule:
    match = raw.get("match", {})
    return ProductRule(
        id=str(raw["id"]),
        match_item=match.get("item"),
        match_item_regex=match.get("item_regex"),
        match_clave_platillo=match.get("clave_platillo"),
        defining_modifiers=_parse_modifier_list(raw.get("defining_modifiers")),
        exclude_modifiers=_parse_modifier_list(raw.get("exclude_modifiers")),
        multi_defining_policy=raw.get("multi_defining_policy", "first"),
        name_template=raw.get("name_template", "{item_lower}"),
    )


def load_modifier_config(path: Path | None = None) -> ModifierConfig:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    defaults = raw.get("defaults", {})
    channel_raw = raw.get("channel_normalization", {})
    channel = ChannelNormalization(
        strip_regex=channel_raw.get("strip_regex", ChannelNormalization.strip_regex),
        strip_prefix_regex=channel_raw.get(
            "strip_prefix_regex", ChannelNormalization.strip_prefix_regex
        ),
        exclude_items=[str(x).upper() for x in channel_raw.get("exclude_items", [])],
        exclude_item_regex=channel_raw.get("exclude_item_regex", ""),
        aliases={k.upper(): v for k, v in channel_raw.get("aliases", {}).items()},
    )
    products = [_parse_product(p) for p in raw.get("products", [])]
    if not products:
        raise ValueError("modifier_products.yaml must define at least one product rule")
    return ModifierConfig(
        version=int(raw.get("version", 1)),
        output_case=defaults.get("output_case", "lower"),
        keep_modifier_rows=bool(defaults.get("keep_modifier_rows", False)),
        update_description=bool(defaults.get("update_description", True)),
        merge_delivery_channels=bool(defaults.get("merge_delivery_channels", True)),
        delivery_channels=[
            str(c).upper() for c in defaults.get("delivery_channels", [])
        ],
        channel_normalization=channel,
        products=products,
    )


def match_product_rule(
    rule: ProductRule,
    item: str,
    clave: str,
) -> bool:
    if rule.match_clave_platillo and clave.upper() == rule.match_clave_platillo.upper():
        return True
    if rule.match_item and item.upper() == rule.match_item.upper():
        return True
    if rule._item_pattern and rule._item_pattern.match(item):
        return True
    return False


def find_product_rule(
    config: ModifierConfig,
    item: str,
    clave: str,
) -> ProductRule | None:
    for rule in config.products:
        if match_product_rule(rule, item, clave):
            return rule
    return None
