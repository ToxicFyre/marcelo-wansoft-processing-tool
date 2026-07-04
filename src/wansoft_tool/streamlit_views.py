"""
Purpose:
  Streamlit UI sections for Marcelo's detalle analysis app.

Why is this in this project:
  Keeps streamlit_app.py thin for Archbrace flow-locality limits.

Inputs:
  Streamlit session state, user selections, loaded DataFrames.

Outputs:
  Rendered widgets and updated session state keys.

Side effects:
  Mutates st.session_state; displays Streamlit UI.

Failure behavior:
  Surfaces user-facing st.error messages; does not swallow exceptions.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from wansoft_tool.excel_export import dataframe_to_excel_bytes
from wansoft_tool.modifier_config import ModifierConfig, load_modifier_config
from wansoft_tool.sales_analytics import pareto_80_20

# Solo bronze por ahora; añade otras fuentes aquí cuando Marcelo las necesite.
ENABLED_DATA_SOURCES = ("Subir Excel bronze (manual)",)

REQUIRED_UPLOAD_COLUMNS = (
    "item",
    "is_modifier",
    "order_id",
    "subtotal_item",
    "sucursal",
    "operating_date",
)


def init_session_state() -> None:
    defaults = {
        "raw_df": None,
        "enriched_df": None,
        "agg_df": None,
        "merge_delivery": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar() -> tuple[str, date, date, list[str], bool]:
    st.sidebar.header("Configuración")
    default_end = date.today()
    default_start = default_end - timedelta(days=7)
    if len(ENABLED_DATA_SOURCES) == 1:
        source = ENABLED_DATA_SOURCES[0]
        st.sidebar.caption(
            "Sube el Excel de Detalle de Ventas que descargaste de Wansoft "
            "(Detail_*.xlsx)."
        )
    else:
        source = st.sidebar.radio("Fuente de datos", list(ENABLED_DATA_SOURCES))
    st.sidebar.caption("Las fechas del panel no aplican al archivo subido.")
    start = default_start
    end = default_end
    branches: list[str] = []
    merge = st.sidebar.checkbox(
        "Combinar Uber/Rappi/DiDi con productos de tienda",
        value=st.session_state.get("merge_delivery", True),
    )
    st.session_state["merge_delivery"] = merge
    return source, start, end, branches, merge


def validate_upload(df: pd.DataFrame) -> str | None:
    missing = [c for c in REQUIRED_UPLOAD_COLUMNS if c not in df.columns]
    if missing:
        return f"El CSV no tiene las columnas requeridas: {', '.join(missing)}"
    return None


def render_summary_tab(enriched: pd.DataFrame, raw: pd.DataFrame) -> None:
    st.subheader("Resumen")
    base = enriched.loc[~enriched["is_modifier"].astype(bool)]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingresos totales", f"${base['subtotal_item'].sum():,.2f}")
    c2.metric("Tickets", base["order_id"].nunique())
    c3.metric("Productos únicos", base["item"].nunique())
    c4.metric("Filas enriquecidas", len(enriched))
    if "operating_date" in enriched.columns:
        dates = pd.to_datetime(enriched["operating_date"])
        st.caption(
            f"Cobertura: {dates.min().date()} — {dates.max().date()} | "
            f"Filas originales: {len(raw)} → enriquecidas: {len(enriched)}"
        )


def render_pareto_tab(agg: pd.DataFrame) -> None:
    st.subheader("Top productos (80/20)")
    if agg.empty:
        st.info("No hay datos para mostrar.")
        return
    top, rest = pareto_80_20(agg)
    display = agg.copy()
    display["ingresos"] = display["revenue"].map(lambda x: f"${x:,.2f}")
    display = display.rename(
        columns={
            "item": "producto",
            "pct_of_total": "% del total",
            "cum_pct": "% acumulado",
        }
    )
    st.dataframe(
        display[["producto", "ingresos", "% del total", "% acumulado"]],
        use_container_width=True,
    )
    st.caption(f"Productos que aportan ~80%: {len(top)} de {len(agg)}")
    chart_df = top.set_index("item")[["revenue"]]
    st.bar_chart(chart_df)
    if not rest.empty:
        with st.expander("Resto (cola larga)"):
            st.dataframe(rest, use_container_width=True)


def render_download_tab(enriched: pd.DataFrame, agg: pd.DataFrame) -> None:
    st.subheader("Descargar Excel")
    if enriched.empty:
        st.info("Carga datos primero.")
        return
    st.download_button(
        "Descargar resumen 80/20",
        data=dataframe_to_excel_bytes(agg, "Resumen8020"),
        file_name="resumen_80_20.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.download_button(
        "Descargar detalle enriquecido",
        data=dataframe_to_excel_bytes(enriched, "Detalle"),
        file_name="detalle_enriquecido.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def load_config() -> ModifierConfig:
    return load_modifier_config(Path("config/modifier_products.yaml"))
