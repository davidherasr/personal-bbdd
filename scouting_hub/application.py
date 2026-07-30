from __future__ import annotations

import streamlit as st

from .config import APP_SUBTITLE, APP_TITLE
from .pages import (
    page_dashboard, page_data_quality, page_database, page_import_export, page_lineups,
    page_matches, page_observations, page_players, page_rankings, page_research,
    page_role_lab, page_settings, page_workflow,
)
from .storage import ensure_storage
from .visuals import inject_css


def run() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="⚽", layout="wide", initial_sidebar_state="expanded")
    ensure_storage()
    inject_css()
    st.sidebar.markdown(f"## ⚽ {APP_TITLE}")
    st.sidebar.caption(APP_SUBTITLE)
    pages = {
        "Trabajo diario": [
            st.Page(page_dashboard, title="Dashboard", icon="🏠"),
            st.Page(page_workflow, title="Alta rápida", icon="➕"),
            st.Page(page_matches, title="Partidos", icon="📅"),
            st.Page(page_observations, title="Observaciones", icon="📝"),
        ],
        "Análisis": [
            st.Page(page_players, title="Jugadores", icon="👤"),
            st.Page(page_rankings, title="Rankings", icon="🏅"),
            st.Page(page_role_lab, title="Laboratorio de roles", icon="🧪"),
            st.Page(page_lineups, title="Alineaciones", icon="📋"),
            st.Page(page_research, title="Investigación", icon="🔎"),
        ],
        "Administración": [
            st.Page(page_data_quality, title="Calidad y duplicados", icon="🧹"),
            st.Page(page_database, title="Base editable", icon="🗃️"),
            st.Page(page_import_export, title="Importar / Exportar", icon="💾"),
            st.Page(page_settings, title="Ajustes del scoring", icon="⚙️"),
        ],
    }
    navigation = st.navigation(pages)
    navigation.run()
