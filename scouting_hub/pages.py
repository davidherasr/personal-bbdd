from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

import pandas as pd
import streamlit as st

from .config import (
    APP_TITLE, DEFAULT_SCORING_WEIGHTS, FOOTS, FORMATION_TEMPLATES, FORMATION_SLOT_POSITIONS, MANUAL_PRIORITIES,
    MATCH_DIFFICULTIES, OPPOSITION_LEVELS, PLAYER_STATUS, POSITIONS, PRIORITY_LABELS,
    RELIABILITY_LEVELS, ROLE_NAMES, ROLE_PROFILES, SOURCE_TYPES, TEAM_TYPES, TREND_LEVELS,
    VIEWING_TYPES, SCHEMAS,
)
from .domain import (
    add_competition, add_country, add_match, add_observation, add_player, add_team, save_match_observation,
    delete_player_cascade, duplicate_candidates, enrich_data, get_name, merge_players, save_role_assessment,
)
from .scoring import (
    criterion_scores, metrics_table, percentile, scoring_breakdown, similarity_table,
)
from .storage import (
    append_row, backup_zip_bytes, delete_rows, empty_table, excel_backup_bytes, get_settings,
    import_csv, load_table, normalize_text, reset_all_data, restore_excel, restore_zip_bytes,
    save_settings, save_table, snapshot_data, update_row,
)
from .excel_views import excel_model_bytes
from .visuals import (
    empty_state, hero, kpi_grid, percentile_bars, priority_block, progress_list, radar_svg,
    render_lineup, score_rows, signals, strip_plot,
)


def _message(created: bool, message: str) -> None:
    (st.success if created else st.info)(message)


def _queue_widget_value(key: str, value: str) -> None:
    """Queue a widget value for the next rerun.

    Streamlit does not allow changing a widget-backed session_state key after
    that widget has been instantiated in the current run. Saving the value
    under a non-widget key and consuming it before the next widget declaration
    keeps the selectors predictable and compatible with recent Streamlit
    versions.
    """
    st.session_state[f"__pending__{key}"] = value


def _apply_queued_widget_value(key: str) -> None:
    pending_key = f"__pending__{key}"
    if pending_key in st.session_state:
        st.session_state[key] = st.session_state.pop(pending_key)


def _sanitize_widget_value(key: str, options: List[str]) -> None:
    """Reset stale dependent selections before their widget is rendered."""
    if key in st.session_state and st.session_state[key] not in options:
        st.session_state[key] = options[0] if options else ""


def _select_from_df(label: str, df: pd.DataFrame, id_col: str, name_col: str, key: str, empty_label: str = "— Seleccionar —") -> str:
    _apply_queued_widget_value(key)
    options = [""] + df[id_col].astype(str).tolist() if not df.empty else [""]
    _sanitize_widget_value(key, options)
    labels = {"": empty_label}
    if not df.empty:
        labels.update(dict(zip(df[id_col].astype(str), df[name_col].astype(str))))
    return st.selectbox(label, options, format_func=lambda value: labels.get(value, value), key=key)


def country_selector(label: str, key: str, allow_add: bool = True) -> str:
    countries = load_table("countries").sort_values("name")
    selected = _select_from_df(label, countries, "country_id", "name", key)
    if allow_add:
        with st.expander("+ Añadir país"):
            name = st.text_input("Nombre del país", key=f"{key}_new_name")
            if st.button("Guardar país", key=f"{key}_save"):
                cid, created, message = add_country(name)
                _message(created, message)
                if cid:
                    _queue_widget_value(key, cid)
                st.rerun()
    return selected



def competition_selector(label: str, country_id: str, key: str, allow_add: bool = True) -> str:
    competitions = load_table("competitions")
    if country_id:
        competitions = competitions[competitions["country_id"].astype(str) == str(country_id)]
    competitions = competitions.sort_values(["level", "name"])
    options = [""] + competitions["competition_id"].astype(str).tolist()
    labels = {"": "— Seleccionar —"}
    for _, row in competitions.iterrows():
        suffix = " · ".join(x for x in [str(row.get("level", "")), str(row.get("season", ""))] if x)
        value = str(row.get("ranking_value", "")).strip()
        value_suffix = f" · valor {value}/50" if value else ""
        labels[str(row["competition_id"])] = f"{row['name']}{' · ' + suffix if suffix else ''}{value_suffix}"
    _apply_queued_widget_value(key)
    _sanitize_widget_value(key, options)
    selected = st.selectbox(label, options, format_func=lambda value: labels.get(value, value), key=key)
    if allow_add and country_id:
        with st.expander("+ Añadir competición"):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            name = c1.text_input("Nombre", key=f"{key}_new_name")
            level = c2.text_input("Nivel", key=f"{key}_new_level", placeholder="1ª, 2ª…")
            season = c3.text_input("Temporada", key=f"{key}_new_season", placeholder="2026/27")
            ranking_value = c4.number_input(
                "Valor competitivo", min_value=1, max_value=50, value=30, step=1,
                key=f"{key}_ranking_value", help="Escala de tu Excel: 1ª ≈ 40-50; 2ª ≈ 30-40; 3ª ≈ 20-30."
            )
            if st.button("Guardar competición", key=f"{key}_save"):
                cid, created, message = add_competition(name, country_id, level, season, ranking_value)
                _message(created, message)
                if cid:
                    _queue_widget_value(key, cid)
                st.rerun()
    return selected

def team_selector(label: str, team_type: str, country_id: str, competition_id: str, key: str, allow_add: bool = True) -> str:
    teams = load_table("teams")
    if team_type:
        teams = teams[teams["team_type"].astype(str) == team_type]
    if country_id:
        teams = teams[teams["country_id"].astype(str) == str(country_id)]
    if team_type == "Club" and competition_id:
        teams = teams[teams["competition_id"].astype(str) == str(competition_id)]
    teams = teams.sort_values("name")
    selected = _select_from_df(label, teams, "team_id", "name", key)
    if allow_add and country_id:
        with st.expander("+ Añadir equipo / selección"):
            name = st.text_input("Nombre", key=f"{key}_new_name")
            if st.button("Guardar equipo / selección", key=f"{key}_save"):
                tid, created, message = add_team(name, team_type, country_id, competition_id)
                _message(created, message)
                if tid:
                    _queue_widget_value(key, tid)
                st.rerun()
    return selected


def player_selector(label: str, key: str, team_id: str = "", allow_all: bool = True) -> str:
    players = load_table("players")
    if team_id:
        players = players[players["current_team_id"].astype(str) == str(team_id)]
    players = players.sort_values("display_name")
    options = [""] + players["player_id"].astype(str).tolist()
    labels = {"": "— Seleccionar jugador —"}
    for _, row in players.iterrows():
        labels[str(row["player_id"])] = " · ".join(x for x in [str(row.get("display_name", "")), str(row.get("primary_position", "")), str(row.get("primary_role", ""))] if x)
    return st.selectbox(label, options, format_func=lambda value: labels.get(value, value), key=key)


def match_selector(label: str, key: str, team_id: str = "") -> str:
    data = enrich_data()
    matches = data["matches"].copy()
    if team_id and not matches.empty:
        matches = matches[(matches["home_team_id"].astype(str) == str(team_id)) | (matches["away_team_id"].astype(str) == str(team_id))]
    matches = matches.sort_values("match_date", ascending=False)
    return _select_from_df(label, matches, "match_id", "match_name", key, "— Sin partido asociado —")


def _weights() -> Mapping[str, float]:
    settings = get_settings()
    return settings.get("scoring_weights", DEFAULT_SCORING_WEIGHTS)  # type: ignore[return-value]



def roles_for_position(position: str) -> List[str]:
    if not position:
        return ROLE_NAMES.copy()
    return [name for name, profile in ROLE_PROFILES.items() if position in profile["positions"]]


def _safe_index(options: List[str], value: object) -> int:
    value = str(value or "")
    return options.index(value) if value in options else 0


def _float_or(value: object, default: float = 0.0) -> float:
    try:
        return float(value) if str(value).strip() else default
    except (TypeError, ValueError):
        return default


def formation_dataframe(formation: str, include_bench: bool = False) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for slot_key, label, _x, _y in FORMATION_TEMPLATES[formation]:
        rows.append({
            "Demarcación": label,
            "Nombre": "",
            "Posición": FORMATION_SLOT_POSITIONS.get(slot_key, ""),
            "Rol": "",
            "Edad": 0,
            "Pierna": "",
        })
    if include_bench:
        for index in range(1, 8):
            rows.append({"Demarcación": f"Suplente {index}", "Nombre": "", "Posición": "", "Rol": "", "Edad": 0, "Pierna": ""})
    return pd.DataFrame(rows)


