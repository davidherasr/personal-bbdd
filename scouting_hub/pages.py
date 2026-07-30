from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

import pandas as pd
import streamlit as st

from .config import (
    APP_TITLE, DEFAULT_SCORING_WEIGHTS, FOOTS, FORMATION_TEMPLATES, MANUAL_PRIORITIES,
    MATCH_DIFFICULTIES, OPPOSITION_LEVELS, PLAYER_STATUS, POSITIONS, PRIORITY_LABELS,
    RELIABILITY_LEVELS, ROLE_NAMES, ROLE_PROFILES, SOURCE_TYPES, TEAM_TYPES, TREND_LEVELS,
    VIEWING_TYPES, SCHEMAS,
)
from .domain import (
    add_competition, add_country, add_match, add_observation, add_player, add_team,
    duplicate_candidates, enrich_data, get_name, merge_players, save_role_assessment,
)
from .scoring import (
    criterion_scores, metrics_table, percentile, scoring_breakdown, similarity_table,
)
from .storage import (
    append_row, backup_zip_bytes, delete_rows, empty_table, excel_backup_bytes, get_settings,
    import_csv, load_table, normalize_text, reset_all_data, restore_excel, restore_zip_bytes,
    save_settings, save_table, snapshot_data, update_row,
)
from .visuals import (
    empty_state, hero, kpi_grid, percentile_bars, priority_block, progress_list, radar_svg,
    render_lineup, score_rows, signals, strip_plot,
)


def _message(created: bool, message: str) -> None:
    (st.success if created else st.info)(message)


