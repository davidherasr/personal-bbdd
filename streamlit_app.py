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

APP_TITLE = "Scouting Hub v0.7"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

POSITIONS = ["POR", "LD", "DFC", "LI", "CAD", "CAI", "MCD", "MC", "MP", "ED", "EI", "SD", "DC"]
FOOTS = ["", "Derecha", "Izquierda", "Ambas"]
PLAYER_STATUS = ["Sin valorar", "Seguir", "Revisar", "Prioritario", "Descartar", "Fichaje recomendado"]
TEAM_TYPES = ["Club", "Selección"]
SOURCE_TYPES = ["", "Partido completo", "Directo", "Torneo", "Recomendación", "Base de datos", "Vídeo", "Entrenador", "Otro"]
PRIORITY_LABELS = ["A", "B+", "B", "C", "D"]

ROLE_TYPES = [
    "", "Portero constructor", "Portero dominador de área", "Central dominante", "Central corrector",
    "Central de salida", "Lateral largo", "Lateral corto/interior", "Carrilero",
    "Pivote posicional", "Pivote defensivo", "Interior ida y vuelta", "Interior creativo",
    "Mediapunta libre", "Extremo abierto", "Extremo interior", "Segundo punta",
    "Nueve referencia", "Nueve móvil", "Delantero presionante"
]

TACTICAL_FITS = ["", "Muy alto", "Alto", "Medio-alto", "Medio", "Bajo", "Muy bajo"]
POSITION_NEED_LEVELS = ["", "Alta", "Media", "Baja"]
RELIABILITY_LEVELS = ["", "Alta", "Media", "Baja"]
TREND_LEVELS = ["", "Sube", "Mantiene", "Baja"]
OPPOSITION_LEVELS = ["", "Muy alto", "Alto", "Medio", "Bajo"]
MATCH_DIFFICULTIES = ["", "Muy alta", "Alta", "Media", "Baja"]

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
        "status", "priority_manual", "potential", "primary_role", "secondary_role", "tactical_fit",
        "position_need", "source", "phone", "email", "test_sheet",
        "entry_date", "entry_age", "tags", "general_notes", "created_at"
    ],
    "matches": [
        "match_id", "match_date", "match_name", "competition_id", "home_team_id", "away_team_id",
        "season", "context", "created_at"
    ],
    "observations": [
        "observation_id", "player_id", "match_id", "team_id", "observed_position", "minutes_observed",
        "role", "action_type", "minute_note", "positive_notes", "improvement_notes", "technical_rating",
        "tactical_rating", "physical_rating", "mental_rating", "global_rating", "recommendation",
        "next_step", "viewing_type", "opposition_level", "match_difficulty", "reliability", "trend", "created_at"
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


FOOTBALL_DATA_SOURCES = [
    {"country": "Inglaterra", "competition": "Premier League", "level": "1ª", "code": "E0", "url": "https://www.football-data.co.uk/mmz4281/2526/E0.csv"},
    {"country": "Inglaterra", "competition": "Championship", "level": "2ª", "code": "E1", "url": "https://www.football-data.co.uk/mmz4281/2526/E1.csv"},
    {"country": "Inglaterra", "competition": "League One", "level": "3ª", "code": "E2", "url": "https://www.football-data.co.uk/mmz4281/2526/E2.csv"},
    {"country": "España", "competition": "LaLiga", "level": "1ª", "code": "SP1", "url": "https://www.football-data.co.uk/mmz4281/2526/SP1.csv"},
    {"country": "España", "competition": "LaLiga Hypermotion", "level": "2ª", "code": "SP2", "url": "https://www.football-data.co.uk/mmz4281/2526/SP2.csv"},
    {"country": "Italia", "competition": "Serie A", "level": "1ª", "code": "I1", "url": "https://www.football-data.co.uk/mmz4281/2526/I1.csv"},
    {"country": "Italia", "competition": "Serie B", "level": "2ª", "code": "I2", "url": "https://www.football-data.co.uk/mmz4281/2526/I2.csv"},
    {"country": "Alemania", "competition": "Bundesliga", "level": "1ª", "code": "D1", "url": "https://www.football-data.co.uk/mmz4281/2526/D1.csv"},
    {"country": "Alemania", "competition": "2. Bundesliga", "level": "2ª", "code": "D2", "url": "https://www.football-data.co.uk/mmz4281/2526/D2.csv"},
    {"country": "Francia", "competition": "Ligue 1", "level": "1ª", "code": "F1", "url": "https://www.football-data.co.uk/mmz4281/2526/F1.csv"},
    {"country": "Francia", "competition": "Ligue 2", "level": "2ª", "code": "F2", "url": "https://www.football-data.co.uk/mmz4281/2526/F2.csv"},
]

EXPECTED_PLAYER_COLUMNS = [
    "country", "competition", "team", "player_name", "birth_date", "age", "nationality",
    "primary_position", "secondary_position", "dominant_foot", "height_cm", "status", "potential",
    "primary_role", "secondary_role", "tactical_fit", "position_need", "tags", "source"
]
EXPECTED_MATCH_COLUMNS = ["country", "competition", "season", "match_date", "home_team", "away_team", "matchday", "context"]
EXPECTED_TEAM_COLUMNS = ["country", "competition", "team_type", "team", "locality", "locality_band"]


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
        "primary_role": kwargs.get("primary_role", ""),
        "secondary_role": kwargs.get("secondary_role", ""),
        "tactical_fit": kwargs.get("tactical_fit", ""),
        "position_need": kwargs.get("position_need", ""),
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
        "display_name", "age", "nationality_id", "primary_position", "primary_role", "dominant_foot", "height_cm",
        "current_team_id", "status", "potential", "tactical_fit", "position_need", "source", "tags", "general_notes"
    ]
    filled = sum(1 for field in fields if str(row.get(field, "")).strip())
    score = filled / len(fields) * 82
    if obs_count > 0:
        score += 12
    if obs_count >= 2:
        score += 6
    return int(round(min(100, score)))


