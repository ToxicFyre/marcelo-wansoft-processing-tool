"""
Purpose:
  Build real silver CSV test fixtures from a live Wansoft ETL fetch.

Why is this in this project:
  Committed fixtures must come from pos_core against Wansoft — never copied
  from other repos or stale local CSVs (that defangs regression tests).

Inputs:
  secrets.env (WS_BASE, WS_USER, WS_PASS), sucursales.json, date range.

Outputs:
  tests/fixtures/raw/*.csv and tests/fixtures/scenarios/*.csv.

Side effects:
  Downloads bronze Excel and writes silver via pos_core; writes fixture files.

Failure behavior:
  Exits non-zero on auth/network errors or missing scenario tickets.
  Does not fall back to local files.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "tests" / "fixtures" / "raw"
SCENARIO_DIR = REPO_ROOT / "tests" / "fixtures" / "scenarios"
PROVENANCE_PATH = REPO_ROOT / "tests" / "fixtures" / "README.md"

START = date(2025, 12, 1)
END = date(2025, 12, 7)
BRANCHES = ["Kavia", "QIN"]

# Committed fixtures must record this exact source (enforced by test_fixtures_provenance.py).
LIVE_SOURCE_LABEL = "pos_core.sales.core.fetch (live Wansoft)"

FIXTURE_POLICY = """\
# Fixtures de prueba (datos reales)

## Política obligatoria

Los CSV en `tests/fixtures/` **deben generarse con descarga en vivo desde Wansoft**
mediante `pos_core.sales.core.fetch()` en esta máquina/repositorio.

**No está permitido** para fixtures comprometidos en git:

- Copiar `detail_*.csv` desde otros repos (`pos-pipeline-front-end`, `Main-ETL-Project`, etc.)
- Usar un fallback local cuando falle la autenticación
- Crear filas sintéticas o recortes minimizados a mano

Si `python tests/bootstrap_fixtures.py` falla, **corrige `secrets.env` / acceso a Wansoft**
y vuelve a ejecutarlo. No sustituyas los fixtures por copias locales.

Regenerar:

```bash
cp secrets.env.example secrets.env   # si aún no existe
# Editar secrets.env con WS_BASE, WS_USER, WS_PASS
python tests/bootstrap_fixtures.py
```