def _select_from_df(label: str, df: pd.DataFrame, id_col: str, name_col: str, key: str, empty_label: str = "— Seleccionar —") -> str:
    options = [""] + df[id_col].astype(str).tolist() if not df.empty else [""]
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
                    st.session_state[key] = cid
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
        labels[str(row["competition_id"])] = f"{row['name']}{' · ' + suffix if suffix else ''}"
    selected = st.selectbox(label, options, format_func=lambda value: labels.get(value, value), key=key)
    if allow_add and country_id:
        with st.expander("+ Añadir competición"):
            c1, c2, c3 = st.columns([2, 1, 1])
            name = c1.text_input("Nombre", key=f"{key}_new_name")
            level = c2.text_input("Nivel", key=f"{key}_new_level", placeholder="1ª, 2ª, Sub-21…")
            season = c3.text_input("Temporada", key=f"{key}_new_season", placeholder="2026/27")
            if st.button("Guardar competición", key=f"{key}_save"):
                cid, created, message = add_competition(name, country_id, level, season)
                _message(created, message)
                if cid:
                    st.session_state[key] = cid
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
                    st.session_state[key] = tid
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
    kpi_grid([
        ("Jugadores", len(players), ""), ("Equipos / selecciones", len(teams), ""),
        ("Partidos", len(matches), ""), ("Observaciones", len(observations), "good"),
        ("Prioridades A/B+", priorities, "warn"), ("Confianza media", f"{avg_conf}%", ""),
        ("Completitud media", f"{avg_completion}%", "warn" if avg_completion < 60 else "good"),
        ("Evaluaciones de rol", len(assessments), ""),
    ])
    if players.empty:
        empty_state("Base vacía, como pediste", "Empieza en ‘Alta rápida’: crea país, competición, equipo y primer jugador. La app no incluye jugadores ni competiciones precargadas.")
        st.markdown("### Arranque recomendado")
        st.markdown(
            """
            <div class="panel"><div class="mini-grid">
              <div class="mini-card"><div class="title">1. Crea la estructura</div><div class="sub">País → competición → equipo o selección.</div></div>
              <div class="mini-card"><div class="title">2. Añade la plantilla</div><div class="sub">Carga jugadores uno a uno o por CSV vacío.</div></div>
              <div class="mini-card"><div class="title">3. Registra evidencia</div><div class="sub">Observación rápida primero; evaluación de rol cuando el jugador lo merezca.</div></div>
            </div></div>
            """,
            unsafe_allow_html=True,
        )
        return

    left, right = st.columns([2, 1])
    with left:
        action = metrics.sort_values(["decision_score", "confidence"], ascending=[False, True]).copy()
        columns = ["display_name", "current_team", "primary_position", "primary_role", "priority_label", "decision_score", "confidence", "next_action", "alerts_text"]
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
    hero("Alta rápida", "Flujo jerárquico anti-duplicados: contexto → plantilla → jugador existente o nuevo → observación.", "Trabajo diario", "Anti-duplicados")
    scope = st.radio("Contexto", TEAM_TYPES, horizontal=True)
    country_id = country_selector("País", "wf_country")
    competition_id = competition_selector("Competición / liga", country_id, "wf_comp") if scope == "Club" and country_id else ""
    team_id = team_selector("Equipo / selección", scope, country_id, competition_id, "wf_team") if country_id else ""
    if not team_id:
        st.info("Selecciona o crea un equipo para continuar.")
        return

    players = load_table("players")
    roster = players[players["current_team_id"].astype(str) == str(team_id)].sort_values("display_name")
    st.subheader("Plantilla")
    if roster.empty:
        st.warning("La plantilla está vacía.")
    else:
        st.dataframe(roster[["display_name", "primary_position", "primary_role", "age", "status", "manual_priority"]], use_container_width=True, hide_index=True)

    with st.expander("Carga rápida de nombres"):
        st.caption("Un jugador por línea. La normalización ignora tildes, mayúsculas y dobles espacios.")
        names = st.text_area("Nombres", height=160, placeholder="Jugador Uno\nJugador Dos")
        default_position = st.selectbox("Posición por defecto", [""] + POSITIONS)
        if st.button("Crear plantilla básica"):
            created = skipped = 0
            for line in names.splitlines():
                name = line.strip()
                if not name:
                    continue
                _, was_created, _ = add_player(name, nationality_id=country_id, current_team_id=team_id, primary_position=default_position, status="Sin valorar")
                created += int(was_created)
                skipped += int(not was_created)
            st.success(f"Creados: {created}. Ya existentes: {skipped}.")
            st.rerun()

    mode = st.segmented_control("Acción", ["Observar existente", "Crear jugador"], default="Observar existente")
    selected_player = ""
    if mode == "Observar existente":
        selected_player = player_selector("Jugador", "wf_player", team_id=team_id)
    else:
        name = st.text_input("Nombre completo", key="wf_new_name")
        candidates = duplicate_candidates(name)
        if name and not candidates.empty:
            st.warning("Antes de crear, revisa estas coincidencias:")
            st.dataframe(candidates, use_container_width=True, hide_index=True)
        with st.form("wf_new_player_form"):
            c1, c2, c3 = st.columns(3)
            position = c1.selectbox("Posición principal", [""] + POSITIONS)
            secondary = c2.selectbox("Posición secundaria", [""] + POSITIONS)
            foot = c3.selectbox("Pierna", FOOTS)
            c4, c5, c6 = st.columns(3)
            age = c4.number_input("Edad", min_value=0, max_value=55, value=0)
            height = c5.number_input("Altura (cm)", min_value=0, max_value=230, value=0)
            source = c6.selectbox("Fuente", SOURCE_TYPES)
            c7, c8 = st.columns(2)
            role = c7.selectbox("Rol principal", [""] + ROLE_NAMES)
            status = c8.selectbox("Estado", PLAYER_STATUS)
            potential = st.slider("Potencial manual", 0.0, 10.0, 5.0, .5, help="No se bonifica automáticamente por edad: tú valoras la proyección.")
            notes = st.text_area("Notas generales")
            submitted = st.form_submit_button("Crear jugador")
        if submitted:
            exact = candidates[candidates["similarity"] >= 99] if not candidates.empty else pd.DataFrame()
            if not exact.empty:
                st.error("No se ha creado: existe una coincidencia exacta o alias.")
            else:
                pid, created, message = add_player(
                    name, age=age or "", nationality_id=country_id, primary_position=position,
                    secondary_position=secondary, dominant_foot=foot, height_cm=height or "",
                    current_team_id=team_id, status=status, potential_rating=potential,
                    primary_role=role, source=source, general_notes=notes,
                )
                _message(created, message)
                if pid:
                    st.session_state["wf_player"] = pid
                    selected_player = pid
                st.rerun()

    if selected_player:
        st.divider()
        _observation_form(selected_player, team_id, prefix="wf")


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
        c1, c2, c3, c4 = st.columns(4)
        position = c1.selectbox("Posición observada", [""] + POSITIONS, index=([""] + POSITIONS).index(str(player.get("primary_position", ""))) if str(player.get("primary_position", "")) in POSITIONS else 0)
        role = c2.selectbox("Rol observado", [""] + ROLE_NAMES, index=([""] + ROLE_NAMES).index(str(player.get("primary_role", ""))) if str(player.get("primary_role", "")) in ROLE_NAMES else 0)
        minutes = c3.number_input("Minutos vistos", min_value=0, max_value=130, value=90)
        viewing = c4.selectbox("Tipo de visionado", VIEWING_TYPES)
        c5, c6, c7, c8 = st.columns(4)
        opposition = c5.selectbox("Nivel del rival", OPPOSITION_LEVELS)
        difficulty = c6.selectbox("Dificultad", MATCH_DIFFICULTIES)
        reliability = c7.selectbox("Fiabilidad", RELIABILITY_LEVELS)
        trend = c8.selectbox("Tendencia", TREND_LEVELS)
        st.caption("0 significa ‘sin puntuar’. El ranking ignora esa dimensión en vez de interpretarla como una nota pésima.")
        r1, r2, r3, r4, r5 = st.columns(5)
        technical = r1.slider("Técnica", 0.0, 10.0, 0.0, .5)
        tactical = r2.slider("Táctica", 0.0, 10.0, 0.0, .5)
        physical = r3.slider("Físico", 0.0, 10.0, 0.0, .5)
        mental = r4.slider("Mental", 0.0, 10.0, 0.0, .5)
        global_rating = r5.slider("Global", 0.0, 10.0, 0.0, .5)
        positive = st.text_area("Conductas positivas")
        improvements = st.text_area("Dudas / aspectos de mejora")
        next_step = st.text_input("Próximo paso manual", placeholder="Ver 90 minutos, comparar por rol, cerrar informe…")
        submitted = st.form_submit_button("Guardar observación")
    if submitted:
        _, created, message = add_observation(
            player_id=player_id, match_id=match_id, team_id=team_id or player.get("current_team_id", ""),
            observed_position=position, role=role, minutes_observed=minutes, viewing_type=viewing,
            opposition_level=opposition, match_difficulty=difficulty, reliability=reliability, trend=trend,
            technical_rating=technical, tactical_rating=tactical, physical_rating=physical,
            mental_rating=mental, global_rating=global_rating, positive_notes=positive,
            improvement_notes=improvements, next_step=next_step,
        )
        _message(created, message)


