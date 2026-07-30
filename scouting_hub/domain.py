from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List, Tuple

import pandas as pd

from .storage import append_row, load_table, normalize_text, now_str, save_table, update_row


def get_name(df: pd.DataFrame, id_col: str, value: str, name_col: str = "name") -> str:
    if not value or df.empty:
        return ""
    rows = df[df[id_col].astype(str) == str(value)]
    return str(rows.iloc[0].get(name_col, "")) if not rows.empty else ""


def add_country(name: str) -> Tuple[str, bool, str]:
    name = str(name).strip()
    if not name:
        return "", False, "Escribe el país."
    countries = load_table("countries")
    norm = normalize_text(name)
    existing = countries[countries["normalized_name"].astype(str) == norm]
    if not existing.empty:
        return str(existing.iloc[0]["country_id"]), False, f"Ya existe como {existing.iloc[0]['name']}."
    cid = append_row("countries", {"name": name, "normalized_name": norm})
    return cid, True, "País añadido."


def add_competition(name: str, country_id: str, level: str = "", season: str = "", ranking_value: object = "") -> Tuple[str, bool, str]:
    name = str(name).strip()
    if not name or not country_id:
        return "", False, "Falta país o competición."
    competitions = load_table("competitions")
    norm = normalize_text(name)
    existing = competitions[(competitions["country_id"].astype(str) == str(country_id)) & (competitions["normalized_name"].astype(str) == norm)]
    if not existing.empty:
        return str(existing.iloc[0]["competition_id"]), False, f"Ya existe como {existing.iloc[0]['name']}."
    cid = append_row("competitions", {"name": name, "normalized_name": norm, "country_id": country_id, "level": level, "season": season, "ranking_value": ranking_value})
    return cid, True, "Competición añadida."


def add_team(name: str, team_type: str, country_id: str, competition_id: str = "") -> Tuple[str, bool, str]:
    name = str(name).strip()
    if not name or not country_id:
        return "", False, "Falta país o equipo."
    teams = load_table("teams")
    norm = normalize_text(name)
    existing = teams[
        (teams["country_id"].astype(str) == str(country_id)) &
        (teams["team_type"].astype(str) == str(team_type)) &
        (teams["normalized_name"].astype(str) == norm)
    ]
    if not existing.empty:
        return str(existing.iloc[0]["team_id"]), False, f"Ya existe como {existing.iloc[0]['name']}."
    tid = append_row("teams", {"name": name, "normalized_name": norm, "team_type": team_type, "country_id": country_id, "competition_id": competition_id if team_type == "Club" else ""})
    return tid, True, "Equipo/selección añadido."


def duplicate_candidates(name: str, limit: int = 7) -> pd.DataFrame:
    players = load_table("players")
    aliases = load_table("aliases")
    norm = normalize_text(name)
    if not norm or players.empty:
        return pd.DataFrame(columns=["player_id", "display_name", "similarity", "reason"])
    rows: List[Dict[str, object]] = []
    alias_map = dict(zip(aliases["normalized_alias"].astype(str), aliases["player_id"].astype(str))) if not aliases.empty else {}
    for _, row in players.iterrows():
        player_norm = str(row.get("normalized_name", ""))
        ratio = SequenceMatcher(None, norm, player_norm).ratio()
        reason = "nombre parecido"
        if player_norm == norm:
            ratio = 1.0
            reason = "coincidencia normalizada"
        rows.append({"player_id": row.get("player_id", ""), "display_name": row.get("display_name", ""), "similarity": round(ratio * 100, 1), "reason": reason})
    if norm in alias_map:
        pid = alias_map[norm]
        match = players[players["player_id"].astype(str) == pid]
        if not match.empty:
            rows.append({"player_id": pid, "display_name": match.iloc[0].get("display_name", ""), "similarity": 100.0, "reason": "alias exacto"})
    result = pd.DataFrame(rows).sort_values("similarity", ascending=False).drop_duplicates("player_id")
    return result[result["similarity"] >= 72].head(limit)


