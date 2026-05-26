from __future__ import annotations

import io
import re
import zipfile
import unicodedata
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd
import streamlit as st

APP_TITLE = "Scouting Hub v0.3.3"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

POSITIONS = ["POR", "LD", "DFC", "LI", "CAD", "CAI", "MCD", "MC", "MP", "ED", "EI", "SD", "DC"]
FOOTS = ["", "Derecha", "Izquierda", "Ambas"]
PLAYER_STATUS = ["Sin valorar", "Seguir", "Revisar", "Prioritario", "Descartar", "Fichaje recomendado"]
TEAM_TYPES = ["Club", "Selección"]

SCHEMAS: Dict[str, List[str]] = {
    "countries": ["country_id", "name", "normalized_name", "created_at"],
    "competitions": ["competition_id", "name", "normalized_name", "country_id", "level", "season", "created_at"],
    "teams": ["team_id", "name", "normalized_name", "team_type", "country_id", "competition_id", "created_at"],
    "players": [
        "player_id", "display_name", "normalized_name", "birth_date", "age", "nationality_id",
        "primary_position", "secondary_position", "dominant_foot", "height_cm", "current_team_id",
        "status", "tags", "general_notes", "created_at"
    ],
    "matches": [
        "match_id", "match_date", "match_name", "competition_id", "home_team_id", "away_team_id",
        "season", "context", "created_at"
    ],
    "observations": [
        "observation_id", "player_id", "match_id", "team_id", "observed_position", "minutes_observed",
        "role", "action_type", "minute_note", "positive_notes", "improvement_notes", "technical_rating",
        "tactical_rating", "physical_rating", "mental_rating", "global_rating", "recommendation", "created_at"
    ],
    "aliases": ["alias_id", "player_id", "alias", "normalized_alias", "created_at"],
}

SEED_COUNTRIES = [
    "España", "Italia", "Francia", "Alemania", "Inglaterra", "Portugal", "Países Bajos",
    "Bélgica", "Argentina", "Brasil", "Uruguay", "Croacia", "Marruecos", "Estados Unidos"
]

SEED_COMPETITIONS = [
    ("España", "LaLiga", "1ª", "2025/26"),
    ("España", "LaLiga Hypermotion", "2ª", "2025/26"),
    ("España", "Primera Federación", "3ª", "2025/26"),
    ("España", "Segunda Federación", "4ª", "2025/26"),
    ("España", "Primera Regional Castilla y León", "Regional", "2025/26"),
    ("Italia", "Serie A", "1ª", "2025/26"),
    ("Italia", "Serie B", "2ª", "2025/26"),
    ("Inglaterra", "Premier League", "1ª", "2025/26"),
    ("Inglaterra", "Championship", "2ª", "2025/26"),
    ("Alemania", "Bundesliga", "1ª", "2025/26"),
    ("Francia", "Ligue 1", "1ª", "2025/26"),
    ("Portugal", "Primeira Liga", "1ª", "2025/26"),
]


def now_str() -> str:
    return pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9ñ\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def file_path(table: str) -> Path:
    return DATA_DIR / f"{table}.csv"


def empty_df(table: str) -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEMAS[table])


def load_table(table: str) -> pd.DataFrame:
    path = file_path(table)
    if not path.exists():
        df = empty_df(table)
        df.to_csv(path, index=False)
        return df
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
    except pd.errors.EmptyDataError:
        df = empty_df(table)
    for col in SCHEMAS[table]:
        if col not in df.columns:
            df[col] = ""
    return df[SCHEMAS[table]].fillna("")


def save_table(table: str, df: pd.DataFrame) -> None:
    for col in SCHEMAS[table]:
        if col not in df.columns:
            df[col] = ""
    df[SCHEMAS[table]].fillna("").to_csv(file_path(table), index=False)


def next_id(df: pd.DataFrame, prefix: str, id_col: str) -> str:
    if df.empty or id_col not in df.columns:
        return f"{prefix}0001"
    nums = []
    for val in df[id_col].astype(str):
        m = re.search(r"(\d+)$", val)
        if m:
            nums.append(int(m.group(1)))
    return f"{prefix}{(max(nums) + 1 if nums else 1):04d}"


def get_name(df: pd.DataFrame, id_col: str, id_value: str, name_col: str = "name") -> str:
    if not id_value or df.empty:
        return ""
    row = df[df[id_col].astype(str) == str(id_value)]
    if row.empty:
        return ""
    return str(row.iloc[0].get(name_col, ""))


def ensure_seed_data() -> None:
    countries = load_table("countries")
    if countries.empty:
        rows = []
        for idx, name in enumerate(SEED_COUNTRIES, 1):
            rows.append({"country_id": f"CTY{idx:04d}", "name": name, "normalized_name": normalize_text(name), "created_at": now_str()})
        save_table("countries", pd.DataFrame(rows, columns=SCHEMAS["countries"]))

    countries = load_table("countries")
    competitions = load_table("competitions")
    if competitions.empty:
        rows = []
        for idx, (country_name, comp_name, level, season) in enumerate(SEED_COMPETITIONS, 1):
            country_id_series = countries.loc[countries["normalized_name"] == normalize_text(country_name), "country_id"]
            country_id = country_id_series.iloc[0] if not country_id_series.empty else ""
            rows.append({
                "competition_id": f"CMP{idx:04d}",
                "name": comp_name,
                "normalized_name": normalize_text(comp_name),
                "country_id": country_id,
                "level": level,
                "season": season,
                "created_at": now_str(),
            })
        save_table("competitions", pd.DataFrame(rows, columns=SCHEMAS["competitions"]))


