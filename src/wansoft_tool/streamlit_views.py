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

from wansoft_tool.cross_selling import top_cross_sell_rules
from wansoft_tool.excel_export import dataframe_to_excel_bytes
from wansoft_tool.modifier_config import ModifierConfig, load_modifier_config
from wansoft_tool.sales_analytics import pareto_80_20
from wansoft_tool.ticket_identity import ticket_key

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
        "cross_sell_df": None,
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
    c2.metric("Tickets", ticket_key(base).nunique())
    c3.metric("Productos únicos", base["item"].nunique())
    c4.metric("Filas enriquecidas", len(enriched))
    if "operating_date" in enriched.columns:
        dates = pd.to_datetime(enriched["operating_date"])
        st.caption(
            f"Cobertura: {dates.min().date()} — {dates.max().date()} | "
            f"Filas originales: {len(raw)} → enriquecidas: {len(enriched)}"
        )


def _rule_card_content(rule: pd.Series) -> dict[str, str]:
    antecedent_tickets = int(rule["antecedent_tickets"])
    co_tickets = int(rule["co_tickets"])
    reliable = " · asociación por encima de lo normal" if bool(rule["eligible"]) else ""
    return {
        "confidence_value": f"{rule['confidence']:.1%}",
        "confidence_detail": f"de esos {antecedent_tickets} tickets",
        "lift_delta": f"{rule['lift']:.2f}× vs. frecuencia normal",
        "evidence": (
            f"Evidencia: {co_tickets} tickets con ambos · "
            f"piso seguro {rule['confidence_lower_bound']:.1%}{reliable}"
        ),
    }


def _render_rule_card(column, rank: int, rule: pd.Series) -> None:
    anchor = str(rule["antecedent"])
    companion = str(rule["consequent"])
    content = _rule_card_content(rule)
    column.markdown(f"#### {rank}. Cuando compren **{anchor}**")
    column.write(f"Ofrece **{companion}**")
    column.metric(
        "También aparece en",
        content["confidence_value"],
        delta=content["lift_delta"],
    )
    column.caption(content["confidence_detail"])
    column.caption(content["evidence"])


def _display_cross_sell_table(rules: pd.DataFrame) -> pd.DataFrame:
    display = rules.copy()
    display["confianza"] = display["confidence"].map(lambda value: f"{value:.1%}")
    display["frecuencia base"] = display["base_rate"].map(lambda value: f"{value:.1%}")
    display["afinidad"] = display["lift"].map(lambda value: f"{value:.2f}×")
    display["piso seguro"] = display["confidence_lower_bound"].map(
        lambda value: f"{value:.1%}"
    )
    return display.rename(
        columns={
            "consequent": "ofrecer",
            "antecedent_tickets": "tickets del producto",
            "co_tickets": "tickets con ambos",
        }
    )[
        [
            "ofrecer",
            "tickets del producto",
            "tickets con ambos",
            "confianza",
            "frecuencia base",
            "afinidad",
            "piso seguro",
        ]
    ]


def _eligible_anchors(rules: pd.DataFrame) -> list[str]:
    eligible = rules.loc[rules["eligible"].astype(bool)]
    if eligible.empty:
        return []
    ordered = eligible.sort_values(
        ["antecedent_tickets", "antecedent"], ascending=[False, True]
    )
    return ordered["antecedent"].drop_duplicates().tolist()


def render_cross_sell_tab(rules: pd.DataFrame) -> None:
    st.subheader("Ventas cruzadas")
    st.caption(
        "Asociaciones históricas confiables entre productos del mismo ticket; "
        "no demuestran que la oferta causará una compra."
    )
    top = top_cross_sell_rules(rules, n=3)
    if top.empty:
        st.info(
            "No hay evidencia suficiente para recomendar ventas cruzadas "
            "con estos datos."
        )
    else:
        columns = st.columns(3)
        for rank, (_, rule) in enumerate(top.iterrows(), start=1):
            _render_rule_card(columns[rank - 1], rank, rule)
    anchors = _eligible_anchors(rules)
    if not anchors:
        return
    st.divider()
    selected = st.selectbox("¿Qué ofrecer con este producto?", anchors)
    selected_rules = top_cross_sell_rules(rules, n=3, antecedent=selected)
    st.dataframe(
        _display_cross_sell_table(selected_rules),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Confianza = tickets con ambos ÷ tickets del producto.")
    with st.expander("Cómo leer estas recomendaciones"):
        st.markdown(
            "- **Qué significa:** cuando alguien compra el producto elegido, "
            "históricamente también se lleva la sugerencia en ese porcentaje de "
            "sus tickets.\n"
            "- **Tickets del producto, tickets con ambos y confianza:** si hay "
            "170 tickets con el producto y 17 llevan también la sugerencia, la "
            "confianza es 10% (17 ÷ 170).\n"
            "- **Afinidad:** cuántas veces más seguido aparecen juntos frente a "
            "lo normal. 1× es lo esperado por azar; más de 1× indica que se "
            "acompañan más de lo esperado.\n"
            "- **Piso seguro:** es la confianza mínima razonable considerando "
            "cuántos tickets hay. Si está cerca de la confianza, la evidencia es "
            "sólida; si baja mucho, hay pocos tickets compartidos y conviene ser "
            "cauteloso. En las recomendaciones mostradas el piso ya supera la "
            "frecuencia normal de la sugerencia, así que la pareja no parece "
            "una coincidencia casual.\n"
            "- **Recuerda:** describen compras pasadas; no garantizan que "
            "ofrecer el producto cause la compra."
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


def render_download_tab(
    enriched: pd.DataFrame,
    agg: pd.DataFrame,
    rules: pd.DataFrame,
) -> None:
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
    st.download_button(
        "Descargar ventas cruzadas",
        data=dataframe_to_excel_bytes(rules, "VentasCruzadas"),
        file_name="ventas_cruzadas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def load_config() -> ModifierConfig:
    return load_modifier_config(Path("config/modifier_products.yaml"))