def add_player(display_name: str, **kwargs: object) -> Tuple[str, bool, str]:
    display_name = str(display_name).strip()
    if not display_name:
        return "", False, "Escribe el nombre."
    norm = normalize_text(display_name)
    players = load_table("players")
    exact = players[players["normalized_name"].astype(str) == norm]
    if not exact.empty:
        return str(exact.iloc[0]["player_id"]), False, f"Ya existe como {exact.iloc[0]['display_name']}."
    row = {
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
        "manual_priority": kwargs.get("manual_priority", ""),
        "potential_rating": kwargs.get("potential_rating", ""),
        "primary_role": kwargs.get("primary_role", ""),
        "secondary_role": kwargs.get("secondary_role", ""),
        "tactical_fit": kwargs.get("tactical_fit", ""),
        "position_need": kwargs.get("position_need", ""),
        "source": kwargs.get("source", ""),
        "tags": kwargs.get("tags", ""),
        "general_notes": kwargs.get("general_notes", ""),
        "updated_at": now_str(),
    }
    pid = append_row("players", row)
    return pid, True, "Jugador añadido."


def add_match(**kwargs: object) -> Tuple[str, bool, str]:
    matches = load_table("matches")
    date = str(kwargs.get("match_date", ""))
    home = str(kwargs.get("home_team_id", ""))
    away = str(kwargs.get("away_team_id", ""))
    duplicate = matches[
        (matches["match_date"].astype(str) == date) &
        (matches["home_team_id"].astype(str) == home) &
        (matches["away_team_id"].astype(str) == away)
    ]
    if not duplicate.empty:
        return str(duplicate.iloc[0]["match_id"]), False, "Ese partido ya existe."
    mid = append_row("matches", kwargs)
    return mid, True, "Partido añadido."


def add_observation(**kwargs: object) -> Tuple[str, bool, str]:
    if not kwargs.get("player_id"):
        return "", False, "Selecciona un jugador."
    oid = append_row("observations", kwargs)
    return oid, True, "Observación guardada."




def save_match_observation(**kwargs: object) -> Tuple[str, bool, str]:
    """Create or update the observation for one player in one match.

    The match desk is designed for repeated edits while watching a game. Using
    an upsert prevents duplicate rows each time the user corrects a rating.
    """
    player_id = str(kwargs.get("player_id", ""))
    match_id = str(kwargs.get("match_id", ""))
    team_id = str(kwargs.get("team_id", ""))
    if not player_id or not match_id:
        return "", False, "Falta jugador o partido."
    observations = load_table("observations")
    mask = (
        (observations["player_id"].astype(str) == player_id)
        & (observations["match_id"].astype(str) == match_id)
        & (observations["team_id"].astype(str) == team_id)
    )
    existing = observations[mask]
    if not existing.empty:
        observation_id = str(existing.iloc[0]["observation_id"])
        update_row("observations", observation_id, kwargs)
        return observation_id, False, "Observación actualizada."
    observation_id = append_row("observations", kwargs)
    return observation_id, True, "Observación creada."


def save_role_assessment(player_id: str, match_id: str, role_name: str, values: Dict[str, Tuple[str, object, str]]) -> int:
    assessments = load_table("role_assessments")
    # Reemplaza la evaluación del mismo jugador/partido/rol para evitar duplicar cada edición.
    mask = ~(
        (assessments["player_id"].astype(str) == str(player_id)) &
        (assessments["match_id"].astype(str) == str(match_id)) &
        (assessments["role_name"].astype(str) == str(role_name))
    )
    assessments = assessments[mask].copy()
    from .storage import new_id
    for key, (label, rating, note) in values.items():
        if str(rating).strip() in {"", "0", "0.0"}:
            continue
        row = {
            "assessment_id": new_id("ras"), "player_id": player_id, "match_id": match_id,
            "role_name": role_name, "criterion_key": key, "criterion_label": label,
            "rating": rating, "note": note, "created_at": now_str(),
        }
        assessments.loc[len(assessments)] = [row.get(col, "") for col in assessments.columns]
    save_table("role_assessments", assessments)
    return len(values)