def _player_edit_panel(player_id: str, prefix: str = "edit") -> None:
    players = load_table("players")
    rows = players[players["player_id"].astype(str) == str(player_id)]
    if rows.empty:
        st.error("Jugador no encontrado.")
        return
    player = rows.iloc[0]
    countries = load_table("countries").sort_values("name")
    teams = enrich_data()["teams"].sort_values("name")

    st.markdown("#### Editar ficha y corregir equipo")
    c1, c2 = st.columns([2, 1])
    name = c1.text_input("Nombre completo", value=str(player.get("display_name", "")), key=f"{prefix}_name_{player_id}")
    age = c2.number_input("Edad", min_value=0, max_value=60, value=int(_float_or(player.get("age"), 0)), key=f"{prefix}_age_{player_id}")

    country_options = [""] + countries["country_id"].astype(str).tolist()
    country_labels = {"": "— Sin nacionalidad —", **dict(zip(countries["country_id"].astype(str), countries["name"].astype(str)))}
    team_options = [""] + teams["team_id"].astype(str).tolist()
    team_labels = {"": "— Sin equipo —"}
    for _, team in teams.iterrows():
        suffix = " · ".join(x for x in [str(team.get("competition", "")), str(team.get("country", ""))] if x)
        team_labels[str(team["team_id"])] = f"{team['name']}{' · ' + suffix if suffix else ''}"

    c3, c4 = st.columns(2)
    nationality = c3.selectbox(
        "Nacionalidad", country_options, index=_safe_index(country_options, player.get("nationality_id")),
        format_func=lambda value: country_labels.get(value, value), key=f"{prefix}_nationality_{player_id}",
    )
    current_team = c4.selectbox(
        "Equipo actual", team_options, index=_safe_index(team_options, player.get("current_team_id")),
        format_func=lambda value: team_labels.get(value, value), key=f"{prefix}_team_{player_id}",
        help="Aquí puedes corregir un jugador asignado por error al equipo equivocado."
    )

    c5, c6, c7 = st.columns(3)
    position_options = [""] + POSITIONS
    primary_position = c5.selectbox("Posición principal", position_options, index=_safe_index(position_options, player.get("primary_position")), key=f"{prefix}_pos_{player_id}")
    secondary_position = c6.selectbox("Posición secundaria", position_options, index=_safe_index(position_options, player.get("secondary_position")), key=f"{prefix}_pos2_{player_id}")
    foot = c7.selectbox("Pierna", FOOTS, index=_safe_index(FOOTS, player.get("dominant_foot")), key=f"{prefix}_foot_{player_id}")

    role_options = [""] + roles_for_position(primary_position)
    current_role = str(player.get("primary_role", ""))
    if current_role and current_role not in role_options:
        role_options.append(current_role)
    c8, c9, c10 = st.columns(3)
    _sanitize_widget_value(f"{prefix}_role_{player_id}", role_options)
    primary_role = c8.selectbox("Rol principal", role_options, index=_safe_index(role_options, current_role), key=f"{prefix}_role_{player_id}")
    status = c9.selectbox("Estado", PLAYER_STATUS, index=_safe_index(PLAYER_STATUS, player.get("status")), key=f"{prefix}_status_{player_id}")
    manual_priority = c10.selectbox("Prioridad manual", MANUAL_PRIORITIES, index=_safe_index(MANUAL_PRIORITIES, player.get("manual_priority")), key=f"{prefix}_priority_{player_id}")

    c11, c12, c13, c14 = st.columns(4)
    height = c11.number_input("Altura (cm)", 0, 230, int(_float_or(player.get("height_cm"), 0)), key=f"{prefix}_height_{player_id}")
    potential = c12.number_input("Potencial 0-10", 0.0, 10.0, _float_or(player.get("potential_rating"), 5.0), .5, key=f"{prefix}_potential_{player_id}")
    tactical_fit = c13.number_input("Encaje táctico 0-10", 0.0, 10.0, _float_or(player.get("tactical_fit"), 5.0), .5, key=f"{prefix}_fit_{player_id}")
    position_need = c14.number_input("Necesidad posicional 0-10", 0.0, 10.0, _float_or(player.get("position_need"), 5.0), .5, key=f"{prefix}_need_{player_id}")
    tags = st.text_input("Etiquetas", value=str(player.get("tags", "")), key=f"{prefix}_tags_{player_id}")
    notes = st.text_area("Notas generales", value=str(player.get("general_notes", "")), key=f"{prefix}_notes_{player_id}")

    if st.button("Guardar cambios del jugador", type="primary", key=f"{prefix}_save_{player_id}"):
        normalized = normalize_text(name)
        duplicate = players[(players["normalized_name"].astype(str) == normalized) & (players["player_id"].astype(str) != str(player_id))]
        if not name.strip():
            st.error("El nombre no puede quedar vacío.")
        elif not duplicate.empty:
            st.error(f"Ya existe otro jugador llamado {duplicate.iloc[0]['display_name']}.")
        else:
            update_row("players", player_id, {
                "display_name": name.strip(), "normalized_name": normalized, "age": age or "",
                "nationality_id": nationality, "current_team_id": current_team,
                "primary_position": primary_position, "secondary_position": secondary_position,
                "dominant_foot": foot, "primary_role": primary_role, "status": status,
                "manual_priority": manual_priority, "height_cm": height or "",
                "potential_rating": potential, "tactical_fit": tactical_fit,
                "position_need": position_need, "tags": tags, "general_notes": notes,
            })
            st.success("Jugador actualizado.")
            st.rerun()

    with st.expander("Eliminar jugador"):
        st.warning("También se eliminarán sus observaciones, evaluaciones de rol, alias y apariciones en alineaciones.")
        confirmation = st.text_input("Escribe ELIMINAR", key=f"{prefix}_delete_confirm_{player_id}")
        if st.button("Eliminar definitivamente", key=f"{prefix}_delete_{player_id}"):
            if confirmation != "ELIMINAR":
                st.error("Escribe ELIMINAR para confirmar.")
            else:
                delete_player_cascade(player_id)
                st.success("Jugador eliminado.")
                st.rerun()


def _save_formation_roster(team_id: str, country_id: str, edited: pd.DataFrame, move_existing: bool = False) -> Tuple[int, int, List[str]]:
    created = updated = 0
    warnings: List[str] = []
    players = load_table("players")
    for _, row in edited.iterrows():
        name = str(row.get("Nombre", "")).strip()
        if not name:
            continue
        pid, was_created, message = add_player(
            name, nationality_id=country_id, current_team_id=team_id,
            primary_position=str(row.get("Posición", "")), primary_role=str(row.get("Rol", "")),
            age=int(_float_or(row.get("Edad"), 0)) or "", dominant_foot=str(row.get("Pierna", "")),
            status="Sin valorar",
        )
        if was_created:
            created += 1
            continue
        existing = players[players["player_id"].astype(str) == str(pid)]
        if existing.empty:
            continue
        existing_team = str(existing.iloc[0].get("current_team_id", ""))
        if existing_team and existing_team != str(team_id) and not move_existing:
            warnings.append(f"{name}: ya existe en otro equipo. No se ha movido.")
            continue
        updates = {
            "current_team_id": team_id,
            "primary_position": str(row.get("Posición", "")) or existing.iloc[0].get("primary_position", ""),
            "primary_role": str(row.get("Rol", "")) or existing.iloc[0].get("primary_role", ""),
        }
        if int(_float_or(row.get("Edad"), 0)):
            updates["age"] = int(_float_or(row.get("Edad"), 0))
        if str(row.get("Pierna", "")):
            updates["dominant_foot"] = str(row.get("Pierna", ""))
        update_row("players", pid, updates)
        updated += 1
    return created, updated, warnings