def add_country(name: str) -> Tuple[str, bool, str]:
    name = name.strip()
    if not name:
        return "", False, "Nombre vacío."
    df = load_table("countries")
    norm = normalize_text(name)
    existing = df[df["normalized_name"] == norm]
    if not existing.empty:
        return existing.iloc[0]["country_id"], False, f"Ya existía como: {existing.iloc[0]['name']}"
    new_id = next_id(df, "CTY", "country_id")
    df.loc[len(df)] = [new_id, name, norm, now_str()]
    save_table("countries", df)
    return new_id, True, "País añadido."


def add_competition(name: str, country_id: str, level: str = "", season: str = "") -> Tuple[str, bool, str]:
    name = name.strip()
    if not name or not country_id:
        return "", False, "Falta nombre o país."
    df = load_table("competitions")
    norm = normalize_text(name)
    existing = df[(df["normalized_name"] == norm) & (df["country_id"] == country_id)]
    if not existing.empty:
        return existing.iloc[0]["competition_id"], False, f"Ya existía como: {existing.iloc[0]['name']}"
    new_id = next_id(df, "CMP", "competition_id")
    df.loc[len(df)] = [new_id, name, norm, country_id, level, season, now_str()]
    save_table("competitions", df)
    return new_id, True, "Competición añadida."


def add_team(name: str, team_type: str, country_id: str, competition_id: str = "") -> Tuple[str, bool, str]:
    name = name.strip()
    if not name or not country_id:
        return "", False, "Falta nombre o país."
    df = load_table("teams")
    norm = normalize_text(name)
    existing = df[(df["normalized_name"] == norm) & (df["country_id"] == country_id) & (df["team_type"] == team_type)]
    if not existing.empty:
        return existing.iloc[0]["team_id"], False, f"Ya existía como: {existing.iloc[0]['name']}"
    new_id = next_id(df, "TEA", "team_id")
    df.loc[len(df)] = [new_id, name, norm, team_type, country_id, competition_id, now_str()]
    save_table("teams", df)
    return new_id, True, "Equipo/selección añadido."


def add_player(display_name: str, **kwargs) -> Tuple[str, bool, str]:
    display_name = display_name.strip()
    if not display_name:
        return "", False, "Nombre vacío."
    df = load_table("players")
    aliases = load_table("aliases")
    norm = normalize_text(display_name)
    candidates = df[df["normalized_name"] == norm]
    if candidates.empty and not aliases.empty:
        alias_match = aliases[aliases["normalized_alias"] == norm]
        if not alias_match.empty:
            candidates = df[df["player_id"] == alias_match.iloc[0]["player_id"]]
    if not candidates.empty:
        return candidates.iloc[0]["player_id"], False, f"Ya existía como: {candidates.iloc[0]['display_name']}"
    new_id = next_id(df, "PLY", "player_id")
    row = {
        "player_id": new_id,
        "display_name": display_name,
        "normalized_name": norm,
        "birth_date": kwargs.get("birth_date", ""),
        "age": kwargs.get("age", ""),
        "nationality_id": kwargs.get("nationality_id", ""),
        "primary_position": kwargs.get("primary_position", ""),
        "secondary_position": kwargs.get("secondary_position", ""),
        "dominant_foot": kwargs.get("dominant_foot", ""),
        "height_cm": kwargs.get("height_cm", ""),
        "current_team_id": kwargs.get("current_team_id", ""),
        "status": kwargs.get("status", "Sin valorar"),
        "tags": kwargs.get("tags", ""),
        "general_notes": kwargs.get("general_notes", ""),
        "created_at": now_str(),
    }
    df.loc[len(df)] = [row[col] for col in SCHEMAS["players"]]
    save_table("players", df)
    return new_id, True, "Jugador añadido."


def add_match(match_date: str, match_name: str, competition_id: str, home_team_id: str, away_team_id: str, season: str, context: str) -> Tuple[str, bool, str]:
    df = load_table("matches")
    norm_key = normalize_text(f"{match_date} {match_name}")
    if not match_name.strip():
        return "", False, "Falta nombre del partido."
    existing = df[df.apply(lambda r: normalize_text(f"{r.get('match_date','')} {r.get('match_name','')}") == norm_key, axis=1)] if not df.empty else pd.DataFrame()
    if not existing.empty:
        return existing.iloc[0]["match_id"], False, f"Ya existía el partido: {existing.iloc[0]['match_name']}"
    new_id = next_id(df, "MAT", "match_id")
    df.loc[len(df)] = [new_id, match_date, match_name, competition_id, home_team_id, away_team_id, season, context, now_str()]
    save_table("matches", df)
    return new_id, True, "Partido creado."