POSITION_WEIGHTS: Dict[str, Dict[str, float]] = {
    "POR": {"technical_rating": .20, "tactical_rating": .25, "physical_rating": .15, "mental_rating": .25, "global_rating": .15},
    "DFC": {"technical_rating": .15, "tactical_rating": .30, "physical_rating": .20, "mental_rating": .20, "global_rating": .15},
    "LD": {"technical_rating": .20, "tactical_rating": .25, "physical_rating": .25, "mental_rating": .15, "global_rating": .15},
    "LI": {"technical_rating": .20, "tactical_rating": .25, "physical_rating": .25, "mental_rating": .15, "global_rating": .15},
    "CAD": {"technical_rating": .22, "tactical_rating": .20, "physical_rating": .28, "mental_rating": .12, "global_rating": .18},
    "CAI": {"technical_rating": .22, "tactical_rating": .20, "physical_rating": .28, "mental_rating": .12, "global_rating": .18},
    "MCD": {"technical_rating": .20, "tactical_rating": .35, "physical_rating": .10, "mental_rating": .20, "global_rating": .15},
    "MC": {"technical_rating": .25, "tactical_rating": .30, "physical_rating": .10, "mental_rating": .20, "global_rating": .15},
    "MP": {"technical_rating": .30, "tactical_rating": .25, "physical_rating": .10, "mental_rating": .20, "global_rating": .15},
    "ED": {"technical_rating": .30, "tactical_rating": .20, "physical_rating": .25, "mental_rating": .10, "global_rating": .15},
    "EI": {"technical_rating": .30, "tactical_rating": .20, "physical_rating": .25, "mental_rating": .10, "global_rating": .15},
    "SD": {"technical_rating": .27, "tactical_rating": .24, "physical_rating": .14, "mental_rating": .20, "global_rating": .15},
    "DC": {"technical_rating": .25, "tactical_rating": .20, "physical_rating": .20, "mental_rating": .20, "global_rating": .15},
}

POTENTIAL_POINTS = {"Muy alto": 92, "Alto": 82, "Medio-alto": 70, "Medio": 56, "Bajo": 34, "Muy bajo": 20}
FIT_POINTS = {"Muy alto": 92, "Alto": 80, "Medio-alto": 68, "Medio": 55, "Bajo": 35, "Muy bajo": 18}
NEED_POINTS = {"Alta": 88, "Media": 62, "Baja": 38, "": 50}
STATUS_URGENCY = {"Fichaje recomendado": 90, "Prioritario": 82, "Seguir": 66, "Revisar": 55, "Sin valorar": 45, "Descartar": 10}
SOURCE_CONFIDENCE = {"Partido completo": 18, "Directo": 16, "Torneo": 13, "Vídeo": 11, "Base de datos": 7, "Recomendación": 6, "Entrenador": 8, "Otro": 4, "": 0}
RELIABILITY_CONFIDENCE = {"Alta": 12, "Media": 7, "Baja": 2, "": 0}
TREND_POINTS = {"Sube": 8, "Mantiene": 3, "Baja": -8, "": 0}


def _mean_rating(obs: pd.DataFrame, col: str) -> float | None:
    if obs.empty or col not in obs.columns:
        return None
    values = to_num(obs[col]).dropna()
    if values.empty:
        return None
    return float(values.mean())


def observed_level_score(player: pd.Series, obs: pd.DataFrame) -> int:
    if obs.empty:
        return 0
    pos = str(player.get("primary_position", "")).strip() or str(obs.iloc[-1].get("observed_position", "")).strip()
    weights = POSITION_WEIGHTS.get(pos, {"technical_rating": .25, "tactical_rating": .25, "physical_rating": .20, "mental_rating": .15, "global_rating": .15})
    total_weight = 0.0
    total = 0.0
    for col, weight in weights.items():
        val = _mean_rating(obs, col)
        if val is not None:
            total += val * 10 * weight
            total_weight += weight
    if total_weight == 0:
        return 0
    score = total / total_weight
    # Tendencia reciente: las últimas observaciones pesan un poco más si la tendencia está marcada.
    if "trend" in obs.columns:
        recent_trends = [TREND_POINTS.get(str(x), 0) for x in obs["trend"].tail(3).tolist()]
        score += sum(recent_trends) / max(1, len(recent_trends))
    return int(round(max(0, min(100, score))))


def potential_score(player: pd.Series) -> int:
    potential = str(player.get("potential", "")).strip()
    base = POTENTIAL_POINTS.get(potential, 50)
    age = pd.to_numeric(pd.Series([player.get("age", "")]), errors="coerce").iloc[0]
    if pd.notna(age):
        if age <= 18:
            base += 10
        elif age <= 21:
            base += 7
        elif age <= 23:
            base += 4
        elif age >= 31:
            base -= 10
    tags = normalize_text(player.get("tags", ""))
    if any(word in tags for word in ["proyeccion", "sub-21", "sub21", "joven", "margen"]):
        base += 6
    if "techo bajo" in tags or "sin margen" in tags:
        base -= 8
    return int(round(max(0, min(100, base))))


def fit_score(player: pd.Series) -> int:
    base = FIT_POINTS.get(str(player.get("tactical_fit", "")).strip(), 50)
    need = NEED_POINTS.get(str(player.get("position_need", "")).strip(), 50)
    role_bonus = 8 if str(player.get("primary_role", "")).strip() else 0
    tags = normalize_text(player.get("tags", ""))
    if any(word in tags for word in ["encaje", "modelo", "presion", "posicional", "vertical", "rest defence", "rest-defense"]):
        role_bonus += 5
    if any(word in tags for word in ["no encaja", "duda tactica", "dudas tacticas"]):
        role_bonus -= 10
    score = base * .70 + need * .25 + role_bonus
    return int(round(max(0, min(100, score))))