def page_dashboard() -> None:
    hero(
        "Dashboard de scouting",
        "Panel de control para detectar huecos de información, ordenar el trabajo y tomar decisiones sin confundir una primera impresión con evidencia sólida.",
        "KPI", "Flujo de trabajo",
    )
    data = enrich_data()
    players, teams, matches, observations, assessments = data["players"], data["teams"], data["matches"], data["observations"], data["role_assessments"]
    metrics = metrics_table(players, observations, assessments, _weights()) if not players.empty else pd.DataFrame()
    priorities = int(metrics["priority_label"].isin(["A", "B+"]).sum()) if not metrics.empty else 0
    avg_conf = int(metrics["confidence"].mean()) if not metrics.empty else 0
    avg_completion = int(metrics["completeness"].mean()) if not metrics.empty else 0
    avg_rating = round(float(metrics.loc[metrics["average_rating"] > 0, "average_rating"].mean()), 2) if not metrics.empty and (metrics["average_rating"] > 0).any() else "—"
    total_mvps = int(metrics["mvp_count"].sum()) if not metrics.empty else 0
    total_minutes = int(metrics["total_minutes"].sum()) if not metrics.empty else 0
    kpi_grid([
        ("Jugadores", len(players), ""), ("Partidos", len(matches), ""),
        ("Jugadores-partido", len(observations), "good"), ("Minutos vistos", total_minutes, ""),
        ("Nota media", avg_rating, ""), ("MVP registrados", total_mvps, "good" if total_mvps else ""),
        ("Prioridades A/B+", priorities, "warn"), ("Confianza media", f"{avg_conf}%", ""),
    ])
    if players.empty:
        empty_state("Base vacía, como pediste", "Empieza creando un partido o una plantilla; después registra minutos, nota y MVP. La app no incluye jugadores ni competiciones precargadas.")
        st.markdown("### Arranque recomendado")
        st.markdown(
            """
            <div class="panel"><div class="mini-grid">
              <div class="mini-card"><div class="title">1. Crea el partido</div><div class="sub">País, competición, local, visitante y fecha.</div></div>
              <div class="mini-card"><div class="title">2. Carga el once</div><div class="sub">Elige formación y escribe los nombres en una tabla.</div></div>
              <div class="mini-card"><div class="title">3. Puntúa en bloque</div><div class="sub">Minutos, nota, MVP y una nota corta. Lo avanzado es opcional.</div></div>
            </div></div>
            """,
            unsafe_allow_html=True,
        )
        return

    left, right = st.columns([2, 1])
    with left:
        action = metrics.sort_values(["decision_score", "confidence"], ascending=[False, True]).copy()
        columns = ["display_name", "current_team", "primary_position", "primary_role", "average_rating", "mvp_count", "heritage_score", "priority_label", "decision_score", "confidence", "next_action", "alerts_text"]
        st.subheader("Cola de trabajo")
        st.dataframe(action[[c for c in columns if c in action.columns]].head(15), use_container_width=True, hide_index=True)
    with right:
        st.markdown(
            """
            <div class="panel"><h3>Cómo leer el ranking</h3><p><strong>Prioridad</strong> decide qué hacer ahora. <strong>Nivel</strong> mide lo observado. <strong>Encaje de rol</strong> evalúa la función concreta. <strong>Confianza</strong> limita cuánto puedes creer el resultado.</p></div>
            <div class="panel"><h3>Regla de seguridad</h3><p>Una señal alta con baja confianza no se convierte en A: se convierte en una segunda observación prioritaria.</p></div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("Alertas de calidad")
    alerts = {
        "Sin observaciones": int((metrics["observation_count"] == 0).sum()),
        "Confianza < 45": int((metrics["confidence"] < 45).sum()),
        "Sin rol principal": int((metrics["primary_role"].astype(str).str.strip() == "").sum()),
        "Ficha < 50%": int((metrics["completeness"] < 50).sum()),
    }
    progress_list("Estado de la base", list(alerts.items()))



def page_workflow() -> None:
    hero("Alta y plantilla", "Crea un once completo, corrige jugadores o añade nombres sin convertir cada alta en un formulario interminable.", "Trabajo diario", "Formación primero")
    c0, c1, c2, c3 = st.columns([1, 1.3, 1.5, 1.7])
    scope = c0.radio("Contexto", TEAM_TYPES, horizontal=False, key="wf_scope")
    with c1:
        country_id = country_selector("País", "wf_country")
    with c2:
        competition_id = competition_selector("Competición / liga", country_id, "wf_comp") if scope == "Club" and country_id else ""
    with c3:
        team_id = team_selector("Equipo / selección", scope, country_id, competition_id, "wf_team") if country_id else ""
    if not team_id:
        st.info("Selecciona o crea un equipo para continuar.")
        return

    tabs = st.tabs(["Once por formación", "Editar jugador", "Jugador individual", "Lista rápida"])
    with tabs[0]:
        st.caption("La formación ya coloca once demarcaciones. Solo escribe nombres; posición, rol, edad y pierna son opcionales.")
        formation = st.selectbox("Formación", list(FORMATION_TEMPLATES), key="wf_formation")
        grid = formation_dataframe(formation)
        edited = st.data_editor(
            grid, use_container_width=True, hide_index=True, num_rows="fixed", key=f"wf_formation_grid_{formation}",
            column_config={
                "Demarcación": st.column_config.TextColumn(disabled=True, width="medium"),
                "Nombre": st.column_config.TextColumn("Jugador", required=False, width="large"),
                "Posición": st.column_config.SelectboxColumn(options=[""] + POSITIONS, width="small"),
                "Rol": st.column_config.SelectboxColumn(options=[""] + ROLE_NAMES, width="medium"),
                "Edad": st.column_config.NumberColumn(min_value=0, max_value=60, step=1, width="small"),
                "Pierna": st.column_config.SelectboxColumn(options=FOOTS, width="small"),
            },
        )
        move_existing = st.checkbox("Mover al equipo seleccionado si el jugador ya existe en otro equipo", value=False, key="wf_move_existing")
        if st.button("Guardar once / plantilla", type="primary", key="wf_save_formation"):
            created, updated, warnings = _save_formation_roster(team_id, country_id, edited, move_existing)
            st.success(f"Creados: {created}. Actualizados: {updated}.")
            for warning in warnings:
                st.warning(warning)
            if not warnings:
                st.rerun()

    with tabs[1]:
        all_players = enrich_data()["players"].sort_values("display_name")
        if all_players.empty:
            st.info("Todavía no hay jugadores.")
        else:
            selector = all_players.copy()
            selector["edit_label"] = selector.apply(
                lambda row: " · ".join(x for x in [str(row.get("display_name", "")), str(row.get("current_team", "")), str(row.get("primary_position", ""))] if x), axis=1
            )
            player_id = _select_from_df("Jugador que quieres corregir", selector, "player_id", "edit_label", "wf_edit_player")
            st.caption("Puedes cambiarlo de equipo aunque hayas entrado desde otro club; el historial de partidos conserva el equipo con el que fue observado.")
            if player_id:
                _player_edit_panel(player_id, "wf_edit")

    with tabs[2]:
        name = st.text_input("Nombre completo", key="wf_new_name")
        candidates = duplicate_candidates(name)
        if name and not candidates.empty:
            st.warning("Coincidencias parecidas encontradas:")
            st.dataframe(candidates, use_container_width=True, hide_index=True)
        c1, c2, c3, c4 = st.columns(4)
        position = c1.selectbox("Posición", [""] + POSITIONS, key="wf_ind_pos")
        role_options = [""] + roles_for_position(position)
        _sanitize_widget_value("wf_ind_role", role_options)
        role = c2.selectbox("Rol (opcional)", role_options, key="wf_ind_role")
        age = c3.number_input("Edad", 0, 60, 0, key="wf_ind_age")
        foot = c4.selectbox("Pierna", FOOTS, key="wf_ind_foot")
        with st.expander("Datos avanzados opcionales"):
            c5, c6, c7 = st.columns(3)
            status = c5.selectbox("Estado", PLAYER_STATUS, key="wf_ind_status")
            potential = c6.number_input("Potencial 0-10", 0.0, 10.0, 5.0, .5, key="wf_ind_potential")
            source = c7.selectbox("Fuente", SOURCE_TYPES, key="wf_ind_source")
            notes = st.text_area("Notas generales", key="wf_ind_notes")
        if st.button("Crear jugador", type="primary", key="wf_ind_create"):
            exact = candidates[candidates["similarity"] >= 99] if not candidates.empty else pd.DataFrame()
            if not name.strip():
                st.error("Escribe un nombre.")
            elif not exact.empty:
                st.error("No se ha creado: ya existe una coincidencia exacta o alias.")
            else:
                _, created, message = add_player(
                    name, age=age or "", nationality_id=country_id, primary_position=position,
                    dominant_foot=foot, current_team_id=team_id, status=status,
                    potential_rating=potential, primary_role=role, source=source, general_notes=notes,
                )
                _message(created, message)
                if created:
                    st.rerun()

    with tabs[3]:
        names = st.text_area("Un jugador por línea", height=190, key="wf_bulk_names", placeholder="Jugador Uno\nJugador Dos\nJugador Tres")
        c1, c2 = st.columns(2)
        default_position = c1.selectbox("Posición por defecto", [""] + POSITIONS, key="wf_bulk_position")
        bulk_role_options = [""] + roles_for_position(default_position)
        _sanitize_widget_value("wf_bulk_role", bulk_role_options)
        default_role = c2.selectbox("Rol por defecto", bulk_role_options, key="wf_bulk_role")
        if st.button("Crear lista", type="primary", key="wf_bulk_create"):
            created = skipped = 0
            for line in names.splitlines():
                player_name = line.strip()
                if not player_name:
                    continue
                _, was_created, _ = add_player(
                    player_name, nationality_id=country_id, current_team_id=team_id,
                    primary_position=default_position, primary_role=default_role, status="Sin valorar",
                )
                created += int(was_created)
                skipped += int(not was_created)
            st.success(f"Creados: {created}. Ya existentes: {skipped}.")
            st.rerun()

    st.divider()
    st.subheader("Plantilla actual")
    roster = load_table("players")
    roster = roster[roster["current_team_id"].astype(str) == str(team_id)].sort_values(["primary_position", "display_name"])
    if roster.empty:
        st.info("La plantilla sigue vacía.")
    else:
        st.dataframe(roster[["display_name", "primary_position", "primary_role", "age", "dominant_foot", "status"]], use_container_width=True, hide_index=True)

def _observation_form(player_id: str, team_id: str = "", prefix: str = "obs") -> None:
    players = load_table("players")
    player_rows = players[players["player_id"].astype(str) == str(player_id)]
    if player_rows.empty:
        st.error("Jugador no encontrado.")
        return
    player = player_rows.iloc[0]
    st.subheader(f"Observación · {player['display_name']}")
    match_id = match_selector("Partido", f"{prefix}_match", team_id)
    with st.form(f"{prefix}_observation_form"):
        c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])
        position = c1.selectbox("Posición", [""] + POSITIONS, index=([""] + POSITIONS).index(str(player.get("primary_position", ""))) if str(player.get("primary_position", "")) in POSITIONS else 0)
        minutes = c2.number_input("Minutos", min_value=0, max_value=130, value=90)
        global_rating = c3.number_input("Nota", min_value=0.0, max_value=10.0, value=0.0, step=0.5, help="0 = pendiente de puntuar")
        mvp = c4.checkbox("MVP", value=False)
        quick_note = st.text_area("Nota rápida", placeholder="Qué hizo bien, dudas o acción decisiva…", height=100)
        with st.expander("Evaluación avanzada (opcional)"):
            a1, a2, a3, a4 = st.columns(4)
            role_options = [""] + roles_for_position(position)
            role = a1.selectbox("Rol observado", role_options, index=_safe_index(role_options, str(player.get("primary_role", ""))))
            viewing = a2.selectbox("Tipo de visionado", VIEWING_TYPES, index=_safe_index(VIEWING_TYPES, "Partido completo"))
            reliability = a3.selectbox("Fiabilidad", RELIABILITY_LEVELS, index=_safe_index(RELIABILITY_LEVELS, "Alta"))
            starter = a4.checkbox("Titular", value=True)
            a5, a6, a7 = st.columns(3)
            opposition = a5.selectbox("Nivel del rival", OPPOSITION_LEVELS, index=_safe_index(OPPOSITION_LEVELS, "Medio"))
            difficulty = a6.selectbox("Dificultad", MATCH_DIFFICULTIES, index=_safe_index(MATCH_DIFFICULTIES, "Media"))
            trend = a7.selectbox("Tendencia", TREND_LEVELS, index=_safe_index(TREND_LEVELS, "Mantiene"))
            st.caption("Las cuatro notas siguientes son opcionales y alimentan el análisis por posición y rol.")
            r1, r2, r3, r4 = st.columns(4)
            technical = r1.number_input("Técnica", 0.0, 10.0, 0.0, .5)
            tactical = r2.number_input("Táctica", 0.0, 10.0, 0.0, .5)
            physical = r3.number_input("Físico", 0.0, 10.0, 0.0, .5)
            mental = r4.number_input("Mental", 0.0, 10.0, 0.0, .5)
            improvements = st.text_area("Dudas / aspectos de mejora")
            next_step = st.text_input("Próximo paso manual", placeholder="Ver 90 minutos, comparar, cerrar informe…")
        submitted = st.form_submit_button("Guardar observación")
    if submitted:
        _, created, message = save_match_observation(
            player_id=player_id, match_id=match_id, team_id=team_id or player.get("current_team_id", ""),
            observed_position=position, role=role, minutes_observed=minutes, viewing_type=viewing,
            opposition_level=opposition, match_difficulty=difficulty, reliability=reliability, trend=trend,
            technical_rating=technical, tactical_rating=tactical, physical_rating=physical,
            mental_rating=mental, global_rating=global_rating if global_rating > 0 else "",
            starter="Sí" if starter else "No", mvp="Sí" if mvp else "No",
            positive_notes=quick_note, improvement_notes=improvements, next_step=next_step,
        )
        _message(created, message)

def _match_grid_base(match_id: str, team_id: str, formation: str) -> pd.DataFrame:
    """Build a formation grid and preload prior match ratings when they exist."""
    data = enrich_data()
    players = data["players"]
    roster = players[players["current_team_id"].astype(str) == str(team_id)].sort_values("display_name")
    observations = data["observations"]
    existing = observations[
        (observations["match_id"].astype(str) == str(match_id)) &
        (observations["team_id"].astype(str) == str(team_id))
    ].copy()
    if not existing.empty:
        existing["_starter"] = existing["starter"].map(lambda value: normalize_text(value) in {"si", "true", "1", "yes"})
        existing["_minutes"] = pd.to_numeric(existing["minutes_observed"], errors="coerce").fillna(0)
        existing = existing.sort_values(["_starter", "_minutes"], ascending=[False, False])

    player_by_id = {str(row["player_id"]): row for _, row in players.iterrows()}
    used_ids: set[str] = set()
    rows: List[Dict[str, object]] = []

    def observation_row(player_id: str) -> pd.Series | None:
        found = existing[existing["player_id"].astype(str) == str(player_id)]
        return found.iloc[0] if not found.empty else None

    for slot_key, label, _x, _y in FORMATION_TEMPLATES[formation]:
        position = FORMATION_SLOT_POSITIONS.get(slot_key, "")
        chosen_id = ""
        # Prefer a previously saved starter in the same/compatible position.
        if not existing.empty:
            candidates = existing[(existing["_starter"]) & (~existing["player_id"].astype(str).isin(used_ids))]
            same = candidates[candidates["observed_position"].astype(str) == position]
            if not same.empty:
                chosen_id = str(same.iloc[0]["player_id"])
            elif not candidates.empty:
                chosen_id = str(candidates.iloc[0]["player_id"])
        if not chosen_id:
            candidates = roster[(roster["primary_position"].astype(str) == position) & (~roster["player_id"].astype(str).isin(used_ids))]
            if not candidates.empty:
                chosen_id = str(candidates.iloc[0]["player_id"])
        used_ids.add(chosen_id) if chosen_id else None
        player = player_by_id.get(chosen_id)
        obs = observation_row(chosen_id) if chosen_id else None
        rows.append({
            "Demarcación": label,
            "Jugador": str(player.get("display_name", "")) if player is not None else "",
            "Jugador nuevo": "",
            "Posición": str(obs.get("observed_position", position)) if obs is not None else position,
            "Minutos": int(_float_or(obs.get("minutes_observed"), 90)) if obs is not None else 90,
            "Nota": _float_or(obs.get("global_rating"), 0.0) if obs is not None else 0.0,
            "MVP": normalize_text(obs.get("mvp", "")) in {"si", "true", "1", "yes", "mvp"} if obs is not None else False,
            "Notas": str(obs.get("positive_notes", "")) if obs is not None else "",
        })

    # Previously saved substitutes are always shown, followed by a few blank rows.
    if not existing.empty:
        remaining = existing[~existing["player_id"].astype(str).isin(used_ids)]
        for _, obs in remaining.iterrows():
            pid = str(obs.get("player_id", ""))
            player = player_by_id.get(pid)
            rows.append({
                "Demarcación": "Suplente", "Jugador": str(player.get("display_name", "")) if player is not None else str(obs.get("player", "")),
                "Jugador nuevo": "", "Posición": str(obs.get("observed_position", "")),
                "Minutos": int(_float_or(obs.get("minutes_observed"), 0)), "Nota": _float_or(obs.get("global_rating"), 0.0),
                "MVP": normalize_text(obs.get("mvp", "")) in {"si", "true", "1", "yes", "mvp"},
                "Notas": str(obs.get("positive_notes", "")),
            })
    for index in range(1, 5):
        rows.append({"Demarcación": f"Suplente {index}", "Jugador": "", "Jugador nuevo": "", "Posición": "", "Minutos": 0, "Nota": 0.0, "MVP": False, "Notas": ""})
    return pd.DataFrame(rows)

def _match_scoring_grid(match_id: str, team_id: str, side: str) -> None:
    matches = load_table("matches")
    match_rows = matches[matches["match_id"].astype(str) == str(match_id)]
    if match_rows.empty:
        st.error("Partido no encontrado.")
        return
    match = match_rows.iloc[0]
    formation_field = "home_formation" if side == "Local" else "away_formation"
    current_formation = str(match.get(formation_field, "")) or "4-3-3"
    formations = list(FORMATION_TEMPLATES)
    c1, c2 = st.columns([1, 2])
    formation = c1.selectbox("Formación", formations, index=_safe_index(formations, current_formation), key=f"desk_form_{match_id}_{team_id}")
    c2.info("Modo rápido: jugador, minutos, nota, MVP y una nota corta. El resto se aplica con valores sensatos por defecto.")

    viewing, reliability, trend = "Partido completo", "Alta", "Mantiene"
    opposition, difficulty = "Medio", "Media"
    with st.expander("Contexto avanzado del visionado (opcional)"):
        a1, a2, a3, a4, a5 = st.columns(5)
        viewing = a1.selectbox("Visionado", VIEWING_TYPES, index=_safe_index(VIEWING_TYPES, viewing), key=f"desk_view_{match_id}_{team_id}")
        reliability = a2.selectbox("Fiabilidad", RELIABILITY_LEVELS, index=_safe_index(RELIABILITY_LEVELS, reliability), key=f"desk_rel_{match_id}_{team_id}")
        opposition = a3.selectbox("Nivel rival", OPPOSITION_LEVELS, index=_safe_index(OPPOSITION_LEVELS, opposition), key=f"desk_opp_{match_id}_{team_id}")
        difficulty = a4.selectbox("Dificultad", MATCH_DIFFICULTIES, index=_safe_index(MATCH_DIFFICULTIES, difficulty), key=f"desk_diff_{match_id}_{team_id}")
        trend = a5.selectbox("Tendencia", TREND_LEVELS, index=_safe_index(TREND_LEVELS, trend), key=f"desk_trend_{match_id}_{team_id}")

    players = load_table("players")
    roster = players[players["current_team_id"].astype(str) == str(team_id)].sort_values("display_name")
    names = roster["display_name"].astype(str).tolist()
    grid = _match_grid_base(match_id, team_id, formation)
    edited = st.data_editor(
        grid, use_container_width=True, hide_index=True, num_rows="dynamic", key=f"desk_grid_{match_id}_{team_id}_{formation}",
        column_config={
            "Demarcación": st.column_config.TextColumn(disabled=True, width="medium"),
            "Jugador": st.column_config.SelectboxColumn(options=[""] + names, width="large"),
            "Jugador nuevo": st.column_config.TextColumn(width="large", help="Escríbelo aquí si aún no está en la plantilla."),
            "Posición": st.column_config.SelectboxColumn(options=[""] + POSITIONS, width="small"),
            "Minutos": st.column_config.NumberColumn(min_value=0, max_value=130, step=1, width="small"),
            "Nota": st.column_config.NumberColumn(min_value=0.0, max_value=10.0, step=0.5, format="%.1f", width="small"),
            "MVP": st.column_config.CheckboxColumn(width="small"),
            "Notas": st.column_config.TextColumn(width="large"),
        },
    )
    move_existing = st.checkbox("Mover al equipo si un nombre nuevo ya existía en otro club", value=False, key=f"desk_move_{match_id}_{team_id}")
    st.caption("Puedes volver al partido y corregir notas: se actualiza la fila existente, no se duplica.")
    if st.button(f"Guardar {side.lower()}", type="primary", key=f"desk_save_{match_id}_{team_id}"):
        name_to_id = dict(zip(roster["display_name"].astype(str), roster["player_id"].astype(str)))
        created_players = created_obs = updated_obs = skipped = 0
        warnings: List[str] = []
        for row_index, row in edited.iterrows():
            selected_name = str(row.get("Jugador", "")).strip()
            new_name = str(row.get("Jugador nuevo", "")).strip()
            player_id = name_to_id.get(selected_name, "")
            if not player_id and new_name:
                player_id, created, _ = add_player(
                    new_name, current_team_id=team_id, primary_position=str(row.get("Posición", "")), status="Sin valorar",
                )
                created_players += int(created)
                if not created:
                    existing_players = load_table("players")
                    existing_row = existing_players[existing_players["player_id"].astype(str) == str(player_id)]
                    if not existing_row.empty:
                        old_team = str(existing_row.iloc[0].get("current_team_id", ""))
                        if old_team and old_team != str(team_id) and not move_existing:
                            warnings.append(f"{new_name}: ya existe en otro equipo; no se ha puntuado.")
                            continue
                        if move_existing:
                            update_row("players", player_id, {"current_team_id": team_id})
            if not player_id:
                continue
            player_rows = load_table("players")
            player_row = player_rows[player_rows["player_id"].astype(str) == str(player_id)]
            primary_role = str(player_row.iloc[0].get("primary_role", "")) if not player_row.empty else ""
            minutes = int(_float_or(row.get("Minutos"), 0))
            rating = _float_or(row.get("Nota"), 0.0)
            mvp = bool(row.get("MVP", False))
            notes = str(row.get("Notas", "")).strip()
            is_starter = row_index < len(FORMATION_TEMPLATES[formation]) and not str(row.get("Demarcación", "")).lower().startswith("suplente")
            _, was_created, _ = save_match_observation(
                player_id=player_id, match_id=match_id, team_id=team_id,
                observed_position=str(row.get("Posición", "")), role=primary_role,
                minutes_observed=minutes, viewing_type=viewing, opposition_level=opposition,
                match_difficulty=difficulty, reliability=reliability, trend=trend,
                global_rating=rating if rating > 0 else "", starter="Sí" if is_starter else "No",
                mvp="Sí" if mvp else "No", positive_notes=notes,
            )
            created_obs += int(was_created)
            updated_obs += int(not was_created)
        update_row("matches", match_id, {"analyzed": "Sí", formation_field: formation})
        st.success(f"Jugadores nuevos: {created_players}. Observaciones creadas: {created_obs}. Actualizadas: {updated_obs}.")
        for warning in warnings:
            st.warning(warning)
        if not warnings:
            st.rerun()

def page_matches() -> None:
    hero("Registrar partido", "El flujo principal del Excel: selecciona un partido y registra a todos desde una tabla simple.", "Partido → nota", "Pocos clics")
    tabs = st.tabs(["Puntuar partido", "Crear partido", "Historial"])

    with tabs[0]:
        matches = enrich_data()["matches"].sort_values("match_date", ascending=False)
        if matches.empty:
            st.info("Primero crea un partido en la pestaña ‘Crear partido’.")
        else:
            match_id = _select_from_df("Partido", matches, "match_id", "match_name", "desk_match")
            if match_id:
                match = matches[matches["match_id"].astype(str) == str(match_id)].iloc[0]
                st.caption(f"{match.get('match_date','')} · {match.get('competition','')} · {match.get('season','')}")
                local_tab, away_tab = st.tabs([f"Local · {match.get('home_team','') or 'sin equipo'}", f"Visitante · {match.get('away_team','') or 'sin equipo'}"])
                with local_tab:
                    team_id = str(match.get("home_team_id", ""))
                    if team_id:
                        _match_scoring_grid(match_id, team_id, "Local")
                    else:
                        st.error("No hay equipo local asociado.")
                with away_tab:
                    team_id = str(match.get("away_team_id", ""))
                    if team_id:
                        _match_scoring_grid(match_id, team_id, "Visitante")
                    else:
                        st.error("No hay equipo visitante asociado.")

    with tabs[1]:
        team_type = st.radio("Tipo", TEAM_TYPES, horizontal=True, key="match_type")
        country_id = country_selector("País", "match_country")
        competition_id = competition_selector("Competición", country_id, "match_comp") if country_id else ""
        c1, c2 = st.columns(2)
        with c1:
            home = team_selector("Local", team_type, country_id, competition_id, "match_home") if country_id else ""
        with c2:
            away = team_selector("Visitante", team_type, country_id, competition_id, "match_away") if country_id else ""
        with st.form("new_match"):
            d1, d2, d3 = st.columns(3)
            match_date = d1.date_input("Fecha", value=date.today())
            season = d2.text_input("Temporada", placeholder="2026/27")
            analyzed = d3.checkbox("Ya analizado")
            s1, s2 = st.columns(2)
            score_home = s1.text_input("Goles local")
            score_away = s2.text_input("Goles visitante")
            context = st.text_area("Contexto opcional", placeholder="Jornada, sistemas, expulsiones, relevancia…")
            submitted = st.form_submit_button("Crear y abrir partido")
        if submitted:
            mid, created, message = add_match(
                match_date=str(match_date), competition_id=competition_id, home_team_id=home,
                away_team_id=away, season=season, context=context, score_home=score_home,
                score_away=score_away, analyzed="Sí" if analyzed else "No",
            )
            _message(created, message)
            if mid:
                _queue_widget_value("desk_match", mid)
                st.rerun()

    with tabs[2]:
        data = enrich_data()
        matches = data["matches"]
        observations = data["observations"]
        if matches.empty:
            empty_state("Sin partidos", "Crea el primero para contextualizar tus valoraciones.")
        else:
            summary = matches.copy()
            if not observations.empty:
                counts = observations.groupby("match_id").agg(Jugadores=("player_id", "nunique"), Minutos=("minutes_observed", lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum()), Nota_media=("global_rating", lambda x: pd.to_numeric(x, errors="coerce").replace(0, pd.NA).dropna().mean())).reset_index()
                summary = summary.merge(counts, on="match_id", how="left")
            cols = ["match_date", "match_name", "competition", "season", "score_home", "score_away", "analyzed", "Jugadores", "Nota_media", "context"]
            st.dataframe(summary[[c for c in cols if c in summary.columns]].sort_values("match_date", ascending=False), use_container_width=True, hide_index=True)

def page_observations() -> None:
    hero("Observaciones y rol", "Registra una nota rápida o profundiza con criterios específicos del rol. No necesitas rellenarlo todo durante el partido.", "Visionado", "Role fit")
    player_id = player_selector("Jugador", "obs_page_player")
    if not player_id:
        empty_state("Selecciona un jugador", "La observación rápida y la evaluación de rol aparecerán aquí.")
        return
    tabs = st.tabs(["Observación rápida", "Evaluación detallada del rol", "Historial"])
    with tabs[0]:
        player = load_table("players")
        row = player[player["player_id"].astype(str) == str(player_id)].iloc[0]
        _observation_form(player_id, str(row.get("current_team_id", "")), prefix="obs_page")
    with tabs[1]:
        _role_assessment_form(player_id)
    with tabs[2]:
        data = enrich_data()
        history = data["observations"][data["observations"]["player_id"].astype(str) == str(player_id)]
        if history.empty:
            st.info("Todavía no hay observaciones.")
        else:
            st.dataframe(history[["created_at", "match", "observed_position", "role", "minutes_observed", "global_rating", "reliability", "trend", "positive_notes", "improvement_notes"]].sort_values("created_at", ascending=False), use_container_width=True, hide_index=True)


def _role_assessment_form(player_id: str) -> None:
    players = load_table("players")
    row = players[players["player_id"].astype(str) == str(player_id)].iloc[0]
    default_role = str(row.get("primary_role", ""))
    position = str(row.get("primary_position", ""))
    role_options = [""] + roles_for_position(position)
    if default_role and default_role not in role_options:
        role_options.append(default_role)
    role = st.selectbox("Rol a evaluar", role_options, index=_safe_index(role_options, default_role))
    match_id = match_selector("Partido", "role_assessment_match", str(row.get("current_team_id", "")))
    if not role:
        st.info("Selecciona un rol. La app mostrará solo los criterios que importan para esa función.")
        return
    criteria = ROLE_PROFILES[role]["criteria"]
    values: Dict[str, Tuple[str, object, str]] = {}
    with st.form("role_assessment_form"):
        st.caption("Evalúa de 0 a 10. Puedes dejar criterios en 0 si no hubo evidencia suficiente.")
        for index, (key, label, weight, _fallback) in enumerate(criteria):
            col1, col2 = st.columns([1, 2])
            rating = col1.slider(f"{label} · {round(weight * 100)}%", 0.0, 10.0, 0.0, .5, key=f"ras_{key}")
            note = col2.text_input(f"Nota sobre {label.lower()}", key=f"ras_note_{key}")
            values[key] = (label, rating, note)
        submitted = st.form_submit_button("Guardar evaluación del rol")
    if submitted:
        save_role_assessment(player_id, match_id, role, values)
        update_row("players", player_id, {"primary_role": role})
        st.success("Evaluación guardada.")
        st.rerun()



def page_players() -> None:
    hero("Jugadores y edición", "Consulta una ficha o corrige de golpe nombres, equipos, posiciones y edades. La edición ya no está escondida.", "Base", "Corregir")
    data = enrich_data()
    players, observations, assessments, teams = data["players"], data["observations"], data["role_assessments"], data["teams"]
    if players.empty:
        empty_state("Sin jugadores", "Añade el primero desde ‘Alta y plantilla’ o durante un partido.")
        return
    metrics = metrics_table(players, observations, assessments, _weights())
    tabs = st.tabs(["Listado y ficha", "Edición rápida"])

    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        search = c1.text_input("Buscar", key="players_search")
        position = c2.multiselect("Posición", POSITIONS, key="players_pos")
        status = c3.multiselect("Estado", PLAYER_STATUS, key="players_status")
        team = c4.multiselect("Equipo", sorted(x for x in metrics["current_team"].unique().tolist() if x), key="players_team")
        filtered = metrics.copy()
        if search:
            filtered = filtered[filtered["display_name"].str.contains(search, case=False, na=False)]
        if position:
            filtered = filtered[filtered["primary_position"].isin(position)]
        if status:
            filtered = filtered[filtered["status"].isin(status)]
        if team:
            filtered = filtered[filtered["current_team"].isin(team)]
        display_cols = ["display_name", "current_team", "primary_position", "age", "matches_seen", "total_minutes", "average_rating", "mvp_count", "heritage_score", "priority_label", "confidence"]
        st.dataframe(filtered[[c for c in display_cols if c in filtered.columns]].sort_values("heritage_score", ascending=False), use_container_width=True, hide_index=True)
        st.divider()
        player_id = _select_from_df("Abrir jugador", filtered.sort_values("display_name"), "player_id", "display_name", "players_detail")
        if player_id:
            detail_tabs = st.tabs(["Ficha y scoring", "Editar jugador", "Historial"])
            with detail_tabs[0]:
                _player_profile(player_id, metrics, observations, assessments)
            with detail_tabs[1]:
                _player_edit_panel(player_id, "players_edit")
            with detail_tabs[2]:
                history = observations[observations["player_id"].astype(str) == str(player_id)].sort_values("created_at", ascending=False)
                if history.empty:
                    st.info("Todavía no hay observaciones.")
                else:
                    cols = ["created_at", "match", "team", "observed_position", "minutes_observed", "global_rating", "mvp", "positive_notes", "improvement_notes"]
                    st.dataframe(history[[c for c in cols if c in history.columns]], use_container_width=True, hide_index=True)

    with tabs[1]:
        st.caption("Pensado para errores de asignación: puedes mover a un jugador de Coria a Valladolid en una sola tabla.")
        q1, q2 = st.columns(2)
        quick_search = q1.text_input("Filtrar por nombre", key="quick_edit_search")
        quick_team = q2.multiselect("Filtrar por equipo actual", sorted(x for x in players["current_team"].unique().tolist() if x), key="quick_edit_team")
        editable = players.copy()
        if quick_search:
            editable = editable[editable["display_name"].str.contains(quick_search, case=False, na=False)]
        if quick_team:
            editable = editable[editable["current_team"].isin(quick_team)]
        team_labels = {"": "— Sin equipo —"}
        team_ids_by_label = {"— Sin equipo —": ""}
        for _, row in teams.sort_values(["country", "competition", "name"]).iterrows():
            label = " · ".join(x for x in [str(row.get("name", "")), str(row.get("competition", "")), str(row.get("country", ""))] if x)
            team_labels[str(row.get("team_id", ""))] = label
            team_ids_by_label[label] = str(row.get("team_id", ""))
        edit_df = editable[["player_id", "display_name", "current_team_id", "primary_position", "secondary_position", "age", "dominant_foot", "status"]].copy()
        edit_df["Equipo"] = edit_df["current_team_id"].map(team_labels).fillna("— Sin equipo —")
        edit_df["age"] = pd.to_numeric(edit_df["age"], errors="coerce").fillna(0).astype(int)
        edit_df = edit_df[["player_id", "display_name", "Equipo", "primary_position", "secondary_position", "age", "dominant_foot", "status"]]
        edited = st.data_editor(
            edit_df, use_container_width=True, hide_index=True, num_rows="fixed", key="players_quick_editor",
            column_config={
                "player_id": st.column_config.TextColumn(disabled=True),
                "display_name": st.column_config.TextColumn("Jugador", required=True, width="large"),
                "Equipo": st.column_config.SelectboxColumn(options=list(team_ids_by_label), width="large"),
                "primary_position": st.column_config.SelectboxColumn("Posición", options=[""] + POSITIONS, width="small"),
                "secondary_position": st.column_config.SelectboxColumn("Pos. secundaria", options=[""] + POSITIONS, width="small"),
                "age": st.column_config.NumberColumn("Edad", min_value=0, max_value=60, step=1, width="small"),
                "dominant_foot": st.column_config.SelectboxColumn("Pierna", options=FOOTS, width="small"),
                "status": st.column_config.SelectboxColumn("Estado", options=PLAYER_STATUS, width="medium"),
            },
        )
        if st.button("Guardar edición rápida", type="primary"):
            normalized = edited["display_name"].map(normalize_text)
            if (normalized == "").any():
                st.error("No puede haber nombres vacíos.")
            elif normalized.duplicated().any():
                st.error("La edición generaría dos jugadores con el mismo nombre normalizado.")
            else:
                for _, row in edited.iterrows():
                    update_row("players", str(row["player_id"]), {
                        "display_name": str(row["display_name"]).strip(), "normalized_name": normalize_text(row["display_name"]),
                        "current_team_id": team_ids_by_label.get(str(row["Equipo"]), ""),
                        "primary_position": row["primary_position"], "secondary_position": row["secondary_position"],
                        "age": int(_float_or(row["age"], 0)) or "", "dominant_foot": row["dominant_foot"], "status": row["status"],
                    })
                st.success(f"Jugadores actualizados: {len(edited)}.")
                st.rerun()

def _player_profile(player_id: str, metrics: pd.DataFrame, observations: pd.DataFrame, assessments: pd.DataFrame) -> None:
    player = metrics[metrics["player_id"].astype(str) == str(player_id)].iloc[0]
    obs = observations[observations["player_id"].astype(str) == str(player_id)]
    ass = assessments[assessments["player_id"].astype(str) == str(player_id)]
    score = scoring_breakdown(player, obs, ass, _weights())
    st.header(str(player["display_name"]))
    kpi_grid([
        ("Score Heras", score["heritage_score"], "good" if score["heritage_score"] >= 75 else "warn"),
        ("Nota media", score["average_rating"] or "—", ""),
        ("Partidos vistos", score["matches_seen"], ""),
        ("Minutos", score["total_minutes"], ""),
        ("MVP", score["mvp_count"], "good" if score["mvp_count"] else ""),
        ("Nota acumulada", score["rating_sum"], ""),
        ("Equipo", player.get("current_team", "—") or "—", ""),
        ("Posición", player.get("primary_position", "—") or "—", ""),
        ("Rol", score["role"] or "—", ""),
    ])
    left, right = st.columns([1.25, 1])
    with left:
        score_rows([
            ("Score Heras", score["heritage_score"], "Versión 0-100 de tu ranking Excel: nota, minutos, MVP y nivel competitivo."),
            ("Rendimiento ajustado", score["performance_adjusted"], "Score Heras contraído hacia 50 cuando la muestra aún es pequeña."),
            ("Proyección", score["projection_score"], "Rendimiento + potencial manual + ajuste moderado de edad."),
            ("Nivel observado", score["level"], "Rendimiento ponderado por posición y calidad de la evidencia."),
            ("Encaje de rol", score["role_fit"], f"Fuente: {score['role_source']}"),
            ("Potencial", score["potential"], "Valoración manual: no se bonifica solo por ser joven."),
            ("Necesidad", score["need"], "Urgencia de esa posición para tu proyecto."),
            ("Confianza", score["confidence"], "Muestra, minutos, fiabilidad, diversidad y consistencia."),
            ("Completitud", score["completeness"], "Calidad de la ficha; no hace mejor al jugador."),
        ])
    with right:
        priority_block(str(score["priority_label"]), score["decision_score"], str(score["next_action"]))
        signals(score["positive_signals"], score["alerts"])
    if score["criteria"]:
        labels = {key: label for key, label, _weight, _fallback in ROLE_PROFILES[str(score["role"])]["criteria"]}
        radar_svg([(labels.get(key, key), value) for key, value in score["criteria"].items()])
    if not obs.empty:
        st.subheader("Cronología de observaciones")
        st.dataframe(obs[["created_at", "match", "role", "starter", "minutes_observed", "viewing_type", "global_rating", "mvp", "reliability", "trend", "positive_notes", "improvement_notes"]].sort_values("created_at", ascending=False), use_container_width=True, hide_index=True)
    report = _report_markdown(player, score, obs)
    st.download_button("Descargar informe Markdown", report.encode("utf-8"), file_name=f"informe_{normalize_text(player['display_name']).replace(' ', '_')}.md", mime="text/markdown")


def _report_markdown(player: pd.Series, score: Mapping[str, object], observations: pd.DataFrame) -> str:
    lines = [
        f"# Informe de scouting — {player.get('display_name','')}", "",
        f"- Equipo: {player.get('current_team','')}",
        f"- Posición / rol: {player.get('primary_position','')} / {score.get('role','')}",
        f"- Prioridad: {score.get('priority_label','')} ({score.get('decision_score','')}/100)",
        f"- Score Heras: {score.get('heritage_score','')} · Nota media: {score.get('average_rating','')} · Partidos: {score.get('matches_seen','')} · Minutos: {score.get('total_minutes','')} · MVP: {score.get('mvp_count','')}",
        f"- Nivel: {score.get('level','')} · Encaje: {score.get('role_fit','')} · Potencial: {score.get('potential','')} · Confianza: {score.get('confidence','')}",
        f"- Próximo paso: {score.get('next_action','')}", "",
        "## Señales", "",
        *[f"- {item}" for item in score.get("positive_signals", [])], "",
        "## Alertas", "",
        *[f"- {item}" for item in score.get("alerts", [])], "",
        "## Observaciones", "",
    ]
    for _, row in observations.sort_values("created_at").iterrows():
        lines.extend([
            f"### {row.get('match','Sin partido')} · {row.get('created_at','')}",
            f"- Rol: {row.get('role','')} · Minutos: {row.get('minutes_observed','')} · Nota global: {row.get('global_rating','')} · MVP: {row.get('mvp','')}",
            f"- Positivo: {row.get('positive_notes','')}",
            f"- Dudas: {row.get('improvement_notes','')}", "",
        ])
    return "\n".join(lines)



def page_rankings() -> None:
    hero("Rankings", "Una tabla simple como tu Excel y, cuando lo necesites, capas de prioridad, confianza y rol.", "Score Heras", "Posición → rol")
    data = enrich_data()
    players, observations, assessments = data["players"], data["observations"], data["role_assessments"]
    if players.empty:
        empty_state("Sin ranking", "Añade jugadores y puntúa algún partido para activar el motor.")
        return

    c0, c1, c2, c3 = st.columns([1, 1.4, 1, 1.2])
    position = c0.selectbox("1. Posición", [""] + POSITIONS, key="ranking_position")
    role_options = [""] + roles_for_position(position) if position else [""]
    _sanitize_widget_value("ranking_role", role_options)
    role_override = c1.selectbox("2. Rol (opcional)", role_options, disabled=not bool(position), key="ranking_role", help="Primero posición; el rol solo refina el análisis.")
    labels = c2.multiselect("Prioridad", PRIORITY_LABELS)
    search = c3.text_input("Buscar jugador")

    metrics = metrics_table(players, observations, assessments, _weights(), role_override)
    df = metrics.copy()
    if position:
        df = df[df["primary_position"].astype(str) == position]
    if search:
        df = df[df["display_name"].str.contains(search, case=False, na=False)]

    f1, f2, f3, f4, f5 = st.columns(5)
    min_confidence = f1.slider("Confianza mínima", 0, 100, 0, 5)
    min_minutes = f2.number_input("Minutos mínimos", 0, 10000, 0, 30)
    minimum_observations = f3.number_input("Partidos mínimos", 0, 100, 0, 1)
    max_age = f4.number_input("Edad máxima", 0, 60, 60, 1)
    selected_teams = f5.multiselect("Equipo", sorted(x for x in df["current_team"].unique().tolist() if x))
    only_rated = st.checkbox("Mostrar solo jugadores con nota", value=True)

    if labels:
        df = df[df["priority_label"].isin(labels)]
    if selected_teams:
        df = df[df["current_team"].isin(selected_teams)]
    ages = pd.to_numeric(df["age"], errors="coerce")
    if max_age < 60:
        df = df[(ages <= max_age) | ages.isna()]
    df = df[(df["confidence"] >= min_confidence) & (df["total_minutes"] >= min_minutes) & (df["matches_seen"] >= minimum_observations)]
    if only_rated:
        df = df[df["rated_observations"] > 0]
    if df.empty:
        st.info("No hay jugadores con esos filtros.")
        return

    df = df.copy()
    df["#"] = df["heritage_score"].rank(method="min", ascending=False).astype(int)
    tabs = st.tabs(["Tabla Excel", "Rendimiento", "Prioridad", "Encaje de rol", "Confianza", "Segunda observación"])
    with tabs[0]:
        st.caption("Equivale a Dim_Jugadores + His_Rank: las columnas que usabas, calculadas automáticamente desde cada jugador-partido.")
        excel_cols = ["#", "display_name", "current_team", "primary_position", "age", "matches_seen", "total_minutes", "average_rating", "mvp_count", "competition_value", "rating_sum", "avg_minutes", "heritage_score", "legacy_raw"]
        table = df.sort_values(["heritage_score", "confidence"], ascending=[False, False])[[c for c in excel_cols if c in df.columns]].copy()
        table = table.rename(columns={
            "display_name":"Jugador", "current_team":"Equipo", "primary_position":"Posición", "age":"Edad",
            "matches_seen":"PartidosV", "total_minutes":"MinutosTotal", "average_rating":"NotaMedia",
            "mvp_count":"MVPtot", "competition_value":"Valoración", "rating_sum":"NotaAcum",
            "avg_minutes":"MinutosPart", "heritage_score":"Score Heras", "legacy_raw":"Rank original",
        })
        st.dataframe(table.head(500), use_container_width=True, hide_index=True)
    with tabs[1]:
        cols = ["#", "display_name", "current_team", "primary_position", "matches_seen", "total_minutes", "average_rating", "rating_sum", "mvp_count", "mvp_rate", "competition_value", "avg_minutes", "heritage_score", "performance_adjusted", "consistency", "confidence"]
        st.dataframe(df.sort_values(["heritage_score", "confidence"], ascending=[False, False])[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True)
    with tabs[2]:
        cols = ["display_name", "current_team", "primary_position", "decision_score", "base_score", "heritage_score", "projection_score", "potential", "need", "trend", "confidence", "priority_label", "next_action", "alerts_text"]
        st.dataframe(df.sort_values(["decision_score", "confidence"], ascending=[False, False])[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True)
    with tabs[3]:
        if not role_override:
            st.info("Selecciona una posición y después un rol para que esta pestaña compare un rol concreto.")
        cols = ["display_name", "current_team", "primary_position", "role", "role_fit", "heritage_score", "confidence", "total_minutes", "observation_count"]
        st.dataframe(df.sort_values(["role_fit", "confidence"], ascending=[False, False])[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True)
    with tabs[4]:
        cols = ["display_name", "current_team", "confidence", "completeness", "matches_seen", "total_minutes", "avg_minutes", "rated_observations", "observation_count", "alerts_text"]
        st.dataframe(df.sort_values("confidence", ascending=False)[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True)
    with tabs[5]:
        target = df[(df["heritage_score"] >= 68) & (df["confidence"] < 60)]
        st.caption("Buena señal de rendimiento, pero todavía falta evidencia.")
        cols = ["display_name", "current_team", "primary_position", "average_rating", "matches_seen", "total_minutes", "heritage_score", "confidence", "next_action"]
        st.dataframe(target.sort_values(["heritage_score", "confidence"], ascending=[False, True])[[c for c in cols if c in target.columns]], use_container_width=True, hide_index=True)
    st.scatter_chart(df, x="confidence", y="heritage_score", size="matches_seen", color="priority_label", use_container_width=True)

def page_excel_summary() -> None:
    hero("Resumen estilo Excel", "Las cuatro vistas que hacían eficaz tu archivo: hechos, jugadores agregados, equipos y ranking.", "BBDD Personal", "Automático")
    data = enrich_data()
    players, teams, matches, observations, assessments = data["players"], data["teams"], data["matches"], data["observations"], data["role_assessments"]
    metrics = metrics_table(players, observations, assessments, _weights()) if not players.empty else pd.DataFrame()
    tabs = st.tabs(["Dim_Jugadores", "Hechos_Stats", "Dim_Equipos", "His_Rank"])
    with tabs[0]:
        if metrics.empty:
            st.info("Sin jugadores.")
        else:
            cols = ["display_name", "current_team", "primary_position", "age", "matches_seen", "total_minutes", "average_rating", "mvp_count", "competition_value", "rating_sum", "avg_minutes", "heritage_score", "legacy_raw"]
            out = metrics[[c for c in cols if c in metrics.columns]].rename(columns={
                "display_name":"Jugador", "current_team":"Equipo", "primary_position":"Posición", "age":"Edad",
                "matches_seen":"PartidosV", "total_minutes":"MinutosTotal", "average_rating":"NotaMedia", "mvp_count":"MVPtot",
                "competition_value":"Valoracion", "rating_sum":"NotaAcum", "avg_minutes":"MinutosPart", "heritage_score":"Score100", "legacy_raw":"RankOriginal",
            })
            st.dataframe(out.sort_values("Score100", ascending=False), use_container_width=True, hide_index=True)
    with tabs[1]:
        if observations.empty:
            st.info("Sin observaciones.")
        else:
            facts = observations.copy()
            match_date_map = dict(zip(matches["match_id"], matches["match_date"])) if not matches.empty else {}
            facts["Fecha"] = facts["match_id"].map(match_date_map).fillna("")
            facts["MVP"] = facts["mvp"].map(lambda value: 1 if normalize_text(value) in {"si", "true", "1", "yes", "mvp"} else 0)
            facts = facts.rename(columns={"player":"Jugador", "minutes_observed":"Minutos", "match":"Partido", "global_rating":"Nota"})
            st.dataframe(facts[["Jugador", "Minutos", "Fecha", "Partido", "Nota", "MVP"]].sort_values(["Fecha", "Partido"], ascending=False), use_container_width=True, hide_index=True)
    with tabs[2]:
        if teams.empty:
            st.info("Sin equipos.")
        else:
            team_summary = teams[["team_id", "name", "competition", "country"]].copy()
            player_counts = players.groupby("current_team_id").size().rename("Jugadores").reset_index() if not players.empty else pd.DataFrame(columns=["current_team_id", "Jugadores"])
            observed_counts = observations.groupby("team_id")["player_id"].nunique().rename("Jugadores observados").reset_index() if not observations.empty else pd.DataFrame(columns=["team_id", "Jugadores observados"])
            match_counts = pd.concat([
                matches[["match_id", "home_team_id"]].rename(columns={"home_team_id":"team_id"}),
                matches[["match_id", "away_team_id"]].rename(columns={"away_team_id":"team_id"}),
            ]).groupby("team_id")["match_id"].nunique().rename("Partidos").reset_index() if not matches.empty else pd.DataFrame(columns=["team_id", "Partidos"])
            team_summary = team_summary.merge(player_counts, left_on="team_id", right_on="current_team_id", how="left").merge(observed_counts, left_on="team_id", right_on="team_id", how="left").merge(match_counts, left_on="team_id", right_on="team_id", how="left")
            team_summary = team_summary.rename(columns={"name":"Equipo", "competition":"Liga", "country":"País"})
            st.dataframe(team_summary[["Equipo", "Liga", "País", "Jugadores", "Jugadores observados", "Partidos"]].fillna(0), use_container_width=True, hide_index=True)
    with tabs[3]:
        if metrics.empty:
            st.info("Sin ranking.")
        else:
            rank = metrics.sort_values("heritage_score", ascending=False).copy()
            rank["Orden"] = range(1, len(rank) + 1)
            rank = rank.rename(columns={"display_name":"Jugador", "current_team":"Equipo", "primary_position":"Posición", "heritage_score":"RANK"})
            st.dataframe(rank[["Orden", "Jugador", "Equipo", "Posición", "RANK", "confidence", "priority_label"]], use_container_width=True, hide_index=True)


def page_role_lab() -> None:
    hero("Laboratorio de roles", "Ranking por rol, radar, percentiles y jugadores similares sin depender de matplotlib ni Plotly.", "Role scoring", "Comparación")
    data = enrich_data()
    players, observations, assessments = data["players"], data["observations"], data["role_assessments"]
    if players.empty:
        empty_state("Sin jugadores", "El laboratorio se activa cuando exista al menos un jugador.")
        return
    role = st.selectbox("Rol", ROLE_NAMES)
    eligible = ROLE_PROFILES[role]["positions"]
    candidates = players[players["primary_position"].isin(eligible)].copy()
    if candidates.empty:
        candidates = players.copy()
        st.caption("No hay jugadores en las posiciones naturales del rol; se muestran todos para no bloquear el análisis.")
    metrics = metrics_table(candidates, observations, assessments, _weights(), role)
    tabs = st.tabs(["Ranking", "Radar", "Percentiles", "Comparador", "Distribución", "Similitud", "Scatter"])
    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        foot = c1.multiselect("Pie", [x for x in FOOTS if x])
        max_age = c2.slider("Edad máxima", 0, 45, 45, key="role_age")
        min_minutes = c3.slider("Minutos mínimos", 0, 900, 0, 30, key="role_minutes")
        ranked = metrics.copy()
        if foot:
            ranked = ranked[ranked["dominant_foot"].isin(foot)]
        ages = pd.to_numeric(ranked["age"], errors="coerce")
        if max_age < 45:
            ranked = ranked[(ages <= max_age) | ages.isna()]
        ranked = ranked[ranked["minutes"] >= min_minutes]
        cols = ["display_name", "current_team", "primary_position", "age", "minutes", "observation_count", "role_fit", "level", "decision_score", "confidence", "priority_label"]
        st.dataframe(ranked.sort_values(["role_fit", "confidence"], ascending=False)[cols], use_container_width=True, hide_index=True)
    with tabs[1]:
        _radar_tab(role, candidates, observations, assessments)
    with tabs[2]:
        _percentile_tab(role, candidates, observations, assessments)
    with tabs[3]:
        _comparison_tab(role, candidates, observations, assessments)
    with tabs[4]:
        metric_name = st.selectbox("Métrica", ["role_fit", "level", "decision_score", "confidence"], format_func=lambda x: {"role_fit":"Encaje de rol", "level":"Nivel observado", "decision_score":"Prioridad", "confidence":"Confianza"}[x])
        strip_plot([(str(r["display_name"]), float(r[metric_name]), str(r["priority_label"])) for _, r in metrics.iterrows()], f"Distribución · {metric_name}")
    with tabs[5]:
        _similarity_tab(role, candidates, observations, assessments)
    with tabs[6]:
        st.scatter_chart(metrics, x="confidence", y="role_fit", size="minutes", color="priority_label", use_container_width=True)
        st.dataframe(metrics[["display_name", "current_team", "role_fit", "confidence", "minutes", "decision_score"]].sort_values("role_fit", ascending=False), use_container_width=True, hide_index=True)


def _radar_tab(role: str, candidates: pd.DataFrame, observations: pd.DataFrame, assessments: pd.DataFrame) -> None:
    c1, c2 = st.columns(2)
    p1 = _select_from_df("Jugador de referencia", candidates.sort_values("display_name"), "player_id", "display_name", "radar_p1")
    p2 = _select_from_df("Comparar con", candidates.sort_values("display_name"), "player_id", "display_name", "radar_p2", "— Sin comparación —")
    if not p1:
        st.info("Selecciona un jugador.")
        return
    row1 = candidates[candidates["player_id"].astype(str) == str(p1)].iloc[0]
    obs1 = observations[observations["player_id"].astype(str) == str(p1)]
    ass1 = assessments[assessments["player_id"].astype(str) == str(p1)]
    values1, source1 = criterion_scores(row1, obs1, ass1, role)
    labels = {key: label for key, label, _weight, _fallback in ROLE_PROFILES[role]["criteria"]}
    primary = [(labels[key], value) for key, value in values1.items()]
    comparison = None
    if p2:
        row2 = candidates[candidates["player_id"].astype(str) == str(p2)].iloc[0]
        obs2 = observations[observations["player_id"].astype(str) == str(p2)]
        ass2 = assessments[assessments["player_id"].astype(str) == str(p2)]
        values2, _source2 = criterion_scores(row2, obs2, ass2, role)
        comparison = [(labels.get(key, key), values2.get(key, 0)) for key in values1]
    st.caption(f"Fuente del perfil principal: {source1}.")
    radar_svg(primary, comparison)


def _percentile_tab(role: str, candidates: pd.DataFrame, observations: pd.DataFrame, assessments: pd.DataFrame) -> None:
    player_id = _select_from_df("Jugador", candidates.sort_values("display_name"), "player_id", "display_name", "percentile_player")
    if not player_id:
        return
    criterion_matrix: Dict[str, List[float]] = {}
    selected_values: Dict[str, float] = {}
    labels = {key: label for key, label, _weight, _fallback in ROLE_PROFILES[role]["criteria"]}
    for _, player in candidates.iterrows():
        pid = str(player["player_id"])
        obs = observations[observations["player_id"].astype(str) == pid]
        ass = assessments[assessments["player_id"].astype(str) == pid]
        values, _source = criterion_scores(player, obs, ass, role)
        for key, value in values.items():
            criterion_matrix.setdefault(key, []).append(value)
        if pid == player_id:
            selected_values = values
    items = []
    for key, value in selected_values.items():
        items.append((labels.get(key, key), value, percentile(pd.Series(criterion_matrix.get(key, [])), value)))
    percentile_bars(items)



def _comparison_tab(role: str, candidates: pd.DataFrame, observations: pd.DataFrame, assessments: pd.DataFrame) -> None:
    c1, c2 = st.columns(2)
    p1 = _select_from_df("Jugador A", candidates.sort_values("display_name"), "player_id", "display_name", "compare_a")
    p2 = _select_from_df("Jugador B", candidates.sort_values("display_name"), "player_id", "display_name", "compare_b")
    if not p1 or not p2:
        st.info("Selecciona dos jugadores.")
        return
    rows = []
    vectors = []
    labels = {key: label for key, label, _weight, _fallback in ROLE_PROFILES[role]["criteria"]}
    for pid in [p1, p2]:
        player = candidates[candidates["player_id"].astype(str) == str(pid)].iloc[0]
        obs = observations[observations["player_id"].astype(str) == str(pid)]
        ass = assessments[assessments["player_id"].astype(str) == str(pid)]
        score = scoring_breakdown(player, obs, ass, _weights(), role)
        rows.append({"Jugador": player.get("display_name", ""), "Equipo": player.get("current_team", ""), "Nivel": score["level"], "Encaje": score["role_fit"], "Potencial": score["potential"], "Confianza": score["confidence"], "Prioridad": score["decision_score"]})
        vectors.append([(labels.get(key, key), value) for key, value in score["criteria"].items()])
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if vectors[0]:
        radar_svg(vectors[0], vectors[1] if vectors[1] else None)

def _similarity_tab(role: str, candidates: pd.DataFrame, observations: pd.DataFrame, assessments: pd.DataFrame) -> None:
    player_id = _select_from_df("Jugador de referencia", candidates.sort_values("display_name"), "player_id", "display_name", "similarity_player")
    if not player_id:
        return
    reference = candidates[candidates["player_id"].astype(str) == str(player_id)].iloc[0]
    result = similarity_table(reference, candidates, observations, assessments, role)
    if result.empty:
        st.info("No hay suficientes perfiles comparables. Añade evaluaciones de rol u observaciones con notas macro.")
        return
    st.dataframe(result.head(20), use_container_width=True, hide_index=True)


def page_lineups() -> None:
    hero("Constructor de alineaciones", "Selecciona una formación, asigna roles y coloca jugadores. La alineación sirve como shortlist contextual, no como once automático incuestionable.", "Alineación", "Roles")
    players = enrich_data()["players"]
    formation = st.selectbox("Formación", list(FORMATION_TEMPLATES))
    template = FORMATION_TEMPLATES[formation]
    if players.empty:
        empty_state("Sin jugadores", "Puedes diseñar la estructura, pero necesitas jugadores para completar los puestos.")
    options = [""] + players["player_id"].astype(str).tolist()
    player_labels = {"": "— Vacío —"}
    player_labels.update(dict(zip(players["player_id"].astype(str), players["display_name"].astype(str))))
    slots: Dict[str, Dict[str, object]] = {}
    st.caption("Cada puesto permite escoger jugador y rol. Se guarda como una foto de trabajo independiente de la ficha del jugador.")
    for start in range(0, len(template), 3):
        columns = st.columns(3)
        for col, (slot_key, slot_label, _x, _y) in zip(columns, template[start:start + 3]):
            with col:
                st.markdown(f"**{slot_label}**")
                pid = st.selectbox("Jugador", options, format_func=lambda value: player_labels.get(value, value), key=f"lineup_player_{formation}_{slot_key}", label_visibility="collapsed")
                role = st.selectbox("Rol", [""] + ROLE_NAMES, key=f"lineup_role_{formation}_{slot_key}", label_visibility="collapsed")
                score = ""
                if pid:
                    row = players[players["player_id"].astype(str) == str(pid)].iloc[0]
                    score = row.get("primary_position", "")
                    slots[slot_key] = {"player": row.get("display_name", ""), "role": role, "score": score, "player_id": pid}
                else:
                    slots[slot_key] = {"player": slot_label, "role": role, "score": "", "player_id": ""}
    render_lineup(formation, slots)
    c1, c2 = st.columns([2, 1])
    name = c1.text_input("Nombre de la alineación", placeholder="Shortlist 4-2-3-1 · España U21")
    notes = c2.text_input("Notas")
    if st.button("Guardar alineación", type="primary"):
        if not name.strip():
            st.error("Pon un nombre a la alineación.")
        else:
            lineup_id = append_row("lineups", {"name": name, "formation": formation, "notes": notes})
            for slot_key, slot_label, x, y in template:
                data = slots.get(slot_key, {})
                append_row("lineup_slots", {
                    "lineup_id": lineup_id, "slot_key": slot_key, "slot_label": slot_label,
                    "player_id": data.get("player_id", ""), "role_name": data.get("role", ""), "x": x, "y": y,
                })
            st.success("Alineación guardada.")
    saved = load_table("lineups")
    if not saved.empty:
        st.subheader("Alineaciones guardadas")
        st.dataframe(saved[["name", "formation", "notes", "created_at"]].sort_values("created_at", ascending=False), use_container_width=True, hide_index=True)


def page_research() -> None:
    hero("Investigación", "Convierte tu base en preguntas medibles: cobertura, fuentes, edades, roles y calidad de decisión.", "Análisis", "Preguntas")
    data = enrich_data()
    players, observations, assessments, teams = data["players"], data["observations"], data["role_assessments"], data["teams"]
    metrics = metrics_table(players, observations, assessments, _weights()) if not players.empty else pd.DataFrame()
    avg_age = pd.to_numeric(players.get("age", pd.Series(dtype=float)), errors="coerce").mean() if not players.empty else None
    kpi_grid([
        ("Edad media", f"{avg_age:.1f}" if pd.notna(avg_age) else "—", ""),
        ("Sin segunda observación", int((metrics["observation_count"] < 2).sum()) if not metrics.empty else 0, "warn"),
        ("Confianza ≥ 70", int((metrics["confidence"] >= 70).sum()) if not metrics.empty else 0, "good"),
        ("Roles evaluados", assessments["role_name"].nunique() if not assessments.empty else 0, ""),
    ])
    c1, c2 = st.columns(2)
    with c1:
        if not players.empty:
            values = players["primary_position"].replace("", "Sin posición").value_counts().head(12)
            progress_list("Cobertura por posición", list(zip(values.index.tolist(), values.astype(int).tolist())))
            values = players["source"].replace("", "Sin fuente").value_counts().head(10)
            progress_list("Canales de entrada", list(zip(values.index.tolist(), values.astype(int).tolist())))
    with c2:
        if not teams.empty:
            values = teams["competition"].replace("", "Sin competición").value_counts().head(10)
            progress_list("Cobertura por competición", list(zip(values.index.tolist(), values.astype(int).tolist())))
        if not metrics.empty:
            values = metrics["priority_label"].value_counts().reindex(PRIORITY_LABELS, fill_value=0)
            progress_list("Distribución de prioridad", list(zip(values.index.tolist(), values.astype(int).tolist())))
    st.markdown(
        """
        <div class="panel"><h3>Mapa de preguntas</h3><div class="mini-grid">
          <div class="mini-card"><div class="title">Cobertura</div><div class="sub">¿Qué posiciones, ligas o edades estás observando demasiado y cuáles tienes vacías?</div></div>
          <div class="mini-card"><div class="title">Calidad de decisión</div><div class="sub">¿Cuántos A/B+ tienen confianza suficiente y cuántos son solo una señal?</div></div>
          <div class="mini-card"><div class="title">Roles</div><div class="sub">¿Qué perfiles aparecen con mayor frecuencia y cuáles no encuentras en tu mercado?</div></div>
          <div class="mini-card"><div class="title">Fuentes</div><div class="sub">¿Qué canal produce jugadores que acaban subiendo de nivel?</div></div>
          <div class="mini-card"><div class="title">Sesgo</div><div class="sub">¿Estás premiando juventud, club grande o una buena primera impresión sin evidencia?</div></div>
          <div class="mini-card"><div class="title">Seguimiento</div><div class="sub">¿Quién lleva demasiado tiempo en ‘revisar’ sin un próximo paso concreto?</div></div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )


