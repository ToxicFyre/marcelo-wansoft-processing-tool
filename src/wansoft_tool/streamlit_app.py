"""
Purpose:
  Streamlit entry point for Marcelo's Wansoft detalle tool.

Why is this in this project:
  Marcelo needs a no-code GUI for fetch, enrichment, 80/20, and Excel export.

Inputs:
  User selections via sidebar; Wansoft fetch, bronze Excel, or silver CSV upload.

Outputs:
  Interactive dashboards and Excel download buttons.

Side effects:
  Network fetch via pos_core; Streamlit session state updates.

Failure behavior:
  Shows st.error with Spanish messages; does not use silent exception handlers.
"""

from __future__ import annotations

import logging
from io import BytesIO

import pandas as pd
import streamlit as st

from wansoft_tool.bronze_upload import bronze_upload_to_silver
from wansoft_tool.enrichment import enrich_detail
from wansoft_tool.sales_analytics import aggregate_by_item
from wansoft_tool.streamlit_views import (
    init_session_state,
    load_config,
    render_download_tab,
    render_pareto_tab,
    render_sidebar,
    render_summary_tab,
    validate_upload,
)
from wansoft_tool.wansoft_fetch import fetch_detail_sales

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BRONZE_SOURCE = "Subir Excel bronze (manual)"
CSV_SOURCE = "Subir archivo CSV silver"
WANSOFT_SOURCE = "Descargar de Wansoft"


def _run_enrichment(raw: pd.DataFrame, merge: bool) -> pd.DataFrame:
    config = load_config()
    return enrich_detail(raw, config, merge_delivery=merge)


def _load_wansoft(start, end, branches) -> pd.DataFrame:
    return fetch_detail_sales(start, end, branches=branches or None)


def _load_bronze_uploads(uploads: list) -> pd.DataFrame:
    frames = []
    for uploaded in uploads:
        silver = bronze_upload_to_silver(BytesIO(uploaded.getvalue()), uploaded.name)
        frames.append(silver)
    if len(frames) == 1:
        return frames[0]
    return pd.concat(frames, ignore_index=True)


def _load_csv_upload(uploaded) -> pd.DataFrame:
    return pd.read_csv(uploaded)


def _load_raw_from_source(source: str, start, end, branches) -> pd.DataFrame | None:
    if source == WANSOFT_SOURCE:
        return _load_wansoft(start, end, branches)
    if source == BRONZE_SOURCE:
        uploads = st.session_state.get("uploaded_bronze_files") or []
        if not uploads:
            st.error("Selecciona uno o más archivos Excel bronze (.xlsx).")
            return None
        return _load_bronze_uploads(uploads)
    uploaded = st.session_state.get("uploaded_csv_file")
    if uploaded is None:
        st.error("Selecciona un archivo CSV silver.")
        return None
    return _load_csv_upload(uploaded)


def _store_enriched(raw: pd.DataFrame, merge: bool) -> None:
    enriched = _run_enrichment(raw, merge)
    st.session_state["raw_df"] = raw
    st.session_state["enriched_df"] = enriched
    st.session_state["agg_df"] = aggregate_by_item(enriched)


def _needs_csv_validation(source: str) -> bool:
    return source == CSV_SOURCE


def _try_load_and_store(source: str, start, end, branches, merge: bool) -> bool:
    raw = _load_raw_from_source(source, start, end, branches)
    if raw is None:
        return False
    if raw.empty:
        st.warning("No se encontraron datos en el archivo.")
        return False
    if _needs_csv_validation(source):
        err = validate_upload(raw)
        if err:
            st.error(err)
            return False
    _store_enriched(raw, merge)
    return True


def _on_load_clicked(source: str, start, end, branches, merge: bool) -> None:
    try:
        label = (
            "Limpiando Excel y cargando datos..."
            if source == BRONZE_SOURCE
            else "Cargando datos..."
        )
        with st.spinner(label):
            if not _try_load_and_store(source, start, end, branches, merge):
                return
        st.success("Datos cargados y enriquecidos.")
    except EnvironmentError as exc:
        st.error(str(exc))
    except ValueError as exc:
        st.error(str(exc))
    except OSError as exc:
        logger.exception("Error de red o archivo")
        st.error(f"Error al cargar datos: {exc}")


def _maybe_refresh_merge(raw: pd.DataFrame, merge: bool) -> pd.DataFrame | None:
    enriched = st.session_state.get("enriched_df")
    if enriched is None or merge == st.session_state.get("_last_merge"):
        return enriched
    st.session_state["enriched_df"] = _run_enrichment(raw, merge)
    st.session_state["agg_df"] = aggregate_by_item(st.session_state["enriched_df"])
    st.session_state["_last_merge"] = merge
    return st.session_state["enriched_df"]


def _render_tabs(enriched: pd.DataFrame, raw: pd.DataFrame, merge: bool) -> None:
    st.session_state["_last_merge"] = merge
    agg = st.session_state.get("agg_df")
    if agg is None:
        agg = aggregate_by_item(enriched)
    tabs = st.tabs(
        ["Resumen", "Top productos (80/20)", "Detalle enriquecido", "Descargar"]
    )
    with tabs[0]:
        render_summary_tab(enriched, raw)
    with tabs[1]:
        render_pareto_tab(agg)
    with tabs[2]:
        st.dataframe(enriched, use_container_width=True)
    with tabs[3]:
        render_download_tab(enriched, agg)


def _render_upload_widget(source: str) -> None:
    if source == BRONZE_SOURCE:
        st.session_state["uploaded_bronze_files"] = st.sidebar.file_uploader(
            "Excel bronze Wansoft (Detail_*.xlsx)",
            type=["xlsx"],
            accept_multiple_files=True,
            help="Descarga manual desde Wansoft → Detalle de Ventas. Puedes subir varios archivos.",
        )
        return
    if source == CSV_SOURCE:
        st.session_state["uploaded_csv_file"] = st.sidebar.file_uploader(
            "Archivo CSV silver (detail_*.csv)",
            type=["csv"],
        )


def main() -> None:
    st.set_page_config(page_title="Detalle Wansoft", layout="wide")
    st.title("Análisis de Detalle de Ventas — Panem")
    init_session_state()
    source, start, end, branches, merge = render_sidebar()
    if source in (BRONZE_SOURCE, CSV_SOURCE):
        _render_upload_widget(source)
    if st.sidebar.button("Cargar datos"):
        _on_load_clicked(source, start, end, branches, merge)
    raw = st.session_state.get("raw_df")
    enriched = st.session_state.get("enriched_df")
    if raw is not None and enriched is not None:
        enriched = _maybe_refresh_merge(raw, merge)
    if enriched is None or raw is None:
        st.info("Configura la fuente de datos y presiona **Cargar datos**.")
        return
    _render_tabs(enriched, raw, merge)


if __name__ == "__main__":
    main()