def confidence_score(player: pd.Series, obs: pd.DataFrame) -> int:
    comp = completeness_for_player(player, len(obs))
    obs_count = len(obs)
    minutes = to_num(obs["minutes_observed"]).fillna(0).sum() if not obs.empty and "minutes_observed" in obs.columns else 0
    score = min(32, obs_count * 12)
    score += min(25, float(minutes) / 180 * 25) if minutes else 0
    score += comp * .28
    score += SOURCE_CONFIDENCE.get(str(player.get("source", "")).strip(), 0)
    if not obs.empty and "reliability" in obs.columns:
        score += max([RELIABILITY_CONFIDENCE.get(str(x), 0) for x in obs["reliability"].tolist()] or [0])
    if obs_count == 0:
        score = min(score, 35)
    elif obs_count == 1 and minutes < 60:
        score = min(score, 55)
    return int(round(max(0, min(100, score))))


def urgency_score(player: pd.Series, obs: pd.DataFrame) -> int:
    status = str(player.get("status", "")).strip()
    score = STATUS_URGENCY.get(status, 45)
    if len(obs) == 1:
        score += 8
    if len(obs) == 0:
        score += 4
    tags = normalize_text(player.get("tags", ""))
    if any(word in tags for word in ["urgente", "mercado", "libre", "cesion", "prioritario"]):
        score += 10
    if "descartar" in tags or status == "Descartar":
        score -= 35
    return int(round(max(0, min(100, score))))


def scoring_breakdown(player: pd.Series, obs: pd.DataFrame) -> Dict[str, object]:
    level = observed_level_score(player, obs)
    pot = potential_score(player)
    fit = fit_score(player)
    conf = confidence_score(player, obs)
    urgency = urgency_score(player, obs)
    if level == 0 and obs.empty:
        # Sin observaciones: ranking de cartera, no de rendimiento.
        base = pot * .36 + fit * .34 + urgency * .20 + completeness_for_player(player, 0) * .10
    else:
        base = level * .40 + pot * .25 + fit * .20 + urgency * .15
    final = base * (0.70 + 0.30 * (conf / 100))

    status = str(player.get("status", "")).strip()
    if status == "Descartar":
        final = min(final, 42)
    if status == "Fichaje recomendado" and conf < 55:
        final = min(final, 74)

    label = "D"
    if base >= 82 and conf < 50:
        label = "B+"
    elif final >= 80 and conf >= 65:
        label = "A"
    elif final >= 68:
        label = "B"
    elif final >= 50:
        label = "C"

    manual = str(player.get("priority_manual", "")).strip()
    # La prioridad manual se muestra como señal, pero no machaca el motor si no hay confianza.
    if manual == "A" and conf >= 65 and final >= 70:
        label = "A"
    elif manual in ["B+", "B"] and final >= 55:
        label = manual

    positive: List[str] = []
    alerts: List[str] = []
    if level >= 75:
        positive.append(f"nivel observado {level}")
    if pot >= 78:
        positive.append(f"potencial {pot}")
    if fit >= 75:
        positive.append(f"encaje {fit}")
    if conf >= 70:
        positive.append("evidencia sólida")
    if len(obs) >= 2:
        positive.append("2+ observaciones")
    if status:
        positive.append(f"estado: {status.lower()}")
    if str(player.get("primary_role", "")).strip():
        positive.append(f"rol: {str(player.get('primary_role')).lower()}")

    if obs.empty:
        alerts.append("sin observaciones")
    elif len(obs) == 1:
        alerts.append("solo una observación")
    if conf < 45:
        alerts.append("confianza baja")
    if level >= 78 and conf < 55:
        alerts.append("nota alta con poca muestra")
    if completeness_for_player(player, len(obs)) < 50:
        alerts.append("ficha incompleta")
    if not str(player.get("primary_position", "")).strip():
        alerts.append("sin posición")
    if status == "Prioritario" and conf < 55:
        alerts.append("prioritario sin evidencia suficiente")

    if level >= 78 and conf >= 65:
        next_step = "Informe largo / decisión fuerte"
    elif level >= 75 and conf < 65:
        next_step = "Segunda observación urgente"
    elif pot >= 78 and conf < 55:
        next_step = "Validar potencial con partido completo"
    elif fit >= 75 and conf >= 50:
        next_step = "Revisar encaje por rol y comparar por posición"
    elif status == "Descartar" and conf >= 60:
        next_step = "Descarte razonado"
    elif conf < 40:
        next_step = "Completar ficha antes de decidir"
    else:
        next_step = "Seguimiento normal"

    evidence = "Alta" if conf >= 70 else "Media" if conf >= 50 else "Baja"
    return {
        "observed_level": int(level),
        "potential_score": int(pot),
        "fit_score": int(fit),
        "confidence_score": int(conf),
        "urgency_score": int(urgency),
        "priority_base": int(round(base)),
        "priority_score": int(round(max(0, min(100, final)))),
        "priority_label": label,
        "evidence_level": evidence,
        "signals": positive[:7],
        "alerts": alerts[:7],
        "next_step": next_step,
    }