def page_data_quality() -> None:
    hero("Calidad y duplicados", "Controla nombres parecidos, referencias rotas y fichas incompletas antes de que la base crezca.", "Gobierno del dato", "Limpieza")
    data = enrich_data()
    players, observations, assessments = data["players"], data["observations"], data["role_assessments"]
    if players.empty:
        empty_state("Base limpia", "No hay jugadores ni duplicados porque la base está vacía.")
        return
    duplicates = players[players.duplicated("normalized_name", keep=False)].sort_values("normalized_name")
    orphan_obs = observations[~observations["player_id"].isin(players["player_id"])] if not observations.empty else observations
    orphan_ass = assessments[~assessments["player_id"].isin(players["player_id"])] if not assessments.empty else assessments
    metrics = metrics_table(players, observations, assessments, _weights())
    kpi_grid([
        ("Duplicados exactos", len(duplicates), "warn" if len(duplicates) else "good"),
        ("Observaciones huérfanas", len(orphan_obs), "warn" if len(orphan_obs) else "good"),
        ("Evaluaciones huérfanas", len(orphan_ass), "warn" if len(orphan_ass) else "good"),
        ("Fichas < 50%", int((metrics["completeness"] < 50).sum()), "warn"),
    ])
    if not duplicates.empty:
        st.dataframe(duplicates[["player_id", "display_name", "normalized_name", "current_team"]], use_container_width=True, hide_index=True)
    st.subheader("Fusionar jugadores")
    options = [""] + players["player_id"].astype(str).tolist()
    labels = {"": "— Seleccionar —"}
    labels.update(dict(zip(players["player_id"].astype(str), players["display_name"].astype(str))))
    c1, c2 = st.columns(2)
    keep_id = c1.selectbox("Ficha correcta", options, format_func=lambda value: labels.get(value, value), key="quality_keep")
    merge_id = c2.selectbox("Duplicado que se elimina", options, format_func=lambda value: labels.get(value, value), key="quality_merge")
    if st.button("Fusionar", disabled=not keep_id or not merge_id or keep_id == merge_id):
        merge_players(keep_id, merge_id)
        st.success("Fusión completada: observaciones y evaluaciones se han movido a la ficha correcta.")
        st.rerun()
    st.subheader("Buscar variantes")
    name = st.text_input("Nombre a comprobar", placeholder="Fabián Ruiz / Fabian Ruiz")
    if name:
        st.dataframe(duplicate_candidates(name, limit=15), use_container_width=True, hide_index=True)