"""


def _ticket_rows(df: pd.DataFrame, order_id: int) -> pd.DataFrame:
    return df.loc[df["order_id"] == order_id].copy()


def _has_cafe_refill_mod(ticket: pd.DataFrame, mod: str) -> bool:
    base = ticket.loc[~ticket["is_modifier"].astype(bool)]
    mods = ticket.loc[ticket["is_modifier"].astype(bool)]
    if not (base["item"].str.upper() == "CAFE REFILL").any():
        return False
    return (mods["modifier"].str.upper() == mod.upper()).any()


def _non_adjacent_cafe_refill(ticket: pd.DataFrame) -> bool:
    if not (ticket["item"].str.upper() == "CAFE REFILL").any():
        return False
    rows = ticket.reset_index(drop=True)
    for i, row in rows.iterrows():
        if row["is_modifier"] or str(row["item"]).upper() != "CAFE REFILL":
            continue
        if i + 2 >= len(rows):
            continue
        next_row = rows.iloc[i + 1]
        mod_row = rows.iloc[i + 2]
        if not next_row["is_modifier"] and mod_row["is_modifier"]:
            if str(mod_row["item"]).upper() == "CAFE REFILL":
                return True
    return False


def _scenario_finders() -> dict[str, callable]:
    return {
        "cafe_refill_regular.csv": lambda t: _has_cafe_refill_mod(t, "REGULAR"),
        "cafe_refill_descafeinado.csv": lambda t: _has_cafe_refill_mod(
            t, "DESCAFEINADO"
        ),
        "chilaquiles_salsa_verde_with_egg.csv": lambda t: (
            t["item"].str.upper().str.contains("CHILAQUILES PANEM").any()
            and (t["modifier"].str.upper() == "SALSA VERDE").any()
            and (t["modifier"].str.upper() == "HUEVO CHILAQUIL INCLUIDO").any()
        ),
        "concha_vainilla_passthrough.csv": lambda t: (
            t["item"].str.upper() == "CONCHA VAINILLA"
        ).any(),
        "concha_uber_chocolate.csv": lambda t: (
            (t["item"].str.upper() == "CONCHA UBER").any()
            and (t["modifier"].str.upper() == "CHOCOLATE").any()
        ),
        "concha_rappi_vainilla.csv": lambda t: (
            (t["item"].str.upper() == "CONCHA RAPPI").any()
            and (t["modifier"].str.upper() == "VAINILLA").any()
        ),
        "chilaquiles_uber_salsa_verde.csv": lambda t: (
            (t["item"].str.upper() == "CHILAQUILES PANEM UBER").any()
            and (t["modifier"].str.upper() == "SALSA VERDE").any()
        ),
        "caja_10_conchas_uber.csv": lambda t: (
            t["item"].str.upper() == "CAJA 10 CONCHAS UBER"
        ).any(),
        "non_adjacent_modifier.csv": _non_adjacent_cafe_refill,
        "delivery_passthrough_latte.csv": lambda t: (
            (t["item"].str.upper() == "LATTE 16OZ UBER").any()
            and (~t["is_modifier"].astype(bool)).any()
        ),
    }


def _find_order(df: pd.DataFrame, predicate) -> int | None:
    for order_id, ticket in df.groupby("order_id"):
        if predicate(ticket):
            return int(order_id)
    return None


def _load_from_wansoft() -> pd.DataFrame:
    from wansoft_tool.wansoft_fetch import fetch_detail_sales

    return fetch_detail_sales(START, END, branches=BRANCHES, mode="force")


def _write_fixtures(integration_df: pd.DataFrame) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    raw_name = f"detail_kavia_qin_{START}_{END}.csv"
    raw_path = RAW_DIR / raw_name
    integration_df.to_csv(raw_path, index=False)
    provenance: dict[str, object] = {
        "start": START.isoformat(),
        "end": END.isoformat(),
        "branches": BRANCHES,
        "source": LIVE_SOURCE_LABEL,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_file": raw_name,
        "row_count": len(integration_df),
        "scenarios": {},
    }
    for filename, predicate in _scenario_finders().items():
        order_id = _find_order(integration_df, predicate)
        if order_id is None:
            raise SystemExit(
                f"Scenario not found in live fetch data: {filename}. "
                "Try a wider date range or more branches in bootstrap_fixtures.py."
            )
        out_path = SCENARIO_DIR / filename
        _ticket_rows(integration_df, order_id).to_csv(out_path, index=False)
        provenance["scenarios"][filename] = {"order_id": order_id}
    PROVENANCE_PATH.write_text(
        FIXTURE_POLICY + "## Procedencia de la última generación\n\n"
        f"```json\n{json.dumps(provenance, indent=2)}\n```\n",
        encoding="utf-8",
    )
    print(f"Wrote {raw_path} ({len(integration_df)} rows) and 10 scenario files.")
    print(f"Source: {LIVE_SOURCE_LABEL}")


def main() -> None:
    try:
        integration_df = _load_from_wansoft()
    except Exception as exc:
        print(
            "Live Wansoft fetch failed. Fix secrets.env (WS_BASE, WS_USER, WS_PASS) "
            "and Wansoft access, then re-run.\n"
            "Do not copy fixtures from other repos — that invalidates regression tests.\n"
            f"Error: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    if integration_df.empty:
        print("Live fetch returned no rows.", file=sys.stderr)
        raise SystemExit(1)
    _write_fixtures(integration_df)


if __name__ == "__main__":
    main()