def enrich_data() -> Dict[str, pd.DataFrame]:
    countries = load_table("countries")
    competitions = load_table("competitions")
    teams = load_table("teams")
    players = load_table("players")
    matches = load_table("matches")
    observations = load_table("observations")
    role_assessments = load_table("role_assessments")

    country_map = dict(zip(countries["country_id"], countries["name"]))
    competition_map = dict(zip(competitions["competition_id"], competitions["name"]))
    team_map = dict(zip(teams["team_id"], teams["name"]))
    player_map = dict(zip(players["player_id"], players["display_name"]))

    competitions_view = competitions.copy()
    competitions_view["country"] = competitions_view["country_id"].map(country_map).fillna("")
    teams_view = teams.copy()
    teams_view["country"] = teams_view["country_id"].map(country_map).fillna("")
    teams_view["competition"] = teams_view["competition_id"].map(competition_map).fillna("")
    players_view = players.copy()
    players_view["nationality"] = players_view["nationality_id"].map(country_map).fillna("")
    players_view["current_team"] = players_view["current_team_id"].map(team_map).fillna("")
    team_competition_map = dict(zip(teams_view["team_id"], teams_view["competition"])) if not teams_view.empty else {}
    team_country_map = dict(zip(teams_view["team_id"], teams_view["country"])) if not teams_view.empty else {}
    players_view["competition"] = players_view["current_team_id"].map(team_competition_map).fillna("")
    players_view["team_country"] = players_view["current_team_id"].map(team_country_map).fillna("")
    matches_view = matches.copy()
    matches_view["competition"] = matches_view["competition_id"].map(competition_map).fillna("")
    matches_view["home_team"] = matches_view["home_team_id"].map(team_map).fillna("")
    matches_view["away_team"] = matches_view["away_team_id"].map(team_map).fillna("")
    matches_view["match_name"] = matches_view.apply(lambda r: f"{r.get('home_team','')} - {r.get('away_team','')}", axis=1)
    observations_view = observations.copy()
    observations_view["player"] = observations_view["player_id"].map(player_map).fillna("")
    observations_view["team"] = observations_view["team_id"].map(team_map).fillna("")
    match_map = dict(zip(matches_view["match_id"], matches_view["match_name"]))
    observations_view["match"] = observations_view["match_id"].map(match_map).fillna("")
    match_competition_map = dict(zip(matches["match_id"], matches["competition_id"]))
    competition_value_map = dict(zip(competitions["competition_id"], competitions.get("ranking_value", pd.Series(dtype=str))))
    observations_view["competition_id"] = observations_view["match_id"].map(match_competition_map).fillna("")
    observations_view["competition_value"] = observations_view["competition_id"].map(competition_value_map).fillna("")
    return {
        "countries": countries, "competitions": competitions_view, "teams": teams_view,
        "players": players_view, "matches": matches_view, "observations": observations_view,
        "role_assessments": role_assessments,
    }





def delete_match_cascade(match_id: str) -> int:
    """Delete a match and dependent observations/role assessments."""
    from .storage import delete_rows
    deleted = delete_rows("matches", [match_id])
    if not deleted:
        return 0
    for table in ["observations", "role_assessments"]:
        df = load_table(table)
        if "match_id" in df.columns:
            save_table(table, df[df["match_id"].astype(str) != str(match_id)].copy())
    return deleted

def delete_player_cascade(player_id: str) -> int:
    """Delete a player and all dependent records."""
    from .storage import delete_rows
    deleted = delete_rows("players", [player_id])
    if not deleted:
        return 0
    for table in ["observations", "role_assessments", "aliases", "lineup_slots"]:
        df = load_table(table)
        if "player_id" in df.columns:
            save_table(table, df[df["player_id"].astype(str) != str(player_id)].copy())
    return deleted


def merge_players(keep_id: str, merge_id: str) -> None:
    if not keep_id or not merge_id or keep_id == merge_id:
        return
    players = load_table("players")
    merge_rows = players[players["player_id"].astype(str) == merge_id]
    if merge_rows.empty:
        return
    merge_name = str(merge_rows.iloc[0].get("display_name", ""))
    observations = load_table("observations")
    observations.loc[observations["player_id"].astype(str) == merge_id, "player_id"] = keep_id
    save_table("observations", observations)
    assessments = load_table("role_assessments")
    assessments.loc[assessments["player_id"].astype(str) == merge_id, "player_id"] = keep_id
    save_table("role_assessments", assessments)
    aliases = load_table("aliases")
    from .storage import new_id
    aliases.loc[len(aliases)] = [new_id("als"), keep_id, merge_name, normalize_text(merge_name), now_str()]
    save_table("aliases", aliases)
    players = players[players["player_id"].astype(str) != merge_id].copy()
    save_table("players", players)
