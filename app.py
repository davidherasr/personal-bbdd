from __future__ import annotations

import html
import io
import re
import zipfile
import unicodedata
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

APP_TITLE = "Scouting Hub v0.5"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

POSITIONS = ["POR", "LD", "DFC", "LI", "CAD", "CAI", "MCD", "MC", "MP", "ED", "EI", "SD", "DC"]
FOOTS = ["", "Derecha", "Izquierda", "Ambas"]
PLAYER_STATUS = ["Sin valorar", "Seguir", "Revisar", "Prioritario", "Descartar", "Fichaje recomendado"]
TEAM_TYPES = ["Club", "Selección"]
SOURCE_TYPES = ["", "Partido completo", "Directo", "Torneo", "Recomendación", "Base de datos", "Vídeo", "Entrenador", "Otro"]
PRIORITY_LABELS = ["A", "B", "C", "D"]

SCHEMAS: Dict[str, List[str]] = {
    "countries": ["country_id", "name", "normalized_name", "created_at"],
    "competitions": ["competition_id", "name", "normalized_name", "country_id", "level", "season", "created_at"],
    "teams": [
        "team_id", "name", "normalized_name", "team_type", "country_id", "competition_id",
        "locality", "locality_band", "created_at"
    ],
    "players": [
        "player_id", "display_name", "normalized_name", "birth_date", "age", "nationality_id",
        "primary_position", "secondary_position", "dominant_foot", "height_cm", "current_team_id",
        "status", "priority_manual", "potential", "source", "phone", "email", "test_sheet",
        "entry_date", "entry_age", "tags", "general_notes", "created_at"
    ],
    "matches": [
        "match_id", "match_date", "match_name", "competition_id", "home_team_id", "away_team_id",
        "season", "context", "created_at"
    ],
    "observations": [
        "observation_id", "player_id", "match_id", "team_id", "observed_position", "minutes_observed",
        "role", "action_type", "minute_note", "positive_notes", "improvement_notes", "technical_rating",
        "tactical_rating", "physical_rating", "mental_rating", "global_rating", "recommendation", "next_step", "created_at"
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
    ("España", "Tercera Federación", "5ª", "2025/26"),
    ("España", "Primera Regional Castilla y León", "Regional", "2025/26"),
    ("España", "Selecciones nacionales", "Selección", "2025/26"),
    ("Italia", "Serie A", "1ª", "2025/26"),
    ("Italia", "Serie B", "2ª", "2025/26"),
    ("Inglaterra", "Premier League", "1ª", "2025/26"),
    ("Inglaterra", "Championship", "2ª", "2025/26"),
    ("Alemania", "Bundesliga", "1ª", "2025/26"),
    ("Francia", "Ligue 1", "1ª", "2025/26"),
    ("Portugal", "Primeira Liga", "1ª", "2025/26"),
]

LOCALITY_BANDS = [
    "", "Sin datos", "Pueblo / rural", "Ciudad pequeña", "Ciudad media", "Gran ciudad", "Cantera profesional", "Academia", "Selección"
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


def safe(value: object) -> str:
    return html.escape(str(value or ""))


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
    df = pd.read_csv(path, dtype=str).fillna("")
    for col in SCHEMAS[table]:
        if col not in df.columns:
            df[col] = ""
    return df[SCHEMAS[table]].fillna("")


def save_table(table: str, df: pd.DataFrame) -> None:
    for col in SCHEMAS[table]:
        if col not in df.columns:
            df[col] = ""
    df = df[SCHEMAS[table]].fillna("")
    df.to_csv(file_path(table), index=False)


def next_id(df: pd.DataFrame, prefix: str, id_col: str) -> str:
    nums: List[int] = []
    if not df.empty and id_col in df.columns:
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
        rows = [
            {"country_id": f"CTY{idx:04d}", "name": name, "normalized_name": normalize_text(name), "created_at": now_str()}
            for idx, name in enumerate(SEED_COUNTRIES, 1)
        ]
        save_table("countries", pd.DataFrame(rows, columns=SCHEMAS["countries"]))

    countries = load_table("countries")
    competitions = load_table("competitions")
    if competitions.empty:
        rows = []
        for idx, (country_name, comp_name, level, season) in enumerate(SEED_COMPETITIONS, 1):
            country_id = countries.loc[countries["normalized_name"] == normalize_text(country_name), "country_id"]
            rows.append({
                "competition_id": f"CMP{idx:04d}",
                "name": comp_name,
                "normalized_name": normalize_text(comp_name),
                "country_id": country_id.iloc[0] if not country_id.empty else "",
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
        return existing.iloc[0]["country_id"], False, f"Ya existía como {existing.iloc[0]['name']}."
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
        return existing.iloc[0]["competition_id"], False, f"Ya existía como {existing.iloc[0]['name']}."
    new_id = next_id(df, "CMP", "competition_id")
    df.loc[len(df)] = [new_id, name, norm, country_id, level, season, now_str()]
    save_table("competitions", df)
    return new_id, True, "Competición añadida."


def add_team(name: str, team_type: str, country_id: str, competition_id: str = "", locality: str = "", locality_band: str = "") -> Tuple[str, bool, str]:
    name = name.strip()
    if not name or not country_id:
        return "", False, "Falta nombre o país."
    df = load_table("teams")
    norm = normalize_text(name)
    existing = df[(df["normalized_name"] == norm) & (df["country_id"] == country_id) & (df["team_type"] == team_type)]
    if not existing.empty:
        return existing.iloc[0]["team_id"], False, f"Ya existía como {existing.iloc[0]['name']}."
    new_id = next_id(df, "TEA", "team_id")
    df.loc[len(df)] = [new_id, name, norm, team_type, country_id, competition_id, locality, locality_band, now_str()]
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
        return candidates.iloc[0]["player_id"], False, f"Ya existía como {candidates.iloc[0]['display_name']}."
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
        "priority_manual": kwargs.get("priority_manual", ""),
        "potential": kwargs.get("potential", ""),
        "source": kwargs.get("source", ""),
        "phone": kwargs.get("phone", ""),
        "email": kwargs.get("email", ""),
        "test_sheet": kwargs.get("test_sheet", ""),
        "entry_date": kwargs.get("entry_date", ""),
        "entry_age": kwargs.get("entry_age", ""),
        "tags": kwargs.get("tags", ""),
        "general_notes": kwargs.get("general_notes", ""),
        "created_at": now_str(),
    }
    df.loc[len(df)] = [row[col] for col in SCHEMAS["players"]]
    save_table("players", df)
    return new_id, True, "Jugador añadido."


def add_match(match_date: str, match_name: str, competition_id: str, home_team_id: str, away_team_id: str, season: str, context: str) -> Tuple[str, bool, str]:
    match_name = match_name.strip()
    if not match_name:
        return "", False, "Falta nombre del partido."
    df = load_table("matches")
    norm_key = normalize_text(f"{match_date} {match_name}")
    existing = df[df.apply(lambda r: normalize_text(f"{r.get('match_date','')} {r.get('match_name','')}") == norm_key, axis=1)]
    if not existing.empty:
        return existing.iloc[0]["match_id"], False, f"Ya existía el partido: {existing.iloc[0]['match_name']}"
    new_id = next_id(df, "MAT", "match_id")
    df.loc[len(df)] = [new_id, match_date, match_name, competition_id, home_team_id, away_team_id, season, context, now_str()]
    save_table("matches", df)
    return new_id, True, "Partido creado."


def add_observation(**kwargs) -> Tuple[str, bool, str]:
    if not kwargs.get("player_id", ""):
        return "", False, "Falta jugador."
    df = load_table("observations")
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


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def completeness_for_player(row: pd.Series, obs_count: int = 0) -> int:
    fields = [
        "display_name", "age", "nationality_id", "primary_position", "dominant_foot", "height_cm",
        "current_team_id", "status", "potential", "source", "tags", "general_notes"
    ]
    filled = sum(1 for field in fields if str(row.get(field, "")).strip())
    score = filled / len(fields) * 85
    if obs_count > 0:
        score += 15
    return int(round(min(100, score)))


def priority_score(player: pd.Series, obs: pd.DataFrame) -> Tuple[int, str, List[str], str]:
    score = 0
    signals: List[str] = []
    status = str(player.get("status", ""))
    potential = str(player.get("potential", ""))
    tags = normalize_text(player.get("tags", ""))

    status_points = {
        "Fichaje recomendado": 30,
        "Prioritario": 26,
        "Seguir": 18,
        "Revisar": 12,
        "Sin valorar": 4,
        "Descartar": -25,
    }
    score += status_points.get(status, 0)
    if status:
        signals.append(f"status: {status.lower()}")

    if potential in ["Alto", "Muy alto"]:
        score += 18 if potential == "Alto" else 24
        signals.append(f"potencial {potential.lower()}")
    elif potential == "Medio-alto":
        score += 12
        signals.append("potencial medio-alto")

    if not obs.empty:
        g = to_num(obs["global_rating"]).dropna()
        if not g.empty:
            avg = float(g.mean())
            score += int(avg * 4)
            signals.append(f"nota media {avg:.1f}")
        if len(obs) >= 2:
            score += 8
            signals.append("segunda observación")
        else:
            signals.append("falta segunda observación")
    else:
        signals.append("sin observaciones")

    if str(player.get("age", "")).strip():
        age = pd.to_numeric(pd.Series([player.get("age")]), errors="coerce").iloc[0]
        if pd.notna(age) and 15 <= age <= 23:
            score += 8
            signals.append("edad interesante")

    if "prioritario" in tags or "top" in tags or "diferencial" in tags:
        score += 8
        signals.append("etiqueta fuerte")
    if "descartar" in tags:
        score -= 15
        signals.append("etiqueta negativa")

    comp = completeness_for_player(player, len(obs))
    if comp >= 70:
        score += 8
        signals.append("ficha completa")
    elif comp < 35:
        signals.append("ficha incompleta")

    score = max(0, min(100, score))
    manual = str(player.get("priority_manual", "")).strip()
    if manual in PRIORITY_LABELS:
        label = manual
    elif score >= 80:
        label = "A"
    elif score >= 60:
        label = "B"
    elif score >= 35:
        label = "C"
    else:
        label = "D"

    if label == "A":
        next_step = "Informe largo o seguimiento prioritario"
    elif label == "B":
        next_step = "Segunda observación / revisar contexto"
    elif label == "C":
        next_step = "Mantener en base y completar datos"
    else:
        next_step = "Baja prioridad o descartar si no mejora"
    return score, label, signals[:6], next_step


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

    observations_view = observations.copy()
    observations_view["player"] = observations_view["player_id"].map(player_map).fillna("")
    observations_view["team"] = observations_view["team_id"].map(team_map).fillna("")
    observations_view["match"] = observations_view["match_id"].map(match_map).fillna("")

    matches_view = matches.copy()
    matches_view["competition"] = matches_view["competition_id"].map(comp_map).fillna("")
    matches_view["home_team"] = matches_view["home_team_id"].map(team_map).fillna("")
    matches_view["away_team"] = matches_view["away_team_id"].map(team_map).fillna("")

    return teams_view, players_view, matches_view, observations_view, competitions


def player_metrics_table(players_view: pd.DataFrame, observations_view: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, p in players_view.iterrows():
        obs = observations_view[observations_view["player_id"] == p["player_id"]]
        score, label, signals, next_step = priority_score(p, obs)
        ratings = to_num(obs["global_rating"]).dropna() if not obs.empty else pd.Series(dtype=float)
        rows.append({
            **p.to_dict(),
            "observations_count": len(obs),
            "avg_global": round(float(ratings.mean()), 2) if not ratings.empty else "",
            "completion": completeness_for_player(p, len(obs)),
            "priority_score": score,
            "priority_label": label,
            "signals": ", ".join(signals),
            "next_step_calc": next_step,
        })
    return pd.DataFrame(rows)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root { --navy:#121a33; --muted:#6b7280; --line:#e5e7eb; --soft:#f7f7f5; --gold:#d4a831; --green:#eaf7ef; --amber:#fff7ed; }
        .block-container { padding-top: 1.4rem; }
        .hero { border:1px solid #e6e8ee; border-radius:28px; padding:30px 34px; background: radial-gradient(circle at top right, #fff5df 0, #ffffff 34%, #f8fafc 100%); box-shadow: 0 14px 40px rgba(18,26,51,.08); margin-bottom:20px; }
        .eyebrow { display:inline-block; border:1px solid #d7dbe6; border-radius:999px; padding:6px 14px; font-size:13px; font-weight:700; color:#213766; background:#f2f4f8; margin-right:8px; }
        .eyebrow.gold { color:#8a650d; border-color:#ead993; background:#fff8d8; }
        .hero h1 { margin:18px 0 8px 0; color:#111827; font-size:44px; line-height:1.05; letter-spacing:-.04em; }
        .hero p { color:#6b7280; font-size:18px; line-height:1.55; max-width:840px; }
        .kpi-grid { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:14px; margin-top:18px; }
        .kpi { border:1px solid #e5e7eb; background:rgba(255,255,255,.82); border-radius:18px; padding:18px 20px; min-height:96px; box-shadow: 0 8px 26px rgba(17,24,39,.045); }
        .kpi.good { background:#effaf4; border-color:#ccefdc; }
        .kpi.warn { background:#fff7ed; border-color:#fde1bd; }
        .kpi .label { color:#6b7280; font-size:15px; margin-bottom:6px; }
        .kpi .value { color:#111827; font-weight:800; font-size:34px; letter-spacing:-.03em; }
        .panel { border:1px solid #e5e7eb; border-radius:22px; background:white; padding:22px 24px; box-shadow:0 10px 30px rgba(17,24,39,.05); margin:18px 0; }
        .panel h3 { margin:0 0 8px 0; color:#111827; }
        .panel p { color:#6b7280; line-height:1.45; }
        .card-grid { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:14px; }
        .mini-card { border:1px solid #e5e7eb; border-radius:18px; padding:18px; background:#fff; min-height:112px; }
        .mini-card .title { color:#6b7280; font-size:14px; }
        .mini-card .main { color:#111827; font-size:20px; font-weight:800; margin-top:4px; }
        .mini-card .sub { color:#6b7280; font-size:14px; margin-top:6px; }
        .priority-badge { display:inline-flex; align-items:center; justify-content:center; width:44px; height:44px; border-radius:15px; border:1px solid #decf78; background:#fffbe6; color:#8a650d; font-weight:900; font-size:20px; }
        .chip { display:inline-block; border:1px solid #e5e7eb; border-radius:999px; padding:7px 12px; margin:4px 5px 4px 0; background:#fff; color:#1f2937; font-weight:600; }
        .bar-wrap { margin:13px 0 19px 0; }
        .bar-label { display:flex; justify-content:space-between; font-weight:700; color:#374151; margin-bottom:7px; }
        .bar-bg { height:11px; border-radius:999px; background:#e9edf3; overflow:hidden; border:1px solid #d9dee8; }
        .bar-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,#213766,#4b8b57); }
        .pitch { position:relative; width:100%; height:520px; border-radius:26px; background:linear-gradient(90deg,#e9f4ec,#f8fbf9); border:2px solid #b8d2bf; overflow:hidden; }
        .pitch:before { content:""; position:absolute; left:50%; top:0; bottom:0; border-left:2px solid rgba(31,86,46,.35); }
        .pitch:after { content:""; position:absolute; left:50%; top:50%; width:130px; height:130px; transform:translate(-50%,-50%); border:2px solid rgba(31,86,46,.35); border-radius:50%; }
        .pos-dot { position:absolute; transform:translate(-50%,-50%); min-width:70px; height:52px; border-radius:16px; background:white; border:1px solid #d9dee8; box-shadow:0 8px 20px rgba(0,0,0,.10); display:flex; flex-direction:column; align-items:center; justify-content:center; font-weight:800; color:#111827; }
        .pos-dot span { font-size:12px; color:#6b7280; font-weight:700; }
        @media (max-width: 900px) { .kpi-grid{grid-template-columns:repeat(2,1fr);} .card-grid{grid-template-columns:1fr;} .hero h1{font-size:34px;} }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, tag1: str = "Scouting", tag2: str = "Base propia") -> None:
    st.markdown(
        f"""
        <div class="hero">
          <span class="eyebrow">{safe(tag1)}</span><span class="eyebrow gold">{safe(tag2)}</span>
          <h1>{safe(title)}</h1>
          <p>{safe(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_grid(items: List[Tuple[str, str, str]]) -> None:
    html_items = "".join(
        f"<div class='kpi {safe(style)}'><div class='label'>{safe(label)}</div><div class='value'>{safe(value)}</div></div>"
        for label, value, style in items
    )
    st.markdown(f"<div class='kpi-grid'>{html_items}</div>", unsafe_allow_html=True)


def progress_rows(title: str, rows: List[Tuple[str, int]]) -> None:
    if not rows:
        st.info("Sin datos suficientes.")
        return
    max_value = max(v for _, v in rows) or 1
    bits = [f"<h3>{safe(title)}</h3>"]
    for label, value in rows:
        width = int(value / max_value * 100)
        bits.append(
            f"""
            <div class="bar-wrap">
              <div class="bar-label"><span>{safe(label)}</span><span>{value}</span></div>
              <div class="bar-bg"><div class="bar-fill" style="width:{width}%"></div></div>
            </div>
            """
        )
    st.markdown(f"<div class='panel'>{''.join(bits)}</div>", unsafe_allow_html=True)


def render_pitch(players_df: pd.DataFrame) -> None:
    pos_xy = {
        "POR": (7, 50), "LD": (24, 82), "DFC": (24, 50), "LI": (24, 18),
        "CAD": (47, 88), "CAI": (47, 12), "MCD": (43, 50), "MC": (57, 50),
        "MP": (70, 50), "ED": (80, 82), "EI": (80, 18), "SD": (86, 60), "DC": (93, 50),
    }
    counts = players_df["primary_position"].value_counts().to_dict() if not players_df.empty else {}
    dots = []
    for pos, (x, y) in pos_xy.items():
        count = int(counts.get(pos, 0))
        if count:
            dots.append(f"<div class='pos-dot' style='left:{x}%;top:{y}%;'>{safe(pos)}<span>{count} jugadores</span></div>")
        else:
            dots.append(f"<div class='pos-dot' style='left:{x}%;top:{y}%;opacity:.35'>{safe(pos)}<span>0</span></div>")
    st.markdown(f"<div class='pitch'>{''.join(dots)}</div>", unsafe_allow_html=True)


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
            locality = st.text_input("Localidad", key=f"{key}_new_locality")
            locality_band = st.selectbox("Tipo de localidad/fuente", LOCALITY_BANDS, key=f"{key}_new_band")
            if st.button("Guardar equipo/selección", key=f"{key}_save_team"):
                _, created, msg = add_team(new_team, team_type, country_id, competition_id if team_type == "Club" else "", locality, locality_band)
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


def show_duplicate_warning(name: str) -> str:
    players = load_table("players")
    aliases = load_table("aliases")
    norm = normalize_text(name)
    if not norm:
        return ""
    exact = players[players["normalized_name"] == norm]
    if not exact.empty:
        player = exact.iloc[0]
        st.warning(f"Posible duplicado exacto: ya existe **{player['display_name']}**.")
        return str(player["player_id"])
    if len(norm) >= 4:
        partial = players[players["normalized_name"].str.contains(re.escape(norm), na=False) | players["display_name"].str.lower().str.contains(str(name).lower(), na=False)]
        if not partial.empty:
            st.info("Jugadores parecidos: " + ", ".join(partial["display_name"].head(5).tolist()))
    if not aliases.empty:
        alias_match = aliases[aliases["normalized_alias"] == norm]
        if not alias_match.empty:
            pid = alias_match.iloc[0]["player_id"]
            pname = get_name(players, "player_id", pid, "display_name")
            st.warning(f"Ese nombre coincide con un alias de **{pname}**.")
            return str(pid)
    return ""


def page_dashboard() -> None:
    hero(
        "Dashboard de scouting",
        "Panel de control para revisar la base, detectar huecos de información, priorizar jugadores y decidir el siguiente paso de observación.",
        "KPI", "Pipeline"
    )
    teams_view, players_view, matches_view, observations_view, _ = enrich_tables()
    metrics = player_metrics_table(players_view, observations_view) if not players_view.empty else pd.DataFrame()
    avg_completion = int(metrics["completion"].mean()) if not metrics.empty else 0
    avg_age = to_num(players_view["age"]).mean() if not players_view.empty else None
    avg_global = to_num(observations_view["global_rating"]).mean() if not observations_view.empty else None
    kpi_grid([
        ("Jugadores", str(len(players_view)), ""),
        ("Equipos / selecciones", str(len(teams_view)), ""),
        ("Partidos", str(len(matches_view)), ""),
        ("Observaciones", str(len(observations_view)), "good"),
        ("Prioridades A/B", str(int(metrics["priority_label"].isin(["A", "B"]).sum())) if not metrics.empty else "0", "warn"),
        ("Edad media", f"{avg_age:.1f}" if pd.notna(avg_age) else "—", ""),
        ("Nota media", f"{avg_global:.1f}" if pd.notna(avg_global) else "—", ""),
        ("Completitud media", f"{avg_completion}%", "good" if avg_completion >= 60 else "warn"),
    ])

    col1, col2 = st.columns([2, 1])
    with col1:
        if not metrics.empty:
            st.markdown("### Prioridades actuales")
            prio = metrics.sort_values(["priority_score", "observations_count"], ascending=False).head(12)
            st.dataframe(
                prio[["display_name", "current_team", "primary_position", "status", "avg_global", "priority_label", "priority_score", "completion", "next_step_calc"]],
                use_container_width=True,
            )
        else:
            st.info("Todavía no hay jugadores. Empieza en ‘Añadir / puntuar jugador’.")
    with col2:
        st.markdown(
            """
            <div class="panel"><h3>Modelo de trabajo</h3>
            <p>La prioridad combina estado, potencial, nota media, número de observaciones, edad, completitud y etiquetas.</p></div>
            <div class="panel"><h3>Siguiente nivel</h3>
            <p>Cuantas más observaciones y datos añadas, más útil será el scoring para decidir seguimiento, informe o descarte.</p></div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Alertas de calidad")
    alerts = []
    if not players_view.empty:
        alerts.append(("Sin posición", int((players_view["primary_position"].astype(str).str.strip() == "").sum())))
        alerts.append(("Sin equipo", int((players_view["current_team_id"].astype(str).str.strip() == "").sum())))
        alerts.append(("Sin nacionalidad", int((players_view["nationality_id"].astype(str).str.strip() == "").sum())))
        alerts.append(("Sin observaciones", int((metrics["observations_count"] == 0).sum()) if not metrics.empty else 0))
        alerts.append(("Ficha < 50%", int((metrics["completion"] < 50).sum()) if not metrics.empty else 0))
        dupes = load_table("players")
        alerts.append(("Posibles duplicados", int(dupes.duplicated("normalized_name", keep=False).sum()) if not dupes.empty else 0))
    progress_rows("Huecos que conviene limpiar", [(a, v) for a, v in alerts if v > 0])


def page_guided_flow() -> None:
    hero("Añadir / puntuar jugador", "Flujo jerárquico anti-duplicados: país → competición → equipo → plantilla → jugador existente o jugador nuevo → observación.", "Captación", "Entrada rápida")
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

    players = load_table("players")
    roster = players[players["current_team_id"] == team_id].sort_values("display_name")
    st.subheader("Plantilla del equipo seleccionado")
    if roster.empty:
        st.warning("Este equipo todavía no tiene jugadores cargados.")
    else:
        st.dataframe(roster[["display_name", "primary_position", "age", "status", "potential", "tags"]], use_container_width=True)

    with st.expander("+ Cargar plantilla de golpe", expanded=False):
        bulk_text = st.text_area("Un jugador por línea", height=160, placeholder="Jugador Uno\nJugador Dos\nJugador Tres")
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

    mode = st.radio("¿Qué quieres hacer?", ["Puntuar jugador existente", "Añadir jugador nuevo"], horizontal=True)
    selected_player_id = ""
    if mode == "Puntuar jugador existente":
        selected_player_id = player_select("Jugador", team_id, "flow_existing_player")
    else:
        with st.form("new_player_form"):
            name = st.text_input("Nombre del jugador")
            duplicate_id = show_duplicate_warning(name)
            c1, c2, c3, c4 = st.columns(4)
            primary = c1.selectbox("Posición principal", [""] + POSITIONS)
            secondary = c2.selectbox("Posición secundaria", [""] + POSITIONS)
            foot = c3.selectbox("Pierna", FOOTS)
            age = c4.text_input("Edad")
            c5, c6, c7, c8 = st.columns(4)
            height = c5.text_input("Altura cm")
            status = c6.selectbox("Estado", PLAYER_STATUS)
            potential = c7.selectbox("Potencial", ["", "Bajo", "Medio", "Medio-alto", "Alto", "Muy alto"])
            priority_manual = c8.selectbox("Prioridad manual", [""] + PRIORITY_LABELS)
            source = st.selectbox("Fuente", SOURCE_TYPES)
            tags = st.text_input("Etiquetas", placeholder="Sub-21, físico top, diferencial, revisar...")
            notes = st.text_area("Notas generales")
            submitted = st.form_submit_button("Guardar jugador")
            if submitted:
                if duplicate_id:
                    st.warning("No lo he creado porque parece duplicado. Selecciona el existente o fusiona desde Duplicados.")
                else:
                    pid, created, msg = add_player(
                        name, nationality_id=country_id, primary_position=primary, secondary_position=secondary,
                        dominant_foot=foot, age=age, height_cm=height, current_team_id=team_id,
                        status=status, priority_manual=priority_manual, potential=potential, source=source,
                        tags=tags, general_notes=notes, entry_date=str(date.today()), entry_age=age,
                    )
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
        match_labels = {"": "— Sin partido / crear rápido —"}
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
            next_step = st.text_input("Próximo paso", placeholder="Ver otro partido, informe largo, descartar, consultar contexto...")
            if st.form_submit_button("Guardar observación"):
                _, created, msg = add_observation(
                    player_id=selected_player_id, match_id=selected_match, team_id=team_id,
                    observed_position=observed_pos, minutes_observed=minutes, role=role, action_type=action_type,
                    minute_note=minute_note, positive_notes=pos_notes, improvement_notes=imp_notes,
                    technical_rating=str(technical), tactical_rating=str(tactical), physical_rating=str(physical),
                    mental_rating=str(mental), global_rating=str(global_rating), recommendation=recommendation, next_step=next_step,
                )
                st.success(msg) if created else st.error(msg)


def page_structure() -> None:
    hero("Estructura", "Administra países, competiciones, equipos, selecciones y localidades de origen.", "Datos maestros", "Orden")
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
        st.caption("En el flujo guiado no necesitas tocar IDs; esta tabla es para mantenimiento fino.")
        edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="edit_comps")
        if st.button("Guardar competiciones"):
            edited["normalized_name"] = edited["name"].apply(normalize_text)
            save_table("competitions", edited)
            st.success("Competiciones guardadas.")
    with tab3:
        teams_view, _, _, _, _ = enrich_tables()
        st.dataframe(teams_view[["team_id", "name", "team_type", "country", "competition", "locality", "locality_band"]], use_container_width=True)
        df = load_table("teams")
        edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="edit_teams")
        if st.button("Guardar equipos"):
            edited["normalized_name"] = edited["name"].apply(normalize_text)
            save_table("teams", edited)
            st.success("Equipos guardados.")


def page_matches() -> None:
    hero("Partidos", "Crea partidos y vincula observaciones para que cada jugador tenga contexto real de seguimiento.", "Observación", "Contexto")
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
        if st.form_submit_button("Crear partido"):
            _, created, msg = add_match(str(mdate), mname, competition_id, home_id, away_id, season, context)
            st.success(msg) if created else st.info(msg)
    _, _, matches_view, _, _ = enrich_tables()
    st.dataframe(matches_view[["match_id", "match_date", "match_name", "competition", "home_team", "away_team", "season", "context"]], use_container_width=True)


def page_players() -> None:
    hero("Jugadores", "Base individual con ficha, scoring automático, señales de prioridad y observaciones acumuladas.", "Catálogo", "Ficha")
    _, players_view, _, observations_view, _ = enrich_tables()
    if players_view.empty:
        st.warning("Todavía no hay jugadores.")
        return
    metrics = player_metrics_table(players_view, observations_view)
    c1, c2, c3, c4 = st.columns(4)
    pos_filter = c1.multiselect("Posición", POSITIONS)
    status_filter = c2.multiselect("Estado", PLAYER_STATUS)
    priority_filter = c3.multiselect("Prioridad", PRIORITY_LABELS)
    search = c4.text_input("Buscar")
    df = metrics.copy()
    if pos_filter:
        df = df[df["primary_position"].isin(pos_filter)]
    if status_filter:
        df = df[df["status"].isin(status_filter)]
    if priority_filter:
        df = df[df["priority_label"].isin(priority_filter)]
    if search:
        df = df[df["display_name"].str.contains(search, case=False, na=False)]
    st.dataframe(
        df[["player_id", "display_name", "current_team", "nationality", "primary_position", "age", "status", "potential", "priority_label", "priority_score", "completion", "observations_count", "avg_global"]],
        use_container_width=True,
    )

    st.subheader("Ficha individual")
    options = [""] + metrics["player_id"].tolist()
    labels = {"": "— Seleccionar —"}
    labels.update(dict(zip(metrics["player_id"], metrics["display_name"])))
    pid = st.selectbox("Jugador", options, format_func=lambda x: labels.get(x, x))
    if not pid:
        return
    player = metrics[metrics["player_id"] == pid].iloc[0]
    obs = observations_view[observations_view["player_id"] == pid]
    score, label, signals, next_step = priority_score(player, obs)
    st.markdown(
        f"""
        <div class="panel">
          <div class="card-grid">
            <div class="mini-card"><div class="title">Jugador</div><div class="main">{safe(player['display_name'])}</div><div class="sub">{safe(player.get('primary_position',''))} · {safe(player.get('current_team',''))}</div></div>
            <div class="mini-card"><div class="title">Prioridad scouting</div><div class="main"><span class="priority-badge">{label}</span> {score}/100</div><div class="sub">{safe(next_step)}</div></div>
            <div class="mini-card"><div class="title">Completitud</div><div class="main">{int(player['completion'])}%</div><div class="sub">datos + observaciones</div></div>
            <div class="mini-card"><div class="title">Edad / entrada</div><div class="main">{safe(player.get('age','—'))}</div><div class="sub">entrada: {safe(player.get('entry_age',''))}</div></div>
            <div class="mini-card"><div class="title">Contacto</div><div class="main">{safe(player.get('phone','Brak') or 'Sin teléfono')}</div><div class="sub">{safe(player.get('email','Sin email') or 'Sin email')}</div></div>
            <div class="mini-card"><div class="title">Hoja de tests</div><div class="main">{safe(player.get('test_sheet','Sin tests') or 'Sin tests')}</div><div class="sub">fuente: {safe(player.get('source',''))}</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("**Señales del scoring:** " + " ".join([f"<span class='chip'>{safe(s)}</span>" for s in signals]), unsafe_allow_html=True)
    st.write("**Notas generales:**", player.get("general_notes", ""))
    if not obs.empty:
        st.subheader("Observaciones acumuladas")
        st.dataframe(obs[["created_at", "match", "observed_position", "role", "action_type", "global_rating", "recommendation", "next_step", "positive_notes", "improvement_notes"]], use_container_width=True)
        report = f"# Informe rápido - {player['display_name']}\n\n"
        report += f"Equipo: {player.get('current_team','')}\nPosición: {player.get('primary_position','')}\nPrioridad: {label} ({score}/100)\nEstado: {player.get('status','')}\n\n"
        report += f"Señales: {', '.join(signals)}\nPróximo paso: {next_step}\n\n"
        for _, r in obs.iterrows():
            report += f"## {r.get('match','Sin partido')} · {r.get('created_at','')}\n"
            report += f"Posición: {r.get('observed_position','')} · Rol: {r.get('role','')} · Nota: {r.get('global_rating','')}\n"
            report += f"Positivo: {r.get('positive_notes','')}\n"
            report += f"Mejora/dudas: {r.get('improvement_notes','')}\n"
            report += f"Próximo paso: {r.get('next_step','')}\n\n"
        st.download_button("Descargar informe TXT", report.encode("utf-8"), file_name=f"informe_{normalize_text(player['display_name']).replace(' ','_')}.txt")
    else:
        st.info("Este jugador todavía no tiene observaciones.")


def page_research() -> None:
    hero(
        "Pestaña de investigación",
        "Vista para responder preguntas estratégicas: qué edades aparecen, qué mercados cubres mejor, de qué fuentes salen perfiles interesantes y dónde faltan datos.",
        "Análisis", "Scouting + decisión"
    )
    teams_view, players_view, _, observations_view, _ = enrich_tables()
    metrics = player_metrics_table(players_view, observations_view) if not players_view.empty else pd.DataFrame()
    avg_entry = to_num(players_view["entry_age"]).mean() if not players_view.empty else None
    avg_age = to_num(players_view["age"]).mean() if not players_view.empty else None
    completion = int(metrics["completion"].mean()) if not metrics.empty else 0
    kpi_grid([
        ("Edad media actual", f"{avg_age:.1f}" if pd.notna(avg_age) else "—", ""),
        ("Edad media de entrada", f"{avg_entry:.1f}" if pd.notna(avg_entry) else "—", ""),
        ("Completitud analítica", f"{completion}%", "good" if completion >= 60 else "warn"),
        ("Jugadores sin 2ª observación", str(int((metrics["observations_count"] < 2).sum())) if not metrics.empty else "0", "warn"),
    ])

    col1, col2 = st.columns(2)
    with col1:
        if not teams_view.empty:
            rows = teams_view["locality_band"].replace("", "Sin datos").value_counts().head(10)
            progress_rows("Procedencia / tipo de fuente", list(zip(rows.index.tolist(), rows.astype(int).tolist())))
        if not players_view.empty:
            rows = players_view["source"].replace("", "Sin datos").value_counts().head(10)
            progress_rows("Canales de entrada", list(zip(rows.index.tolist(), rows.astype(int).tolist())))
    with col2:
        if not metrics.empty:
            rows = metrics["primary_position"].replace("", "Sin posición").value_counts().head(12)
            progress_rows("Posiciones más observadas", list(zip(rows.index.tolist(), rows.astype(int).tolist())))
            top_countries = metrics["nationality"].replace("", "Sin datos").value_counts().head(10)
            progress_rows("Países / nacionalidades", list(zip(top_countries.index.tolist(), top_countries.astype(int).tolist())))

    st.markdown(
        """
        <div class="panel"><h3>Mapa de preguntas de scouting</h3>
        <div class="card-grid">
          <div class="mini-card"><div class="main">Edad de entrada</div><div class="sub">¿Detectas jugadores demasiado tarde, demasiado pronto o en el momento adecuado?</div></div>
          <div class="mini-card"><div class="main">Procedencia</div><div class="sub">¿Qué países, clubes, ligas o selecciones generan más perfiles interesantes?</div></div>
          <div class="mini-card"><div class="main">Fuentes</div><div class="sub">¿Qué canal da mejores entradas: partidos, torneos, recomendaciones, bases de datos o directo?</div></div>
          <div class="mini-card"><div class="main">Seguimiento</div><div class="sub">¿Quién necesita segunda observación antes de pasar a informe o descarte?</div></div>
          <div class="mini-card"><div class="main">Cobertura</div><div class="sub">¿Qué posiciones o mercados están sobrerrepresentados y cuáles están vacíos?</div></div>
          <div class="mini-card"><div class="main">Calidad de decisión</div><div class="sub">¿Tus prioridades A/B tienen datos suficientes o solo una primera impresión?</div></div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )


def page_duplicate_center() -> None:
    hero("Control de duplicados", "Detecta nombres iguales sin tildes/mayúsculas y fusiona fichas duplicadas sin perder observaciones.", "Limpieza", "Anti-duplicados")
    players = load_table("players")
    if players.empty:
        st.warning("No hay jugadores.")
        return
    dupes = players[players.duplicated("normalized_name", keep=False)].sort_values("normalized_name")
    if dupes.empty:
        st.success("No hay duplicados exactos por nombre normalizado.")
    else:
        st.warning("Duplicados exactos detectados:")
        st.dataframe(dupes[["player_id", "display_name", "normalized_name", "current_team_id", "primary_position"]], use_container_width=True)

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

    st.subheader("Añadir alias")
    alias_player = st.selectbox("Jugador", options, format_func=lambda x: labels.get(x, x), key="alias_player")
    alias_text = st.text_input("Alias / variante de escritura")
    if st.button("Guardar alias") and alias_player and alias_text:
        aliases = load_table("aliases")
        alias_id = next_id(aliases, "ALS", "alias_id")
        aliases.loc[len(aliases)] = [alias_id, alias_player, alias_text, normalize_text(alias_text), now_str()]
        save_table("aliases", aliases)
        st.success("Alias guardado.")


def page_pitch_and_compare() -> None:
    hero("Campograma y comparador", "Vista posicional sin dependencias externas y comparación rápida de dos jugadores por métricas acumuladas.", "Visual", "Comparativa")
    _, players_view, _, observations_view, _ = enrich_tables()
    if players_view.empty:
        st.warning("No hay jugadores.")
        return
    st.subheader("Campograma por posición principal")
    render_pitch(players_view)

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
        score, label, _, next_step = priority_score(player, obs)
        rows.append({
            "Jugador": player["display_name"],
            "Equipo": player.get("current_team", ""),
            "Posición": player.get("primary_position", ""),
            "Observaciones": len(obs),
            "Técnica": round(to_num(obs["technical_rating"]).mean(), 2) if not obs.empty else "",
            "Táctica": round(to_num(obs["tactical_rating"]).mean(), 2) if not obs.empty else "",
            "Físico": round(to_num(obs["physical_rating"]).mean(), 2) if not obs.empty else "",
            "Mental": round(to_num(obs["mental_rating"]).mean(), 2) if not obs.empty else "",
            "Global": round(to_num(obs["global_rating"]).mean(), 2) if not obs.empty else "",
            "Prioridad": label,
            "Score": score,
            "Próximo paso": next_step,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


def page_data_editor() -> None:
    hero("Base editable", "Editor directo de tablas para mantenimiento avanzado. Úsalo con cuidado y exporta antes de cambios grandes.", "Admin", "Tablas")
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
    hero("Backup / importar / exportar", "Exporta siempre al terminar en Streamlit Cloud. Puedes reimportar ZIP o Excel para continuar más adelante.", "Seguridad", "Portabilidad")
    c1, c2 = st.columns(2)
    c1.download_button("Descargar Excel completo", make_excel_bytes(), file_name="scouting_hub_backup.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    c2.download_button("Descargar ZIP completo", make_zip_bytes(), file_name="scouting_hub_backup.zip", mime="application/zip")
    st.subheader("CSV individuales")
    for table in SCHEMAS:
        st.download_button(f"Descargar {table}.csv", dataframe_download_csv(load_table(table)), file_name=f"{table}.csv", key=f"down_{table}")
    st.divider()
    uploaded = st.file_uploader("Sube un ZIP o Excel exportado por la app", type=["zip", "xlsx"])
    if uploaded is not None and st.button("Importar archivo"):
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


def page_dataset_info() -> None:
    hero("Dataset inicial 2025/26", "Estructura precargada con grandes ligas, segundas divisiones y un paquete de jugadores semilla para arrancar el trabajo sin la base vacía.", "Datos", "Starter")
    teams = load_table("teams")
    players = load_table("players")
    comps = load_table("competitions")
    countries = load_table("countries")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Países", len(countries))
    c2.metric("Competiciones", len(comps))
    c3.metric("Equipos/selecciones", len(teams))
    c4.metric("Jugadores semilla", len(players))
    st.info("El dataset inicial está pensado para empezar a trabajar y filtrar, no como certificado oficial de inscripción de plantilla. Las plantillas cambian con mercado, lesiones y dorsales; por eso la app mantiene importación/exportación para que puedas corregir y enriquecer tu propia base.")
    st.subheader("Cobertura por competición")
    if not teams.empty:
        _, teams_view, _, _, _ = enrich_tables()[0], None, None, None, None
        teams_view = enrich_tables()[0]
        coverage = teams_view.groupby(["country", "competition", "team_type"], dropna=False).size().reset_index(name="equipos")
        st.dataframe(coverage.sort_values(["country", "competition"]), use_container_width=True)
    st.subheader("Jugadores cargados por equipo")
    if not players.empty and not teams.empty:
        teams_view, players_view, *_ = enrich_tables()
        counts = players_view.groupby("current_team").size().reset_index(name="jugadores").sort_values("jugadores", ascending=False)
        st.dataframe(counts, use_container_width=True)
    st.subheader("Siguiente paso recomendado")
    st.write("Usa **Añadir / puntuar jugador** para cargar plantillas completas por equipo cuando vayas viendo partidos. Si un jugador ya existe con tilde/sin tilde, el control de duplicados lo detecta mediante nombre normalizado y alias.")


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide", page_icon="⚽")
    inject_css()
    ensure_seed_data()
    st.sidebar.title("⚽ Scouting Hub")
    page = st.sidebar.radio(
        "Navegación",
        [
            "Dashboard",
            "Añadir / puntuar jugador",
            "Estructura",
            "Partidos",
            "Jugadores",
            "Investigación",
            "Duplicados",
            "Campograma / comparador",
            "Base editable",
            "Dataset inicial",
            "Backup / Importar / Exportar",
        ],
    )
    if page == "Dashboard":
        page_dashboard()
    elif page == "Añadir / puntuar jugador":
        page_guided_flow()
    elif page == "Estructura":
        page_structure()
    elif page == "Partidos":
        page_matches()
    elif page == "Jugadores":
        page_players()
    elif page == "Investigación":
        page_research()
    elif page == "Duplicados":
        page_duplicate_center()
    elif page == "Campograma / comparador":
        page_pitch_and_compare()
    elif page == "Base editable":
        page_data_editor()
    elif page == "Dataset inicial":
        page_dataset_info()
    elif page == "Backup / Importar / Exportar":
        page_backup()


if __name__ == "__main__":
    main()