def add_observation(**kwargs) -> Tuple[str, bool, str]:
    df = load_table("observations")
    if not kwargs.get("player_id", ""):
        return "", False, "Falta jugador."
    new_id = next_id(df, "OBS", "observation_id")
    row = {col: kwargs.get(col, "") for col in SCHEMAS["observations"]}
    row["observation_id"] = new_id
    row["created_at"] = now_str()
    df.loc[len(df)] = [row[col] for col in SCHEMAS["observations"]]
    save_table("observations", df)
    return new_id, True, "Observación guardada."


def dataframe_download_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def make_excel_bytes() -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for table in SCHEMAS:
            load_table(table).to_excel(writer, index=False, sheet_name=table[:31])
    return output.getvalue()


def make_zip_bytes() -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for table in SCHEMAS:
            zf.writestr(f"{table}.csv", dataframe_download_csv(load_table(table)))
        zf.writestr("scouting_hub_backup.xlsx", make_excel_bytes())
    return output.getvalue()


def import_excel(uploaded) -> None:
    xls = pd.ExcelFile(uploaded)
    for table in SCHEMAS:
        if table in xls.sheet_names:
            df = pd.read_excel(xls, table, dtype=str).fillna("")
            save_table(table, df)


def import_zip(uploaded) -> None:
    data = uploaded.read()
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        for table in SCHEMAS:
            name = f"{table}.csv"
            if name in zf.namelist():
                with zf.open(name) as f:
                    df = pd.read_csv(f, dtype=str).fillna("")
                    save_table(table, df)


def country_select(label: str, key: str, allow_add: bool = True) -> str:
    countries = load_table("countries").sort_values("name")
    options = [""] + countries["country_id"].tolist()
    labels = {"": "— Seleccionar —"}
    labels.update(dict(zip(countries["country_id"], countries["name"])))
    selected = st.selectbox(label, options, format_func=lambda x: labels.get(x, x), key=key)
    if allow_add:
        with st.expander("+ Añadir país", expanded=False):
            new_country = st.text_input("Nombre del país", key=f"{key}_new_country")
            if st.button("Guardar país", key=f"{key}_save_country"):
                _, created, msg = add_country(new_country)
                st.success(msg) if created else st.info(msg)
                st.rerun()
    return selected


def competition_select(label: str, country_id: str, key: str, allow_add: bool = True) -> str:
    competitions = load_table("competitions")
    if country_id:
        competitions = competitions[competitions["country_id"] == country_id]
    competitions = competitions.sort_values(["level", "name"])
    options = [""] + competitions["competition_id"].tolist()
    labels = {"": "— Seleccionar —"}
    labels.update({r["competition_id"]: f"{r['name']} · {r.get('level','')} · {r.get('season','')}" for _, r in competitions.iterrows()})
    selected = st.selectbox(label, options, format_func=lambda x: labels.get(x, x), key=key)
    if allow_add and country_id:
        with st.expander("+ Añadir competición/liga", expanded=False):
            c1, c2, c3 = st.columns([2, 1, 1])
            new_name = c1.text_input("Nombre", key=f"{key}_new_comp")
            new_level = c2.text_input("Nivel", key=f"{key}_new_level", placeholder="1ª, 2ª, Sub-21...")
            new_season = c3.text_input("Temporada", key=f"{key}_new_season", placeholder="2025/26")
            if st.button("Guardar competición", key=f"{key}_save_comp"):
                _, created, msg = add_competition(new_name, country_id, new_level, new_season)
                st.success(msg) if created else st.info(msg)
                st.rerun()
    return selected


def team_select(label: str, team_type: str, country_id: str, competition_id: str, key: str, allow_add: bool = True) -> str:
    teams = load_table("teams")
    if team_type:
        teams = teams[teams["team_type"] == team_type]
    if country_id:
        teams = teams[teams["country_id"] == country_id]
    if team_type == "Club" and competition_id:
        teams = teams[teams["competition_id"] == competition_id]
    teams = teams.sort_values("name")
    options = [""] + teams["team_id"].tolist()
    labels = {"": "— Seleccionar —"}
    labels.update(dict(zip(teams["team_id"], teams["name"])))
    selected = st.selectbox(label, options, format_func=lambda x: labels.get(x, x), key=key)
    if allow_add and country_id:
        with st.expander("+ Añadir equipo/selección", expanded=False):
            new_team = st.text_input("Nombre", key=f"{key}_new_team")
            if st.button("Guardar equipo/selección", key=f"{key}_save_team"):
                _, created, msg = add_team(new_team, team_type, country_id, competition_id if team_type == "Club" else "")
                st.success(msg) if created else st.info(msg)
                st.rerun()
    return selected


def player_select(label: str, team_id: str, key: str) -> str:
    players = load_table("players")
    if team_id:
        players = players[players["current_team_id"] == team_id]
    players = players.sort_values("display_name")
    options = [""] + players["player_id"].tolist()
    labels = {"": "— Seleccionar jugador —"}
    labels.update({r["player_id"]: f"{r['display_name']} · {r.get('primary_position','')} · {r.get('status','')}" for _, r in players.iterrows()})
    return st.selectbox(label, options, format_func=lambda x: labels.get(x, x), key=key)