def page_matches() -> None:
    hero("Partidos", "Crea el contexto de visionado y vincula cada observación a un partido concreto.", "Contexto", "Evidencia")
    team_type = st.radio("Tipo", TEAM_TYPES, horizontal=True)
    country_id = country_selector("País", "match_country")
    competition_id = competition_selector("Competición", country_id, "match_comp") if country_id else ""
    home = team_selector("Local", team_type, country_id, competition_id, "match_home") if country_id else ""
    away = team_selector("Visitante", team_type, country_id, competition_id, "match_away") if country_id else ""
    with st.form("new_match"):
        c1, c2, c3 = st.columns(3)
        match_date = c1.date_input("Fecha", value=date.today())
        season = c2.text_input("Temporada", placeholder="2026/27")
        analyzed = c3.checkbox("Analizado")
        c4, c5 = st.columns(2)
        score_home = c4.text_input("Goles local")
        score_away = c5.text_input("Goles visitante")
        context = st.text_area("Contexto", placeholder="Jornada, competición, sistemas, expulsiones, relevancia…")
        submitted = st.form_submit_button("Guardar partido")
    if submitted:
        _, created, message = add_match(
            match_date=str(match_date), competition_id=competition_id, home_team_id=home,
            away_team_id=away, season=season, context=context, score_home=score_home,
            score_away=score_away, analyzed="Sí" if analyzed else "No",
        )
        _message(created, message)
        if created:
            st.rerun()
    matches = enrich_data()["matches"]
    if matches.empty:
        empty_state("Sin partidos", "Crea el primero para contextualizar tus observaciones.")
    else:
        st.dataframe(matches[["match_date", "match_name", "competition", "season", "score_home", "score_away", "analyzed", "context"]].sort_values("match_date", ascending=False), use_container_width=True, hide_index=True)


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
    role = st.selectbox("Rol a evaluar", [""] + ROLE_NAMES, index=([""] + ROLE_NAMES).index(default_role) if default_role in ROLE_NAMES else 0)
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
    hero("Jugadores", "Consulta la base y abre una ficha donde se separan nivel, encaje, potencial, confianza y prioridad.", "Base", "Ficha individual")
    data = enrich_data()
    players, observations, assessments = data["players"], data["observations"], data["role_assessments"]
    if players.empty:
        empty_state("Sin jugadores", "Añade el primero desde ‘Alta rápida’.")
        return
    metrics = metrics_table(players, observations, assessments, _weights())
    c1, c2, c3, c4 = st.columns(4)
    search = c1.text_input("Buscar")
    position = c2.multiselect("Posición", POSITIONS)
    status = c3.multiselect("Estado", PLAYER_STATUS)
    team = c4.multiselect("Equipo", sorted(x for x in metrics["current_team"].unique().tolist() if x))
    filtered = metrics.copy()
    if search:
        filtered = filtered[filtered["display_name"].str.contains(search, case=False, na=False)]
    if position:
        filtered = filtered[filtered["primary_position"].isin(position)]
    if status:
        filtered = filtered[filtered["status"].isin(status)]
    if team:
        filtered = filtered[filtered["current_team"].isin(team)]
    display_cols = ["display_name", "current_team", "primary_position", "primary_role", "age", "status", "priority_label", "decision_score", "confidence", "next_action"]
    st.dataframe(filtered[[c for c in display_cols if c in filtered.columns]].sort_values("decision_score", ascending=False), use_container_width=True, hide_index=True)

    st.divider()
    player_id = _select_from_df("Abrir ficha", filtered.sort_values("display_name"), "player_id", "display_name", "players_detail")
    if player_id:
        _player_profile(player_id, metrics, observations, assessments)


