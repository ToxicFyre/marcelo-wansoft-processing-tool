"""
Purpose:
  Lowercase and accent-stripping helpers for enriched product names.

Why is this in this project:
  Output names must be consistent lowercase per Marcelo's menu/stocking view.

Inputs:
  Raw item or modifier strings from Wansoft silver data.

Outputs:
  Normalized lowercase strings for name templates.

Side effects:
  None.

Failure behavior:
  Returns empty string for blank input.
"""

from __future__ import annotations

import re
import unicodedata


def remove_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def to_output_case(text: str, output_case: str) -> str:
    if not text:
        return text
    if output_case == "preserve":
        return text
    return remove_accents(text).lower()


def extract_concha_flavor(item: str) -> str:
    match = re.match(r"^CONCHA\s+(VAINILLA|CHOCOLATE)$", item.strip(), re.IGNORECASE)
    if not match:
        return ""
    return to_output_case(match.group(1), "lower")