def show_duplicate_warning(name: str) -> Optional[str]:
    players = load_table("players")
    aliases = load_table("aliases")
    norm = normalize_text(name)
    if not norm:
        return None
    exact = players[players["normalized_name"] == norm]
    if not exact.empty:
        player = exact.iloc[0]
        st.warning(f"Posible duplicado exacto: ya existe **{player['display_name']}**.")
        return player["player_id"]
    if len(norm) >= 4 and not players.empty:
        partial = players[players["normalized_name"].str.contains(re.escape(norm), na=False) | players["display_name"].str.lower().str.contains(str(name).lower(), na=False)]
        if not partial.empty:
            st.info("Jugadores parecidos encontrados: " + ", ".join(partial["display_name"].head(5).tolist()))
    if not aliases.empty:
        alias_match = aliases[aliases["normalized_alias"] == norm]
        if not alias_match.empty:
            pid = alias_match.iloc[0]["player_id"]
            pname = get_name(players, "player_id", pid, "display_name")
            st.warning(f"Ese nombre coincide con un alias de **{pname}**.")
            return pid
    return None


def enrich_tables() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    countries = load_table("countries")
    competitions = load_table("competitions")
    teams = load_table("teams")
    players = load_table("players")
    matches = load_table("matches")
    observations = load_table("observations")

    c_map = dict(zip(countries["country_id"], countries["name"]))
    comp_map = dict(zip(competitions["competition_id"], competitions["name"]))
    team_map = dict(zip(teams["team_id"], teams["name"]))
    player_map = dict(zip(players["player_id"], players["display_name"]))
    match_map = dict(zip(matches["match_id"], matches["match_name"]))

    teams_view = teams.copy()
    teams_view["country"] = teams_view["country_id"].map(c_map).fillna("")
    teams_view["competition"] = teams_view["competition_id"].map(comp_map).fillna("")

    players_view = players.copy()
    players_view["nationality"] = players_view["nationality_id"].map(c_map).fillna("")
    players_view["current_team"] = players_view["current_team_id"].map(team_map).fillna("")

    matches_view = matches.copy()
    matches_view["competition"] = matches_view["competition_id"].map(comp_map).fillna("")
    matches_view["home_team"] = matches_view["home_team_id"].map(team_map).fillna("")
    matches_view["away_team"] = matches_view["away_team_id"].map(team_map).fillna("")

    observations_view = observations.copy()
    observations_view["player"] = observations_view["player_id"].map(player_map).fillna("")
    observations_view["team"] = observations_view["team_id"].map(team_map).fillna("")
    observations_view["match"] = observations_view["match_id"].map(match_map).fillna("")
    return teams_view, players_view, matches_view, observations_view, competitions