def _player_profile(player_id: str, metrics: pd.DataFrame, observations: pd.DataFrame, assessments: pd.DataFrame) -> None:
    player = metrics[metrics["player_id"].astype(str) == str(player_id)].iloc[0]
    obs = observations[observations["player_id"].astype(str) == str(player_id)]
    ass = assessments[assessments["player_id"].astype(str) == str(player_id)]
    score = scoring_breakdown(player, obs, ass, _weights())
    st.header(str(player["display_name"]))
    kpi_grid([
        ("Equipo", player.get("current_team", "—") or "—", ""),
        ("Posición", player.get("primary_position", "—") or "—", ""),
        ("Rol", score["role"] or "—", ""),
        ("Observaciones", score["observation_count"], "good" if score["observation_count"] >= 2 else "warn"),
    ])
    left, right = st.columns([1.25, 1])
    with left:
        score_rows([
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
        st.dataframe(obs[["created_at", "match", "role", "minutes_observed", "viewing_type", "global_rating", "reliability", "trend", "positive_notes", "improvement_notes"]].sort_values("created_at", ascending=False), use_container_width=True, hide_index=True)
    report = _report_markdown(player, score, obs)
    st.download_button("Descargar informe Markdown", report.encode("utf-8"), file_name=f"informe_{normalize_text(player['display_name']).replace(' ', '_')}.md", mime="text/markdown")


def _report_markdown(player: pd.Series, score: Mapping[str, object], observations: pd.DataFrame) -> str:
    lines = [
        f"# Informe de scouting — {player.get('display_name','')}", "",
        f"- Equipo: {player.get('current_team','')}",
        f"- Posición / rol: {player.get('primary_position','')} / {score.get('role','')}",
        f"- Prioridad: {score.get('priority_label','')} ({score.get('decision_score','')}/100)",
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
            f"- Rol: {row.get('role','')} · Minutos: {row.get('minutes_observed','')} · Nota global: {row.get('global_rating','')}",
            f"- Positivo: {row.get('positive_notes','')}",
            f"- Dudas: {row.get('improvement_notes','')}", "",
        ])
    return "\n".join(lines)


def page_rankings() -> None:
    hero("Rankings", "Ordena por rol y contexto. El score final se ajusta hacia 50 cuando la evidencia es baja, en lugar de inflar o hundir al jugador por una muestra mínima.", "Scoring", "Confianza")
    data = enrich_data()
    players, observations, assessments = data["players"], data["observations"], data["role_assessments"]
    if players.empty:
        empty_state("Sin ranking", "Añade jugadores y observaciones para activar el motor.")
        return
    role_override = st.selectbox("Rankear para un rol concreto", [""] + ROLE_NAMES, help="Vacío = rol principal de cada jugador.")
    metrics = metrics_table(players, observations, assessments, _weights(), role_override)
    c1, c2, c3, c4 = st.columns(4)
    positions = c1.multiselect("Posición", POSITIONS)
    labels = c2.multiselect("Prioridad", PRIORITY_LABELS)
    min_confidence = c3.slider("Confianza mínima", 0, 100, 0, 5)
    min_minutes = c4.slider("Minutos mínimos", 0, 900, 0, 30)
    c5, c6, c7 = st.columns(3)
    max_age = c5.slider("Edad máxima", 0, 45, 45)
    selected_teams = c6.multiselect("Equipo", sorted(x for x in metrics["current_team"].unique().tolist() if x))
    minimum_observations = c7.slider("Observaciones mínimas", 0, 5, 0)
    df = metrics.copy()
    if positions:
        df = df[df["primary_position"].isin(positions)]
    if labels:
        df = df[df["priority_label"].isin(labels)]
    if selected_teams:
        df = df[df["current_team"].isin(selected_teams)]
    ages = pd.to_numeric(df["age"], errors="coerce")
    if max_age < 45:
        df = df[(ages <= max_age) | ages.isna()]
    df = df[(df["confidence"] >= min_confidence) & (df["minutes"] >= min_minutes) & (df["observation_count"] >= minimum_observations)]
    if df.empty:
        st.info("No hay jugadores con esos filtros.")
        return
    columns = ["display_name", "current_team", "primary_position", "role", "priority_label", "decision_score", "base_score", "level", "role_fit", "potential", "need", "confidence", "minutes", "observation_count", "next_action", "alerts_text"]
    tabs = st.tabs(["Prioridad", "Nivel", "Encaje de rol", "Potencial", "Confianza", "Segunda observación", "Discrepancias"])
    sorts = [
        ("decision_score", False), ("level", False), ("role_fit", False), ("potential", False), ("confidence", False),
    ]
    for tab, (sort_col, ascending) in zip(tabs[:5], sorts):
        with tab:
            st.dataframe(df.sort_values([sort_col, "confidence"], ascending=[ascending, False])[[c for c in columns if c in df.columns]].head(250), use_container_width=True, hide_index=True)
    with tabs[5]:
        target = df[(df["base_score"] >= 70) & (df["confidence"] < 60)]
        st.caption("Buena señal, evidencia todavía insuficiente.")
        st.dataframe(target.sort_values(["base_score", "confidence"], ascending=[False, True])[[c for c in columns if c in target.columns]], use_container_width=True, hide_index=True)
    with tabs[6]:
        target = df[df["alerts_text"].astype(str).str.contains("prioridad manual", na=False)]
        st.caption("Casos donde tu prioridad manual y el modelo no coinciden. No es un error: es una invitación a revisar el motivo.")
        st.dataframe(target[[c for c in columns if c in target.columns]], use_container_width=True, hide_index=True)
    st.scatter_chart(df, x="confidence", y="decision_score", size="observation_count", color="priority_label", use_container_width=True)


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
    c1, c2 = st.columns(2)
    c1.download_button("Descargar backup ZIP", backup_zip_bytes(), file_name="scouting_hub_v08_backup.zip", mime="application/zip", use_container_width=True)
    c2.download_button("Descargar Excel completo", excel_backup_bytes(), file_name="scouting_hub_v08.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
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
    hero("Ajustes del scoring", "Personaliza cuánto pesan nivel, encaje de rol, potencial, necesidad y tendencia. La confianza no se mezcla: modula la fuerza de la decisión.", "Modelo", "Transparencia")
    settings = get_settings()
    current = dict(DEFAULT_SCORING_WEIGHTS)
    current.update(settings.get("scoring_weights", {}))
    with st.form("scoring_settings"):
        c1, c2, c3, c4, c5 = st.columns(5)
        level = c1.number_input("Nivel", 0.0, 1.0, float(current["level"]), .05)
        role_fit = c2.number_input("Encaje", 0.0, 1.0, float(current["role_fit"]), .05)
        potential = c3.number_input("Potencial", 0.0, 1.0, float(current["potential"]), .05)
        need = c4.number_input("Necesidad", 0.0, 1.0, float(current["need"]), .05)
        trend = c5.number_input("Tendencia", 0.0, 1.0, float(current["trend"]), .05)
        submitted = st.form_submit_button("Guardar pesos")
    total = level + role_fit + potential + need + trend
    st.caption(f"Suma actual: {total:.2f}. La app normaliza automáticamente aunque no sea 1.00.")
    if submitted:
        settings["scoring_weights"] = {"level": level, "role_fit": role_fit, "potential": potential, "need": need, "trend": trend}
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
        <div class="panel"><h3>Principios del motor</h3><div class="mini-grid">
          <div class="mini-card"><div class="title">No hay bonus automático por edad</div><div class="sub">La juventud no equivale a potencial: la proyección la valoras tú.</div></div>
          <div class="mini-card"><div class="title">La completitud no mejora al jugador</div><div class="sub">Solo aumenta la confianza de la decisión.</div></div>
          <div class="mini-card"><div class="title">La prioridad manual no altera el score</div><div class="sub">Se muestra como discrepancia para que puedas revisar tu criterio, no para confirmar lo que ya marcaste.</div></div>
          <div class="mini-card"><div class="title">Poca muestra → neutralidad</div><div class="sub">El score se contrae hacia 50, no hacia cero.</div></div>
          <div class="mini-card"><div class="title">Ranking por rol</div><div class="sub">Un lateral ofensivo y uno defensivo no se ordenan con los mismos criterios.</div></div>
          <div class="mini-card"><div class="title">0 = no evaluado</div><div class="sub">Una dimensión no observada no debe castigar al jugador.</div></div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )
