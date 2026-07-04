"""Ensure committed fixtures were generated from a live Wansoft fetch."""

from __future__ import annotations

import json
import re
from pathlib import Path

FIXTURES_README = Path(__file__).parent / "fixtures" / "README.md"
LIVE_SOURCE_LABEL = "pos_core.sales.core.fetch (live Wansoft)"

FORBIDDEN_SOURCE_MARKERS = (
    "local silver",
    "local pos-core-etl",
    "fallback",
    "pos-pipeline-front-end",
    "Main-ETL-Project",
)


def _provenance_from_readme() -> dict[str, object]:
    text = FIXTURES_README.read_text(encoding="utf-8")
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if not match:
        raise AssertionError(
            "tests/fixtures/README.md must contain a JSON provenance block. "
            "Run: python tests/bootstrap_fixtures.py"
        )
    return json.loads(match.group(1))


def test_fixture_provenance_is_live_wansoft() -> None:
    provenance = _provenance_from_readme()
    source = str(provenance.get("source", ""))
    assert source == LIVE_SOURCE_LABEL, (
        f"Fixture source must be live Wansoft ETL ({LIVE_SOURCE_LABEL!r}), "
        f"got {source!r}. Run: python tests/bootstrap_fixtures.py "
        "after fixing secrets.env — do not copy CSVs from other repos."
    )
    lowered = source.lower()
    for marker in FORBIDDEN_SOURCE_MARKERS:
        assert marker not in lowered, (
            f"Fixture provenance contains forbidden marker {marker!r}. "
            "Regenerate with live fetch only."
        )