def page_database() -> None:
    hero("Base editable", "Edición avanzada de las tablas. Utilízala para correcciones puntuales; para el trabajo normal es más seguro usar los formularios.", "Administración", "Data editor")
    table = st.selectbox("Tabla", list(SCHEMAS))
    df = load_table(table)
    edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key=f"editor_{table}")
    if st.button("Guardar cambios", type="primary"):
        save_table(table, edited)
        st.success("Cambios guardados.")
        st.rerun()


def page_import_export() -> None:
    hero("Importar, exportar y reiniciar", "La base empieza vacía. Exporta un ZIP al terminar cada sesión importante y podrás restaurarlo más adelante.", "Backup", "Portabilidad")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Backup ZIP", backup_zip_bytes(), file_name="scouting_hub_v11_backup.zip", mime="application/zip", use_container_width=True)
    c2.download_button("Excel técnico", excel_backup_bytes(), file_name="scouting_hub_v11_raw.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    c3.download_button("Excel estilo BBDD", excel_model_bytes(), file_name="BBDD_Personal_Scouting_Hub.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, help="Incluye Hechos_Stats, Dim_Jugadores, Dim_Equipos e His_Rank, además de las tablas técnicas.")
    st.subheader("Plantillas CSV vacías")
    columns = st.columns(3)
    for index, table in enumerate(SCHEMAS):
        columns[index % 3].download_button(
            f"{table}.csv", empty_table(table).to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{table}_template.csv", mime="text/csv", key=f"template_{table}", use_container_width=True,
        )
    st.divider()
    tabs = st.tabs(["Restaurar backup", "Importar CSV", "Reiniciar"])
    with tabs[0]:
        uploaded = st.file_uploader("ZIP o Excel", type=["zip", "xlsx"], key="restore_file")
        if uploaded and st.button("Restaurar", type="primary"):
            snapshot_data("before_restore")
            if uploaded.name.lower().endswith(".zip"):
                count, messages = restore_zip_bytes(uploaded.read())
            else:
                count, messages = restore_excel(uploaded), []
            st.success(f"Tablas restauradas: {count}.")
            for message in messages:
                st.warning(message)
            st.rerun()
    with tabs[1]:
        table = st.selectbox("Tabla destino", list(SCHEMAS), key="csv_table")
        replace = st.checkbox("Reemplazar tabla completa", value=False)
        csv_file = st.file_uploader("CSV", type=["csv"], key="csv_file")
        if csv_file and st.button("Importar CSV"):
            added, skipped = import_csv(table, csv_file, replace=replace)
            st.success(f"Filas importadas: {added}. Omitidas por ID existente: {skipped}.")
            st.rerun()
    with tabs[2]:
        st.warning("Esto borra países, competiciones, equipos, jugadores, partidos, observaciones, evaluaciones y alineaciones.")
        confirmation = st.text_input("Escribe BORRAR TODO")
        if st.button("Vaciar completamente la base", disabled=confirmation != "BORRAR TODO"):
            snapshot_data("before_reset")
            reset_all_data()
            st.success("Base vaciada. Solo quedan las cabeceras de los CSV.")
            st.rerun()