def priority_score(player: pd.Series, obs: pd.DataFrame) -> Tuple[int, str, List[str], str]:
    data = scoring_breakdown(player, obs)
    signals = [str(x) for x in data.get("signals", [])]
    alerts = [str(x) for x in data.get("alerts", [])]
    return int(data["priority_score"]), str(data["priority_label"]), (signals + alerts)[:6], str(data["next_step"])


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
        scoring = scoring_breakdown(p, obs)
        ratings = to_num(obs["global_rating"]).dropna() if not obs.empty and "global_rating" in obs.columns else pd.Series(dtype=float)
        row = {
            **p.to_dict(),
            "observations_count": len(obs),
            "minutes_total": int(to_num(obs["minutes_observed"]).fillna(0).sum()) if not obs.empty and "minutes_observed" in obs.columns else 0,
            "avg_global": round(float(ratings.mean()), 2) if not ratings.empty else "",
            "completion": completeness_for_player(p, len(obs)),
            **scoring,
            "signals_text": ", ".join(scoring.get("signals", [])),
            "alerts_text": ", ".join(scoring.get("alerts", [])),
            "next_step_calc": scoring.get("next_step", ""),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def score_card(title: str, value: object, subtitle: str = "", tone: str = "") -> None:
    cls = "mini-card"
    if tone:
        cls += f" {tone}"
    st.markdown(
        f"""<div class=\"{cls}\"><div class=\"title\">{safe(title)}</div><div class=\"main\">{safe(value)}</div><div class=\"sub\">{safe(subtitle)}</div></div>""",
        unsafe_allow_html=True,
    )


def score_bar(label: str, value: int, hint: str = "") -> str:
    value = int(max(0, min(100, value)))
    return f"""
    <div class="score-row">
      <div class="score-head"><span>{safe(label)}</span><strong>{value}/100</strong></div>
      <div class="score-track"><div class="score-fill" style="width:{value}%"></div></div>
      <div class="score-hint">{safe(hint)}</div>
    </div>
    """


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
        
        .score-row { margin: 10px 0 14px 0; }
        .score-head { display:flex; justify-content:space-between; color:#111827; font-size:14px; margin-bottom:6px; }
        .score-track { height:10px; border-radius:999px; background:#eef2f7; overflow:hidden; border:1px solid #e5e7eb; }
        .score-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,#213766,#4f8b5f); }
        .score-hint { color:#6b7280; font-size:12px; margin-top:4px; }
        .rank-badge { display:inline-flex; align-items:center; justify-content:center; min-width:44px; height:34px; padding:0 12px; border-radius:999px; border:1px solid #decf78; background:#fffbe6; color:#8a650d; font-weight:900; }
        .alert-chip { display:inline-block; border:1px solid #fecaca; border-radius:999px; padding:6px 10px; background:#fff1f2; color:#991b1b; margin:3px; font-size:13px; }
        .good-chip { display:inline-block; border:1px solid #bbf7d0; border-radius:999px; padding:6px 10px; background:#f0fdf4; color:#166534; margin:3px; font-size:13px; }
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
        ("Prioridades A/B+", str(int(metrics["priority_label"].isin(["A", "B+", "B"]).sum())) if not metrics.empty else "0", "warn"),
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
                prio[["display_name", "current_team", "primary_position", "primary_role", "priority_label", "priority_score", "observed_level", "potential_score", "fit_score", "confidence_score", "next_step_calc"]],
                use_container_width=True,
            )
        else:
            st.info("Todavía no hay jugadores. Empieza en ‘Añadir / puntuar jugador’.")
    with col2:
        st.markdown(
            """
            <div class="panel"><h3>Modelo de trabajo</h3>
            <p>La prioridad separa nivel observado, potencial, encaje, urgencia y confianza para evitar mezclar rendimiento con intuición.</p></div>
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
            c9, c10, c11 = st.columns(3)
            primary_role = c9.selectbox("Rol principal", ROLE_TYPES)
            tactical_fit = c10.selectbox("Encaje táctico", TACTICAL_FITS)
            position_need = c11.selectbox("Necesidad posicional", POSITION_NEED_LEVELS)
            secondary_role = st.selectbox("Rol secundario", ROLE_TYPES, key="new_player_secondary_role")
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
                        status=status, priority_manual=priority_manual, potential=potential, primary_role=primary_role,
                        secondary_role=secondary_role, tactical_fit=tactical_fit, position_need=position_need, source=source,
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
            v1, v2, v3, v4 = st.columns(4)
            viewing_type = v1.selectbox("Tipo de visionado", SOURCE_TYPES)
            opposition_level = v2.selectbox("Nivel rival", OPPOSITION_LEVELS)
            match_difficulty = v3.selectbox("Dificultad partido", MATCH_DIFFICULTIES)
            reliability = v4.selectbox("Fiabilidad", RELIABILITY_LEVELS)
            trend = st.selectbox("Tendencia", TREND_LEVELS, help="Sube/mantiene/baja respecto a observaciones previas.")
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
                    viewing_type=viewing_type, opposition_level=opposition_level, match_difficulty=match_difficulty,
                    reliability=reliability, trend=trend,
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
    hero("Jugadores", "Ficha individual con desglose del motor de ranking: nivel observado, potencial, encaje, confianza y prioridad final.", "Base", "Scoring")
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
    display_cols = [
        "player_id", "display_name", "current_team", "primary_position", "primary_role", "age",
        "priority_label", "priority_score", "observed_level", "potential_score", "fit_score",
        "confidence_score", "observations_count", "next_step_calc"
    ]
    st.dataframe(df[[c for c in display_cols if c in df.columns]].sort_values(["priority_score", "confidence_score"], ascending=False), use_container_width=True)

    st.subheader("Ficha individual")
    options = [""] + metrics["player_id"].tolist()
    labels = {"": "— Seleccionar —"}
    labels.update(dict(zip(metrics["player_id"], metrics["display_name"])))
    pid = st.selectbox("Jugador", options, format_func=lambda x: labels.get(x, x))
    if not pid:
        return
    player = metrics[metrics["player_id"] == pid].iloc[0]
    obs = observations_view[observations_view["player_id"] == pid]
    scoring = scoring_breakdown(player, obs)

    st.markdown(
        f"""
        <div class="panel">
          <div class="card-grid">
            <div class="mini-card"><div class="title">Jugador</div><div class="main">{safe(player['display_name'])}</div><div class="sub">{safe(player.get('primary_position',''))} · {safe(player.get('primary_role',''))}</div></div>
            <div class="mini-card"><div class="title">Prioridad final</div><div class="main"><span class="rank-badge">{safe(scoring['priority_label'])}</span> {safe(scoring['priority_score'])}/100</div><div class="sub">{safe(scoring['next_step'])}</div></div>
            <div class="mini-card"><div class="title">Evidencia</div><div class="main">{safe(scoring['evidence_level'])}</div><div class="sub">confianza {safe(scoring['confidence_score'])}/100 · {safe(player.get('observations_count', 0))} obs.</div></div>
            <div class="mini-card"><div class="title">Equipo</div><div class="main">{safe(player.get('current_team',''))}</div><div class="sub">{safe(player.get('nationality',''))} · edad {safe(player.get('age','—'))}</div></div>
            <div class="mini-card"><div class="title">Encaje</div><div class="main">{safe(player.get('tactical_fit','Sin valorar') or 'Sin valorar')}</div><div class="sub">necesidad: {safe(player.get('position_need',''))}</div></div>
            <div class="mini-card"><div class="title">Completitud</div><div class="main">{int(player['completion'])}%</div><div class="sub">datos, rol, fuente y observaciones</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    bars = "".join([
        score_bar("Nivel observado", scoring["observed_level"], "rendimiento ponderado por posición"),
        score_bar("Potencial", scoring["potential_score"], "edad, potencial manual, margen y etiquetas"),
        score_bar("Encaje", scoring["fit_score"], "rol, encaje táctico y necesidad posicional"),
        score_bar("Confianza", scoring["confidence_score"], "observaciones, minutos, fuente y completitud"),
        score_bar("Urgencia", scoring["urgency_score"], "estado de seguimiento y señales de mercado"),
        score_bar("Prioridad base", scoring["priority_base"], "sin modular por confianza"),
    ])
    st.markdown(f"<div class='panel'><h3>Desglose del ranking</h3>{bars}</div>", unsafe_allow_html=True)

    positives = scoring.get("signals", [])
    alerts = scoring.get("alerts", [])
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Señales positivas")
        if positives:
            st.markdown(" ".join([f"<span class='good-chip'>{safe(s)}</span>" for s in positives]), unsafe_allow_html=True)
        else:
            st.write("Sin señales positivas fuertes todavía.")
    with col2:
        st.markdown("### Alertas")
        if alerts:
            st.markdown(" ".join([f"<span class='alert-chip'>{safe(s)}</span>" for s in alerts]), unsafe_allow_html=True)
        else:
            st.write("Sin alertas relevantes.")

    st.write("**Notas generales:**", player.get("general_notes", ""))
    if not obs.empty:
        st.subheader("Observaciones acumuladas")
        obs_cols = ["created_at", "match", "observed_position", "role", "viewing_type", "minutes_observed", "global_rating", "reliability", "trend", "recommendation", "next_step", "positive_notes", "improvement_notes"]
        st.dataframe(obs[[c for c in obs_cols if c in obs.columns]], use_container_width=True)
        report = f"# Informe rápido - {player['display_name']}\n\n"
        report += f"Equipo: {player.get('current_team','')}\nPosición: {player.get('primary_position','')}\nRol: {player.get('primary_role','')}\n"
        report += f"Prioridad: {scoring['priority_label']} ({scoring['priority_score']}/100)\n"
        report += f"Nivel: {scoring['observed_level']} · Potencial: {scoring['potential_score']} · Encaje: {scoring['fit_score']} · Confianza: {scoring['confidence_score']}\n"
        report += f"Próximo paso: {scoring['next_step']}\nSeñales: {', '.join(positives)}\nAlertas: {', '.join(alerts)}\n\n"
        for _, r in obs.iterrows():
            report += f"## {r.get('match','Sin partido')} · {r.get('created_at','')}\n"
            report += f"Posición: {r.get('observed_position','')} · Rol: {r.get('role','')} · Nota: {r.get('global_rating','')} · Fiabilidad: {r.get('reliability','')}\n"
            report += f"Positivo: {r.get('positive_notes','')}\nMejora/dudas: {r.get('improvement_notes','')}\nPróximo paso: {r.get('next_step','')}\n\n"
        st.download_button("Descargar informe TXT", report.encode("utf-8"), file_name=f"informe_{normalize_text(player['display_name']).replace(' ','_')}.txt")
    else:
        st.info("Este jugador todavía no tiene observaciones.")



def page_rankings() -> None:
    hero("Rankings", "Motor de decisión separado por nivel, potencial, encaje, confianza y prioridad. El objetivo no es solo ordenar jugadores, sino decir qué toca hacer con cada uno.", "Scoring", "Decisión")
    teams_view, players_view, _, observations_view, competitions = enrich_tables()
    if players_view.empty:
        st.warning("No hay jugadores para rankear.")
        return
    metrics = player_metrics_table(players_view, observations_view)
    c1, c2, c3, c4 = st.columns(4)
    pos = c1.multiselect("Posición", POSITIONS)
    role = c2.multiselect("Rol", [r for r in ROLE_TYPES if r])
    label = c3.multiselect("Prioridad", PRIORITY_LABELS)
    min_conf = c4.slider("Confianza mínima", 0, 100, 0, 5)
    c5, c6, c7, c8 = st.columns(4)
    status = c5.multiselect("Estado", PLAYER_STATUS)
    country = c6.multiselect("Nacionalidad", sorted([x for x in metrics["nationality"].dropna().unique().tolist() if x])) if "nationality" in metrics.columns else []
    max_age = c7.slider("Edad máxima", 0, 45, 45)
    min_obs = c8.slider("Observaciones mínimas", 0, 5, 0)

    df = metrics.copy()
    if pos:
        df = df[df["primary_position"].isin(pos)]
    if role and "primary_role" in df.columns:
        df = df[df["primary_role"].isin(role)]
    if label:
        df = df[df["priority_label"].isin(label)]
    if status:
        df = df[df["status"].isin(status)]
    if country and "nationality" in df.columns:
        df = df[df["nationality"].isin(country)]
    if max_age < 45:
        ages = pd.to_numeric(df["age"], errors="coerce")
        df = df[(ages <= max_age) | ages.isna()]
    df = df[(pd.to_numeric(df["confidence_score"], errors="coerce").fillna(0) >= min_conf) & (pd.to_numeric(df["observations_count"], errors="coerce").fillna(0) >= min_obs)]

    if df.empty:
        st.info("No hay jugadores con esos filtros.")
        return

    base_cols = ["display_name", "current_team", "primary_position", "primary_role", "age", "priority_label", "priority_score", "observed_level", "potential_score", "fit_score", "confidence_score", "observations_count", "next_step_calc", "alerts_text"]
    tabs = st.tabs(["Prioridad", "Nivel observado", "Potencial", "Encaje", "Confianza", "2ª observación", "Alertas"])
    with tabs[0]:
        st.dataframe(df.sort_values(["priority_score", "confidence_score"], ascending=False)[[c for c in base_cols if c in df.columns]].head(150), use_container_width=True)
    with tabs[1]:
        st.caption("Ranking de rendimiento: lo que el jugador ha demostrado en observaciones, ponderado por posición.")
        st.dataframe(df.sort_values(["observed_level", "confidence_score"], ascending=False)[[c for c in base_cols if c in df.columns]].head(150), use_container_width=True)
    with tabs[2]:
        st.caption("Ranking de proyección: edad, potencial manual y señales de margen.")
        st.dataframe(df.sort_values(["potential_score", "confidence_score"], ascending=False)[[c for c in base_cols if c in df.columns]].head(150), use_container_width=True)
    with tabs[3]:
        st.caption("Ranking de encaje: rol, necesidad posicional y compatibilidad táctica.")
        st.dataframe(df.sort_values(["fit_score", "confidence_score"], ascending=False)[[c for c in base_cols if c in df.columns]].head(150), use_container_width=True)
    with tabs[4]:
        st.caption("Ranking de confianza: quién tiene datos suficientes para decidir.")
        st.dataframe(df.sort_values(["confidence_score", "observations_count"], ascending=False)[[c for c in base_cols if c in df.columns]].head(150), use_container_width=True)
    with tabs[5]:
        target = df[(pd.to_numeric(df["observed_level"], errors="coerce").fillna(0) >= 70) & (pd.to_numeric(df["confidence_score"], errors="coerce").fillna(0) < 65)]
        st.caption("Jugadores que han dado señal, pero todavía no tienen evidencia suficiente.")
        st.dataframe(target.sort_values(["observed_level", "priority_base"], ascending=False)[[c for c in base_cols if c in target.columns]].head(150), use_container_width=True)
    with tabs[6]:
        alert_df = df[df["alerts_text"].astype(str).str.len() > 0]
        st.caption("Alta nota con baja confianza, prioritarios sin evidencia, fichas incompletas, jugadores sin observaciones.")
        st.dataframe(alert_df.sort_values(["priority_score", "confidence_score"], ascending=[False, True])[[c for c in base_cols if c in alert_df.columns]].head(150), use_container_width=True)

    st.markdown("### Matriz de decisión")
    st.markdown(
        """
        <div class="panel"><div class="card-grid">
          <div class="mini-card"><div class="main">Nivel alto + confianza alta</div><div class="sub">Informe largo, decisión fuerte o prioridad A.</div></div>
          <div class="mini-card"><div class="main">Nivel alto + confianza baja</div><div class="sub">Segunda observación urgente, no venderlo como certeza.</div></div>
          <div class="mini-card"><div class="main">Nivel medio + confianza alta</div><div class="sub">Seguimiento normal, comparación por rol y posición.</div></div>
          <div class="mini-card"><div class="main">Nivel bajo + confianza alta</div><div class="sub">Descarte razonado o archivo frío.</div></div>
          <div class="mini-card"><div class="main">Potencial alto + sin muestra</div><div class="sub">Programar visionado completo antes de subirlo a A/B.</div></div>
          <div class="mini-card"><div class="main">Encaje alto + datos incompletos</div><div class="sub">Completar ficha y validar rol exacto.</div></div>
        </div></div>
        """,
        unsafe_allow_html=True,
    )


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
    hero("Campograma y comparador", "Vista posicional sin dependencias externas y comparación rápida por el nuevo motor de scoring.", "Visual", "Comparativa")
    _, players_view, _, observations_view, _ = enrich_tables()
    if players_view.empty:
        st.warning("No hay jugadores.")
        return
    metrics = player_metrics_table(players_view, observations_view)
    st.subheader("Campograma por posición principal")
    render_pitch(metrics)

    st.subheader("Comparador")
    options = metrics["player_id"].tolist()
    labels = dict(zip(metrics["player_id"], metrics["display_name"]))
    c1, c2 = st.columns(2)
    p1 = c1.selectbox("Jugador A", options, format_func=lambda x: labels.get(x, x), key="comp_a")
    p2 = c2.selectbox("Jugador B", options, format_func=lambda x: labels.get(x, x), key="comp_b")
    rows = []
    for pid in [p1, p2]:
        player = metrics[metrics["player_id"] == pid].iloc[0]
        rows.append({
            "Jugador": player["display_name"],
            "Equipo": player.get("current_team", ""),
            "Posición": player.get("primary_position", ""),
            "Rol": player.get("primary_role", ""),
            "Observaciones": player.get("observations_count", 0),
            "Nivel": player.get("observed_level", 0),
            "Potencial": player.get("potential_score", 0),
            "Encaje": player.get("fit_score", 0),
            "Confianza": player.get("confidence_score", 0),
            "Prioridad": f"{player.get('priority_label','')} · {player.get('priority_score','')}/100",
            "Próximo paso": player.get("next_step_calc", ""),
            "Alertas": player.get("alerts_text", ""),
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



def get_or_create_country(name: str) -> str:
    cid, _, _ = add_country(str(name or "").strip())
    return cid


def get_or_create_competition(name: str, country_id: str, level: str = "", season: str = "2025/26") -> str:
    cid, _, _ = add_competition(str(name or "").strip(), country_id, level, season)
    return cid


def get_or_create_team(name: str, team_type: str, country_id: str, competition_id: str = "", locality: str = "", locality_band: str = "") -> str:
    tid, created, _ = add_team(str(name or "").strip(), team_type, country_id, competition_id)
    if tid and (locality or locality_band):
        teams = load_table("teams")
        mask = teams["team_id"] == tid
        if locality:
            teams.loc[mask, "locality"] = locality
        if locality_band:
            teams.loc[mask, "locality_band"] = locality_band
        save_table("teams", teams)
    return tid


def import_teams_dataframe(raw: pd.DataFrame) -> Tuple[int, int]:
    created_or_seen = 0
    errors = 0
    for _, row in raw.fillna("").iterrows():
        try:
            country = str(row.get("country", "")).strip()
            competition = str(row.get("competition", "")).strip()
            team = str(row.get("team", "")).strip()
            team_type = str(row.get("team_type", "Club") or "Club").strip()
            if not country or not team:
                errors += 1
                continue
            country_id = get_or_create_country(country)
            competition_id = get_or_create_competition(competition, country_id, "", "2025/26") if competition else ""
            get_or_create_team(team, team_type, country_id, competition_id, str(row.get("locality", "")), str(row.get("locality_band", "")))
            created_or_seen += 1
        except Exception:
            errors += 1
    return created_or_seen, errors


def import_players_dataframe(raw: pd.DataFrame) -> Tuple[int, int, int]:
    created = 0
    skipped = 0
    errors = 0
    for _, row in raw.fillna("").iterrows():
        try:
            country = str(row.get("country", "")).strip()
            competition = str(row.get("competition", "")).strip()
            team = str(row.get("team", "")).strip()
            player_name = str(row.get("player_name", "")).strip()
            if not player_name or not team or not country:
                errors += 1
                continue
            country_id = get_or_create_country(country)
            competition_id = get_or_create_competition(competition, country_id, "", "2025/26") if competition else ""
            team_id = get_or_create_team(team, "Club", country_id, competition_id)
            nat_name = str(row.get("nationality", "")).strip() or country
            nationality_id = get_or_create_country(nat_name)
            _, was_created, _ = add_player(
                player_name,
                birth_date=str(row.get("birth_date", "")),
                age=str(row.get("age", "")),
                nationality_id=nationality_id,
                primary_position=str(row.get("primary_position", "")),
                secondary_position=str(row.get("secondary_position", "")),
                dominant_foot=str(row.get("dominant_foot", "")),
                height_cm=str(row.get("height_cm", "")),
                current_team_id=team_id,
                status=str(row.get("status", "Sin valorar") or "Sin valorar"),
                potential=str(row.get("potential", "")),
                primary_role=str(row.get("primary_role", "")),
                secondary_role=str(row.get("secondary_role", "")),
                tactical_fit=str(row.get("tactical_fit", "")),
                position_need=str(row.get("position_need", "")),
                tags=str(row.get("tags", "")),
                source=str(row.get("source", "Importación CSV") or "Importación CSV"),
            )
            created += int(was_created)
            skipped += int(not was_created)
        except Exception:
            errors += 1
    return created, skipped, errors


def import_matches_dataframe(raw: pd.DataFrame) -> Tuple[int, int, int]:
    created = 0
    skipped = 0
    errors = 0
    for _, row in raw.fillna("").iterrows():
        try:
            country = str(row.get("country", "")).strip()
            competition = str(row.get("competition", "")).strip()
            season = str(row.get("season", "2025/26") or "2025/26")
            match_date = str(row.get("match_date", "")).strip()
            home_team = str(row.get("home_team", "")).strip()
            away_team = str(row.get("away_team", "")).strip()
            if not country or not competition or not match_date or not home_team or not away_team:
                errors += 1
                continue
            country_id = get_or_create_country(country)
            competition_id = get_or_create_competition(competition, country_id, "", season)
            home_id = get_or_create_team(home_team, "Club", country_id, competition_id)
            away_id = get_or_create_team(away_team, "Club", country_id, competition_id)
            context_parts = []
            if str(row.get("matchday", "")).strip():
                context_parts.append(f"Jornada {row.get('matchday')}")
            if str(row.get("context", "")).strip():
                context_parts.append(str(row.get("context")))
            mid, was_created, _ = add_match(match_date, f"{home_team} - {away_team}", competition_id, home_id, away_id, season, " · ".join(context_parts))
            created += int(was_created)
            skipped += int(not was_created)
        except Exception:
            errors += 1
    return created, skipped, errors


def football_data_to_matches_df(fd_df: pd.DataFrame, source: dict) -> pd.DataFrame:
    rows = []
    for _, r in fd_df.fillna("").iterrows():
        if not str(r.get("HomeTeam", "")).strip() or not str(r.get("AwayTeam", "")).strip():
            continue
        raw_date = str(r.get("Date", "")).strip()
        parsed = pd.to_datetime(raw_date, dayfirst=True, errors="coerce")
        match_date = parsed.strftime("%Y-%m-%d") if not pd.isna(parsed) else raw_date
        result = ""
        if str(r.get("FTHG", "")).strip() != "" and str(r.get("FTAG", "")).strip() != "":
            result = f"Resultado: {r.get('FTHG')}-{r.get('FTAG')}"
        rows.append({
            "country": source["country"],
            "competition": source["competition"],
            "season": "2025/26",
            "match_date": match_date,
            "home_team": r.get("HomeTeam", ""),
            "away_team": r.get("AwayTeam", ""),
            "matchday": "",
            "context": f"Importado Football-Data.co.uk {source['code']}" + (f" · {result}" if result else ""),
        })
    return pd.DataFrame(rows, columns=EXPECTED_MATCH_COLUMNS)


def template_bytes(columns: List[str]) -> bytes:
    sample = pd.DataFrame([{col: "" for col in columns}])
    return sample.to_csv(index=False).encode("utf-8-sig")


def page_mass_importer() -> None:
    hero("Importador masivo", "Importa partidos, equipos y plantillas en bloque sin romper la base: valida, normaliza, evita duplicados y crea países/ligas/equipos si faltan.", "v0.6", "Masivo")
    st.warning("Para jugadores completos de todas las ligas, lo más fiable es cargar CSV de plantillas por fuente. La app evita duplicados por nombre normalizado, pero conviene revisar equipos y nacionalidades después.")
    tab1, tab2, tab3 = st.tabs(["Partidos Football-Data", "CSV universal", "Plantillas vacías"])

    with tab1:
        st.subheader("Importar partidos 2025/26 desde Football-Data.co.uk")
        st.caption("Cubre automáticamente las competiciones disponibles en Football-Data. Para terceras no cubiertas, usa CSV universal.")
        source_labels = [f"{s['country']} · {s['competition']} ({s['code']})" for s in FOOTBALL_DATA_SOURCES]
        selected = st.multiselect("Competiciones", source_labels, default=source_labels[:5])
        if st.button("Descargar e importar partidos seleccionados"):
            total_created = total_skipped = total_errors = 0
            logs = []
            for label, source in zip(source_labels, FOOTBALL_DATA_SOURCES):
                if label not in selected:
                    continue
                try:
                    fd_df = pd.read_csv(source["url"])
                    matches_df = football_data_to_matches_df(fd_df, source)
                    created, skipped, errors = import_matches_dataframe(matches_df)
                    total_created += created
                    total_skipped += skipped
                    total_errors += errors
                    logs.append({"fuente": label, "filas": len(matches_df), "creados": created, "ya_existían": skipped, "errores": errors})
                except Exception as exc:
                    total_errors += 1
                    logs.append({"fuente": label, "filas": 0, "creados": 0, "ya_existían": 0, "errores": str(exc)})
            st.success(f"Importación finalizada. Creados: {total_created}. Ya existían: {total_skipped}. Errores: {total_errors}.")
            if logs:
                st.dataframe(pd.DataFrame(logs), use_container_width=True)
            st.rerun()
        st.info("Si Streamlit Cloud no tuviera salida a internet temporalmente, descarga los CSV desde Football-Data y súbelos en la pestaña CSV universal ya transformados al formato de partidos.")

    with tab2:
        st.subheader("Importar CSV universal")
        import_type = st.radio("Tipo de importación", ["Jugadores", "Partidos", "Equipos"], horizontal=True)
        uploaded = st.file_uploader("Sube CSV", type=["csv"], key="mass_csv_upload")
        if uploaded is not None:
            raw = pd.read_csv(uploaded, dtype=str).fillna("")
            st.write("Vista previa")
            st.dataframe(raw.head(50), use_container_width=True)
            if st.button("Validar e importar CSV"):
                if import_type == "Jugadores":
                    created, skipped, errors = import_players_dataframe(raw)
                    st.success(f"Jugadores creados: {created}. Ya existentes/duplicados: {skipped}. Errores: {errors}.")
                elif import_type == "Partidos":
                    created, skipped, errors = import_matches_dataframe(raw)
                    st.success(f"Partidos creados: {created}. Ya existentes: {skipped}. Errores: {errors}.")
                else:
                    seen, errors = import_teams_dataframe(raw)
                    st.success(f"Equipos procesados: {seen}. Errores: {errors}.")
                st.rerun()
        st.caption("Columnas esperadas: usa las plantillas de la pestaña siguiente.")

    with tab3:
        st.subheader("Descargar plantillas de carga")
        c1, c2, c3 = st.columns(3)
        c1.download_button("Plantilla jugadores.csv", template_bytes(EXPECTED_PLAYER_COLUMNS), file_name="plantilla_jugadores_scouting_hub.csv")
        c2.download_button("Plantilla partidos.csv", template_bytes(EXPECTED_MATCH_COLUMNS), file_name="plantilla_partidos_scouting_hub.csv")
        c3.download_button("Plantilla equipos.csv", template_bytes(EXPECTED_TEAM_COLUMNS), file_name="plantilla_equipos_scouting_hub.csv")
        st.write("**Formato jugadores:**")
        st.code(",".join(EXPECTED_PLAYER_COLUMNS))
        st.write("**Formato partidos:**")
        st.code(",".join(EXPECTED_MATCH_COLUMNS))
        st.write("**Formato equipos:**")
        st.code(",".join(EXPECTED_TEAM_COLUMNS))


def page_coverage_control() -> None:
    hero("Cobertura de datos", "Mapa de huecos: equipos sin plantilla, jugadores sin observaciones, fichas incompletas y competiciones con pocos partidos cargados.", "QA", "Cobertura")
    teams_view, players_view, matches_view, observations_view, _ = enrich_tables()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Equipos", len(teams_view))
    c2.metric("Equipos sin jugadores", int((teams_view["team_id"].map(players_view.groupby("current_team_id").size()).fillna(0) == 0).sum()) if not teams_view.empty else 0)
    c3.metric("Jugadores sin observación", int((players_view["player_id"].map(observations_view.groupby("player_id").size()).fillna(0) == 0).sum()) if not players_view.empty else 0)
    c4.metric("Partidos cargados", len(matches_view))
    if not teams_view.empty:
        counts = players_view.groupby("current_team_id").size() if not players_view.empty else pd.Series(dtype=int)
        tv = teams_view.copy()
        tv["jugadores"] = tv["team_id"].map(counts).fillna(0).astype(int)
        st.subheader("Equipos con menos de 15 jugadores cargados")
        st.dataframe(tv[tv["jugadores"] < 15][["country", "competition", "name", "jugadores"]].sort_values(["country", "competition", "jugadores"]), use_container_width=True)
    if not players_view.empty:
        p = players_view.copy()
        p["observaciones"] = p["player_id"].map(observations_view.groupby("player_id").size() if not observations_view.empty else {}).fillna(0).astype(int)
        st.subheader("Jugadores sin observación")
        st.dataframe(p[p["observaciones"] == 0][["display_name", "current_team", "primary_position", "status", "source"]].head(300), use_container_width=True)

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
            "Rankings",
            "Investigación",
            "Duplicados",
            "Campograma / comparador",
            "Base editable",
            "Dataset inicial",
            "Importador masivo",
            "Cobertura de datos",
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
    elif page == "Rankings":
        page_rankings()
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
    elif page == "Importador masivo":
        page_mass_importer()
    elif page == "Cobertura de datos":
        page_coverage_control()
    elif page == "Backup / Importar / Exportar":
        page_backup()


if __name__ == "__main__":
    main()