def draw_pitch(players_df: pd.DataFrame) -> None:
    """Campograma sin matplotlib: HTML/CSS puro para evitar dependencias."""
    pos_xy = {
        "POR": (7, 50), "LD": (24, 78), "DFC": (24, 50), "LI": (24, 22),
        "CAD": (46, 84), "CAI": (46, 16), "MCD": (43, 50), "MC": (56, 50),
        "MP": (70, 50), "ED": (78, 78), "EI": (78, 22), "SD": (84, 58), "DC": (91, 50),
    }
    counts = players_df["primary_position"].value_counts().to_dict() if not players_df.empty else {}
    markers = []
    for pos, (x, y) in pos_xy.items():
        count = int(counts.get(pos, 0))
        opacity = "1" if count else "0.35"
        size = min(70, 38 + count * 6) if count else 34
        label = f"{pos}<br><b>{count}</b>" if count else pos
        markers.append(
            f'<div class="marker" style="left:{x}%; top:{y}%; width:{size}px; height:{size}px; opacity:{opacity};">{label}</div>'
        )
    html = f"""
    <style>
      .pitch {{
        position: relative;
        width: 100%;
        max-width: 980px;
        height: 560px;
        margin: 0 auto 1rem auto;
        border: 3px solid #14532d;
        border-radius: 18px;
        background: linear-gradient(90deg, #dff3df 0 10%, #cfeccf 10% 20%, #dff3df 20% 30%, #cfeccf 30% 40%, #dff3df 40% 50%, #cfeccf 50% 60%, #dff3df 60% 70%, #cfeccf 70% 80%, #dff3df 80% 90%, #cfeccf 90% 100%);
        overflow: hidden;
      }}
      .half {{ position:absolute; top:0; bottom:0; left:50%; width:2px; background:#14532d; opacity:.7; }}
      .circle {{ position:absolute; left:50%; top:50%; width:110px; height:110px; margin-left:-55px; margin-top:-55px; border:2px solid #14532d; border-radius:50%; opacity:.7; }}
      .box-left {{ position:absolute; left:0; top:24%; width:17%; height:52%; border:2px solid #14532d; border-left:0; opacity:.7; }}
      .box-right {{ position:absolute; right:0; top:24%; width:17%; height:52%; border:2px solid #14532d; border-right:0; opacity:.7; }}
      .marker {{
        position:absolute;
        transform:translate(-50%,-50%);
        border-radius:999px;
        background:#ffffff;
        border:2px solid #1f6feb;
        color:#111827;
        font-size:12px;
        line-height:1.05;
        text-align:center;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        box-shadow:0 6px 16px rgba(0,0,0,.12);
        font-family:system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      }}
    </style>
    <div class="pitch">
      <div class="half"></div><div class="circle"></div><div class="box-left"></div><div class="box-right"></div>
      {''.join(markers)}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    if not players_df.empty:
        summary = players_df["primary_position"].value_counts().reset_index()
        summary.columns = ["Posición", "Jugadores"]
        st.dataframe(summary, use_container_width=True, hide_index=True)


def page_dashboard() -> None:
    st.title(APP_TITLE)
    st.caption("Base propia de scouting con flujo jerárquico y control de duplicados. Sin matplotlib.")
    _, players_view, matches_view, observations_view, _ = enrich_tables()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jugadores", len(players_view))
    c2.metric("Partidos", len(matches_view))
    c3.metric("Observaciones", len(observations_view))
    c4.metric("Prioritarios", int((players_view["status"] == "Prioritario").sum()) if not players_view.empty else 0)
    st.info("Flujo recomendado: país/liga/equipo → plantilla → jugador existente o nuevo → observación → exportar backup.")
    if not observations_view.empty:
        st.subheader("Últimas observaciones")
        st.dataframe(observations_view[["created_at", "player", "match", "observed_position", "global_rating", "recommendation"]].tail(10), use_container_width=True, hide_index=True)


def page_guided_flow() -> None:
    st.title("Añadir / puntuar jugador")
    st.caption("Entrada principal: evita duplicados y trabaja desde país → competición → equipo → jugador.")

    scope = st.radio("¿Desde dónde partes?", ["Club", "Selección"], horizontal=True)
    country_id = country_select("País", "flow_country")
    competition_id = ""
    if scope == "Club" and country_id:
        competition_id = competition_select("Liga / competición", country_id, "flow_competition")
    team_id = ""
    if country_id:
        team_id = team_select("Equipo / selección", scope, country_id, competition_id, "flow_team")
    if not team_id:
        st.stop()

    st.divider()
    st.subheader("Plantilla del equipo seleccionado")
    players = load_table("players")
    roster = players[players["current_team_id"] == team_id].sort_values("display_name")
    if roster.empty:
        st.warning("Este equipo todavía no tiene jugadores cargados.")
    else:
        st.dataframe(roster[["display_name", "primary_position", "secondary_position", "age", "status", "tags"]], use_container_width=True, hide_index=True)

    with st.expander("+ Cargar varios jugadores de golpe", expanded=False):
        bulk_text = st.text_area("Plantilla", placeholder="Jugador Uno\nJugador Dos\nJugador Tres", height=160)
        default_pos = st.selectbox("Posición por defecto", [""] + POSITIONS, key="bulk_pos")
        if st.button("Añadir plantilla", key="bulk_add"):
            created, skipped = 0, 0
            for line in bulk_text.splitlines():
                name = line.strip()
                if not name:
                    continue
                _, was_created, _ = add_player(name, nationality_id=country_id, primary_position=default_pos, current_team_id=team_id, status="Sin valorar")
                created += int(was_created)
                skipped += int(not was_created)
            st.success(f"Añadidos: {created}. Ya existentes/no duplicados: {skipped}.")
            st.rerun()

    st.divider()
    mode = st.radio("¿Qué quieres hacer?", ["Puntuar jugador existente", "Añadir jugador nuevo"], horizontal=True)
    selected_player_id = ""
    if mode == "Puntuar jugador existente":
        selected_player_id = player_select("Jugador", team_id, "flow_existing_player")
    else:
        name = st.text_input("Nombre del jugador")
        duplicate_id = show_duplicate_warning(name)
        col1, col2, col3 = st.columns(3)
        primary = col1.selectbox("Posición principal", [""] + POSITIONS)
        secondary = col2.selectbox("Posición secundaria", [""] + POSITIONS)
        foot = col3.selectbox("Pierna dominante", FOOTS)
        col4, col5, col6 = st.columns(3)
        age = col4.text_input("Edad")
        height = col5.text_input("Altura cm")
        status = col6.selectbox("Estado", PLAYER_STATUS)
        tags = st.text_input("Etiquetas", placeholder="Sub-21, físico top, zurdo, revisar...")
        notes = st.text_area("Notas generales")
        if st.button("Guardar jugador"):
            if duplicate_id:
                st.warning("No lo he creado porque parece duplicado. Selecciona el existente o fusiona desde Duplicados.")
            else:
                pid, created, msg = add_player(name, nationality_id=country_id, primary_position=primary, secondary_position=secondary, dominant_foot=foot, age=age, height_cm=height, current_team_id=team_id, status=status, tags=tags, general_notes=notes)
                st.success(msg) if created else st.info(msg)
                st.session_state["last_player_id"] = pid
                st.rerun()
        selected_player_id = st.session_state.get("last_player_id", "")

    if selected_player_id:
        st.divider()
        st.subheader("Añadir observación")
        matches = load_table("matches")
        teams = load_table("teams")
        match_options = [""] + matches["match_id"].tolist()
        match_labels = {"": "— Sin partido / crear luego —"}
        match_labels.update(dict(zip(matches["match_id"], matches["match_name"])))
        selected_match = st.selectbox("Partido", match_options, format_func=lambda x: match_labels.get(x, x))

        with st.expander("+ Crear partido rápido", expanded=False):
            comp_for_match = competition_id or competition_select("Competición del partido", country_id, "quick_match_comp")
            match_date = st.date_input("Fecha", value=date.today(), key="quick_match_date")
            home = team_select("Local", scope, country_id, comp_for_match, "quick_home")
            away = team_select("Visitante", scope, country_id, comp_for_match, "quick_away")
            home_name = get_name(teams, "team_id", home, "name")
            away_name = get_name(teams, "team_id", away, "name")
            match_name = st.text_input("Nombre del partido", value=f"{home_name} - {away_name}" if home_name and away_name else "")
            if st.button("Guardar partido rápido"):
                _, created, msg = add_match(str(match_date), match_name, comp_for_match, home, away, "", "")
                st.success(msg) if created else st.info(msg)
                st.rerun()

        with st.form("observation_form"):
            c1, c2, c3 = st.columns(3)
            observed_pos = c1.selectbox("Posición observada", [""] + POSITIONS)
            minutes = c2.text_input("Minutos vistos", placeholder="90, 45, 20...")
            action_type = c3.selectbox("Tipo", ["Informe global", "Acción puntual", "ABP", "Transición", "Duelos", "Con balón", "Sin balón"])
            role = st.text_input("Rol observado", placeholder="Extremo abierto, central corrector, pivote posicional...")
            minute_note = st.text_input("Minuto / contexto", placeholder="Min 23, primera parte, tras pérdida...")
            pos_notes = st.text_area("Notas positivas")
            imp_notes = st.text_area("Notas de mejora / dudas")
            r1, r2, r3, r4, r5 = st.columns(5)
            technical = r1.slider("Técnica", 0, 10, 0)
            tactical = r2.slider("Táctica", 0, 10, 0)
            physical = r3.slider("Físico", 0, 10, 0)
            mental = r4.slider("Mental", 0, 10, 0)
            global_rating = r5.slider("Global", 0, 10, 0)
            recommendation = st.selectbox("Recomendación", PLAYER_STATUS)
            submit_obs = st.form_submit_button("Guardar observación")
            if submit_obs:
                _, created, msg = add_observation(player_id=selected_player_id, match_id=selected_match, team_id=team_id, observed_position=observed_pos, minutes_observed=minutes, role=role, action_type=action_type, minute_note=minute_note, positive_notes=pos_notes, improvement_notes=imp_notes, technical_rating=str(technical), tactical_rating=str(tactical), physical_rating=str(physical), mental_rating=str(mental), global_rating=str(global_rating), recommendation=recommendation)
                st.success(msg) if created else st.error(msg)


def page_structure() -> None:
    st.title("Estructura: países, ligas y equipos")
    tab1, tab2, tab3 = st.tabs(["Países", "Competiciones", "Equipos / selecciones"])
    with tab1:
        df = load_table("countries")
        edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="edit_countries")
        if st.button("Guardar países"):
            edited["normalized_name"] = edited["name"].apply(normalize_text)
            save_table("countries", edited)
            st.success("Países guardados.")
    with tab2:
        df = load_table("competitions")
        edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="edit_comps")
        if st.button("Guardar competiciones"):
            edited["normalized_name"] = edited["name"].apply(normalize_text)
            save_table("competitions", edited)
            st.success("Competiciones guardadas.")
    with tab3:
        teams_view, _, _, _, _ = enrich_tables()
        st.dataframe(teams_view[["team_id", "name", "team_type", "country", "competition"]], use_container_width=True, hide_index=True)
        df = load_table("teams")
        edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="edit_teams")
        if st.button("Guardar equipos"):
            edited["normalized_name"] = edited["name"].apply(normalize_text)
            save_table("teams", edited)
            st.success("Equipos guardados.")


def page_matches() -> None:
    st.title("Partidos")
    country_id = country_select("País principal", "match_country")
    competition_id = competition_select("Competición", country_id, "match_comp") if country_id else ""
    scope = st.radio("Tipo de equipos", TEAM_TYPES, horizontal=True, key="match_scope")
    home_id = team_select("Local", scope, country_id, competition_id, "match_home") if country_id else ""
    away_id = team_select("Visitante", scope, country_id, competition_id, "match_away") if country_id else ""
    teams = load_table("teams")
    home_name = get_name(teams, "team_id", home_id, "name")
    away_name = get_name(teams, "team_id", away_id, "name")
    with st.form("match_form"):
        mdate = st.date_input("Fecha", value=date.today())
        mname = st.text_input("Nombre", value=f"{home_name} - {away_name}" if home_name and away_name else "")
        season = st.text_input("Temporada", placeholder="2025/26")
        context = st.text_area("Contexto", placeholder="Eurocopa, Mundial, amistoso, playoff, jornada...")
        submit = st.form_submit_button("Crear partido")
        if submit:
            _, created, msg = add_match(str(mdate), mname, competition_id, home_id, away_id, season, context)
            st.success(msg) if created else st.info(msg)
    _, _, matches_view, _, _ = enrich_tables()
    st.subheader("Partidos registrados")
    st.dataframe(matches_view[["match_id", "match_date", "match_name", "competition", "home_team", "away_team", "season", "context"]], use_container_width=True, hide_index=True)


def page_players() -> None:
    st.title("Jugadores")
    _, players_view, _, observations_view, _ = enrich_tables()
    if players_view.empty:
        st.warning("Todavía no hay jugadores.")
        return
    c1, c2, c3 = st.columns(3)
    pos_filter = c1.multiselect("Posición", POSITIONS)
    status_filter = c2.multiselect("Estado", PLAYER_STATUS)
    search = c3.text_input("Buscar")
    df = players_view.copy()
    if pos_filter:
        df = df[df["primary_position"].isin(pos_filter)]
    if status_filter:
        df = df[df["status"].isin(status_filter)]
    if search:
        df = df[df["display_name"].str.contains(search, case=False, na=False)]
    st.dataframe(df[["player_id", "display_name", "current_team", "nationality", "primary_position", "age", "status", "tags"]], use_container_width=True, hide_index=True)

    st.subheader("Ficha individual")
    options = [""] + players_view["player_id"].tolist()
    labels = {"": "— Seleccionar —"}
    labels.update(dict(zip(players_view["player_id"], players_view["display_name"])))
    pid = st.selectbox("Jugador", options, format_func=lambda x: labels.get(x, x))
    if pid:
        player = players_view[players_view["player_id"] == pid].iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Posición", player.get("primary_position", ""))
        col2.metric("Equipo", player.get("current_team", ""))
        col3.metric("Estado", player.get("status", ""))
        obs = observations_view[observations_view["player_id"] == pid]
        ratings = pd.to_numeric(obs["global_rating"], errors="coerce") if not obs.empty else pd.Series(dtype=float)
        col4.metric("Nota media", f"{ratings.mean():.1f}" if not ratings.dropna().empty else "—")
        st.write("**Notas generales:**", player.get("general_notes", ""))
        if not obs.empty:
            st.subheader("Observaciones acumuladas")
            st.dataframe(obs[["created_at", "match", "observed_position", "role", "action_type", "global_rating", "recommendation", "positive_notes", "improvement_notes"]], use_container_width=True, hide_index=True)
            report = f"# Informe rápido - {player['display_name']}\n\n"
            report += f"Equipo: {player.get('current_team','')}\nPosición: {player.get('primary_position','')}\nEstado: {player.get('status','')}\n\n"
            for _, r in obs.iterrows():
                report += f"## {r.get('match','Sin partido')} · {r.get('created_at','')}\n"
                report += f"Posición: {r.get('observed_position','')} · Rol: {r.get('role','')} · Nota: {r.get('global_rating','')}\n"
                report += f"Positivo: {r.get('positive_notes','')}\n"
                report += f"Mejora/dudas: {r.get('improvement_notes','')}\n\n"
            st.download_button("Descargar informe TXT", report.encode("utf-8"), file_name=f"informe_{normalize_text(player['display_name']).replace(' ','_')}.txt")


def page_duplicate_center() -> None:
    st.title("Control de duplicados")
    players = load_table("players")
    if players.empty:
        st.warning("No hay jugadores.")
        return
    dupes = players[players.duplicated("normalized_name", keep=False)].sort_values("normalized_name")
    if dupes.empty:
        st.success("No hay duplicados exactos por nombre normalizado.")
    else:
        st.warning("Duplicados exactos detectados:")
        st.dataframe(dupes[["player_id", "display_name", "normalized_name", "current_team_id", "primary_position"]], use_container_width=True, hide_index=True)

    st.subheader("Fusionar dos jugadores")
    options = [""] + players["player_id"].tolist()
    labels = {"": "— Seleccionar —"}
    labels.update(dict(zip(players["player_id"], players["display_name"])))
    keep_id = st.selectbox("Jugador correcto que se queda", options, format_func=lambda x: labels.get(x, x), key="keep_player")
    merge_id = st.selectbox("Jugador duplicado que se fusiona/elimina", options, format_func=lambda x: labels.get(x, x), key="merge_player")
    if keep_id and merge_id and keep_id != merge_id:
        if st.button("Fusionar jugadores"):
            observations = load_table("observations")
            aliases = load_table("aliases")
            merge_name = get_name(players, "player_id", merge_id, "display_name")
            observations.loc[observations["player_id"] == merge_id, "player_id"] = keep_id
            save_table("observations", observations)
            alias_id = next_id(aliases, "ALS", "alias_id")
            aliases.loc[len(aliases)] = [alias_id, keep_id, merge_name, normalize_text(merge_name), now_str()]
            save_table("aliases", aliases)
            players = players[players["player_id"] != merge_id]
            save_table("players", players)
            st.success("Fusión completada.")
            st.rerun()

    st.subheader("Añadir alias a un jugador")
    alias_player = st.selectbox("Jugador", options, format_func=lambda x: labels.get(x, x), key="alias_player")
    alias_text = st.text_input("Alias / variante de escritura", placeholder="Fabián / Fabian Ruiz / Fabián Ruiz Peña")
    if st.button("Guardar alias") and alias_player and alias_text:
        aliases = load_table("aliases")
        alias_id = next_id(aliases, "ALS", "alias_id")
        aliases.loc[len(aliases)] = [alias_id, alias_player, alias_text, normalize_text(alias_text), now_str()]
        save_table("aliases", aliases)
        st.success("Alias guardado.")


def page_pitch_and_compare() -> None:
    st.title("Campograma y comparador")
    _, players_view, _, observations_view, _ = enrich_tables()
    if players_view.empty:
        st.warning("No hay jugadores.")
        return
    st.subheader("Campograma por posición principal")
    draw_pitch(players_view)

    st.subheader("Comparador")
    options = players_view["player_id"].tolist()
    labels = dict(zip(players_view["player_id"], players_view["display_name"]))
    c1, c2 = st.columns(2)
    p1 = c1.selectbox("Jugador A", options, format_func=lambda x: labels.get(x, x), key="comp_a")
    p2 = c2.selectbox("Jugador B", options, format_func=lambda x: labels.get(x, x), key="comp_b")
    rows = []
    for pid in [p1, p2]:
        obs = observations_view[observations_view["player_id"] == pid]
        player = players_view[players_view["player_id"] == pid].iloc[0]
        rows.append({
            "Jugador": player["display_name"],
            "Equipo": player.get("current_team", ""),
            "Posición": player.get("primary_position", ""),
            "Observaciones": len(obs),
            "Técnica": pd.to_numeric(obs["technical_rating"], errors="coerce").mean() if not obs.empty else None,
            "Táctica": pd.to_numeric(obs["tactical_rating"], errors="coerce").mean() if not obs.empty else None,
            "Físico": pd.to_numeric(obs["physical_rating"], errors="coerce").mean() if not obs.empty else None,
            "Mental": pd.to_numeric(obs["mental_rating"], errors="coerce").mean() if not obs.empty else None,
            "Global": pd.to_numeric(obs["global_rating"], errors="coerce").mean() if not obs.empty else None,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def page_data_editor() -> None:
    st.title("Base de datos editable")
    table = st.selectbox("Tabla", list(SCHEMAS.keys()))
    df = load_table(table)
    edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key=f"editor_{table}")
    if st.button("Guardar cambios"):
        if "name" in edited.columns:
            edited["normalized_name"] = edited["name"].apply(normalize_text)
        if "display_name" in edited.columns:
            edited["normalized_name"] = edited["display_name"].apply(normalize_text)
        if "alias" in edited.columns:
            edited["normalized_alias"] = edited["alias"].apply(normalize_text)
        save_table(table, edited)
        st.success("Cambios guardados.")


def page_backup() -> None:
    st.title("Backup / Importar / Exportar")
    st.warning("En Streamlit Cloud, exporta siempre al terminar. Luego podrás importar el ZIP o Excel para continuar.")
    c1, c2 = st.columns(2)
    c1.download_button("Descargar Excel completo", make_excel_bytes(), file_name="scouting_hub_backup.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    c2.download_button("Descargar ZIP completo", make_zip_bytes(), file_name="scouting_hub_backup.zip", mime="application/zip")

    st.subheader("CSV individuales")
    for table in SCHEMAS:
        st.download_button(f"Descargar {table}.csv", dataframe_download_csv(load_table(table)), file_name=f"{table}.csv", key=f"down_{table}")

    st.divider()
    st.subheader("Importar backup")
    uploaded = st.file_uploader("Sube un ZIP o Excel exportado por la app", type=["zip", "xlsx"])
    if uploaded is not None:
        if st.button("Importar archivo"):
            if uploaded.name.endswith(".zip"):
                import_zip(uploaded)
            else:
                import_excel(uploaded)
            st.success("Importación completada.")
            st.rerun()

    st.divider()
    st.subheader("Zona peligrosa")
    confirm = st.text_input("Escribe BORRAR para reiniciar todos los datos")
    if st.button("Reiniciar base de datos") and confirm == "BORRAR":
        for table in SCHEMAS:
            save_table(table, empty_df(table))
        ensure_seed_data()
        st.success("Datos reiniciados con países/ligas base.")
        st.rerun()


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide", page_icon="⚽")
    ensure_seed_data()
    st.sidebar.title("⚽ Scouting Hub")
    page = st.sidebar.radio(
        "Navegación",
        [
            "Inicio",
            "Añadir / puntuar jugador",
            "Estructura",
            "Partidos",
            "Jugadores",
            "Duplicados",
            "Campograma / comparador",
            "Base editable",
            "Backup / Importar / Exportar",
        ],
    )
    if page == "Inicio":
        page_dashboard()
    elif page == "Añadir / puntuar jugador":
        page_guided_flow()
    elif page == "Estructura":
        page_structure()
    elif page == "Partidos":
        page_matches()
    elif page == "Jugadores":
        page_players()
    elif page == "Duplicados":
        page_duplicate_center()
    elif page == "Campograma / comparador":
        page_pitch_and_compare()
    elif page == "Base editable":
        page_data_editor()
    elif page == "Backup / Importar / Exportar":
        page_backup()


if __name__ == "__main__":
    main()