def page_settings() -> None:
    hero("Ajustes del scoring", "Configura el peso del Score Heras, el encaje de rol, el potencial, la necesidad y la tendencia. La confianza sigue actuando como freno de seguridad.", "Modelo", "Transparencia")
    settings = get_settings()
    current = dict(DEFAULT_SCORING_WEIGHTS)
    saved = settings.get("scoring_weights", {})
    if isinstance(saved, dict):
        current.update({key: value for key, value in saved.items() if key in current})
    with st.form("scoring_settings"):
        c1, c2, c3, c4, c5 = st.columns(5)
        heritage = c1.number_input("Score Heras", 0.0, 1.0, float(current["heritage"]), .05)
        role_fit = c2.number_input("Encaje", 0.0, 1.0, float(current["role_fit"]), .05)
        potential = c3.number_input("Potencial", 0.0, 1.0, float(current["potential"]), .05)
        need = c4.number_input("Necesidad", 0.0, 1.0, float(current["need"]), .05)
        trend = c5.number_input("Tendencia", 0.0, 1.0, float(current["trend"]), .05)
        submitted = st.form_submit_button("Guardar pesos")
    total = heritage + role_fit + potential + need + trend
    st.caption(f"Suma actual: {total:.2f}. La app normaliza automáticamente aunque no sea 1.00.")
    if submitted:
        settings["scoring_weights"] = {"heritage": heritage, "role_fit": role_fit, "potential": potential, "need": need, "trend": trend}
        save_settings(settings)
        st.success("Pesos guardados.")
        st.rerun()
    if st.button("Restaurar pesos recomendados"):
        settings["scoring_weights"] = DEFAULT_SCORING_WEIGHTS.copy()
        save_settings(settings)
        st.success("Pesos restaurados.")
        st.rerun()
    st.markdown(
        """
        <div class="panel"><h3>Qué entra en el Score Heras</h3><div class="mini-grid">
          <div class="mini-card"><div class="title">Nota media</div><div class="sub">Es la señal principal, suavizada durante los primeros partidos.</div></div>
          <div class="mini-card"><div class="title">Partidos y minutos</div><div class="sub">Dan estabilidad y una bonificación moderada de evidencia.</div></div>
          <div class="mini-card"><div class="title">MVP</div><div class="sub">Premia impacto diferencial, con rendimiento decreciente para no romper el ranking.</div></div>
          <div class="mini-card"><div class="title">Nivel competitivo</div><div class="sub">Usa el valor 1-50 guardado en la competición.</div></div>
          <div class="mini-card"><div class="title">Edad</div><div class="sub">Solo desempata ligeramente; no convierte juventud en potencial automático.</div></div>
          <div class="mini-card"><div class="title">Confianza separada</div><div class="sub">Una buena nota con poca muestra exige volver a observar.</div></div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )

