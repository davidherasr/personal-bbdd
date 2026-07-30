from __future__ import annotations

import io
from typing import Mapping

import pandas as pd

from .config import DEFAULT_SCORING_WEIGHTS, SCHEMAS
from .domain import enrich_data
from .scoring import metrics_table
from .storage import get_settings, load_table, normalize_text


def _weights() -> Mapping[str, float]:
    settings = get_settings()
    saved = settings.get("scoring_weights", DEFAULT_SCORING_WEIGHTS)
    return saved if isinstance(saved, dict) else DEFAULT_SCORING_WEIGHTS


def model_tables() -> dict[str, pd.DataFrame]:
    """Return the four logical tables from the user's original workbook."""
    data = enrich_data()
    players = data["players"]
    teams = data["teams"]
    matches = data["matches"]
    observations = data["observations"]
    assessments = data["role_assessments"]
    metrics = metrics_table(players, observations, assessments, _weights()) if not players.empty else pd.DataFrame()

    if observations.empty:
        facts = pd.DataFrame(columns=["Jugador", "Minutos", "Fecha", "Partido", "Nota", "MVP"])
    else:
        facts = observations.copy()
        match_date_map = dict(zip(matches["match_id"], matches["match_date"])) if not matches.empty else {}
        facts["Fecha"] = facts["match_id"].map(match_date_map).fillna("")
        facts["MVP"] = facts["mvp"].map(lambda value: 1 if normalize_text(value) in {"si", "true", "1", "yes", "mvp"} else 0)
        facts = facts.rename(columns={"player": "Jugador", "minutes_observed": "Minutos", "match": "Partido", "global_rating": "Nota"})
        facts = facts[["Jugador", "Minutos", "Fecha", "Partido", "Nota", "MVP"]]

    if metrics.empty:
        players_dim = pd.DataFrame(columns=["Jugador", "Equipo", "Posicion", "Edad", "PartidosV", "MinutosTotal", "NotaMedia", "MVPtot", "Valoracion", "NotaAcum", "MinutosPart", "Score100", "RankOriginal"])
        history = pd.DataFrame(columns=["Orden", "Jugador", "Equipo", "Posición", "RANK", "Confianza", "Prioridad"])
    else:
        cols = ["display_name", "current_team", "primary_position", "age", "matches_seen", "total_minutes", "average_rating", "mvp_count", "competition_value", "rating_sum", "avg_minutes", "heritage_score", "legacy_raw"]
        players_dim = metrics[[c for c in cols if c in metrics.columns]].rename(columns={
            "display_name": "Jugador", "current_team": "Equipo", "primary_position": "Posicion", "age": "Edad",
            "matches_seen": "PartidosV", "total_minutes": "MinutosTotal", "average_rating": "NotaMedia",
            "mvp_count": "MVPtot", "competition_value": "Valoracion", "rating_sum": "NotaAcum",
            "avg_minutes": "MinutosPart", "heritage_score": "Score100", "legacy_raw": "RankOriginal",
        }).sort_values("Score100", ascending=False)
        history = metrics.sort_values("heritage_score", ascending=False).copy()
        history["Orden"] = range(1, len(history) + 1)
        history = history.rename(columns={"display_name": "Jugador", "current_team": "Equipo", "primary_position": "Posición", "heritage_score": "RANK", "confidence": "Confianza", "priority_label": "Prioridad"})
        history = history[["Orden", "Jugador", "Equipo", "Posición", "RANK", "Confianza", "Prioridad"]]

    if teams.empty:
        teams_dim = pd.DataFrame(columns=["Equipo", "Liga", "Pais", "Jugadores", "Jugadores observados", "Partidos"])
    else:
        teams_dim = teams[["team_id", "name", "competition", "country"]].copy()
        player_counts = players.groupby("current_team_id").size().rename("Jugadores").reset_index() if not players.empty else pd.DataFrame(columns=["current_team_id", "Jugadores"])
        observed_counts = observations.groupby("team_id")["player_id"].nunique().rename("Jugadores observados").reset_index() if not observations.empty else pd.DataFrame(columns=["team_id", "Jugadores observados"])
        if matches.empty:
            match_counts = pd.DataFrame(columns=["team_id", "Partidos"])
        else:
            match_counts = pd.concat([
                matches[["match_id", "home_team_id"]].rename(columns={"home_team_id": "team_id"}),
                matches[["match_id", "away_team_id"]].rename(columns={"away_team_id": "team_id"}),
            ]).groupby("team_id")["match_id"].nunique().rename("Partidos").reset_index()
        teams_dim = teams_dim.merge(player_counts, left_on="team_id", right_on="current_team_id", how="left")
        teams_dim = teams_dim.merge(observed_counts, on="team_id", how="left")
        teams_dim = teams_dim.merge(match_counts, on="team_id", how="left")
        teams_dim = teams_dim.rename(columns={"name": "Equipo", "competition": "Liga", "country": "Pais"})
        teams_dim = teams_dim[["Equipo", "Liga", "Pais", "Jugadores", "Jugadores observados", "Partidos"]].fillna(0)

    return {
        "Hechos_Stats": facts,
        "Dim_Jugadores": players_dim,
        "Dim_Equipos": teams_dim,
        "His_Rank": history,
    }


def excel_model_bytes(include_raw: bool = True) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        workbook = writer.book
        header = workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#17324D", "border": 0, "align": "center"})
        decimal = workbook.add_format({"num_format": "0.00"})
        integer = workbook.add_format({"num_format": "0"})
        date_fmt = workbook.add_format({"num_format": "yyyy-mm-dd"})
        for sheet_name, df in model_tables().items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            sheet = writer.sheets[sheet_name]
            sheet.freeze_panes(1, 0)
            sheet.autofilter(0, 0, max(len(df), 1), max(len(df.columns) - 1, 0))
            for col_index, column in enumerate(df.columns):
                sheet.write(0, col_index, column, header)
                values = df[column].astype(str) if len(df) else pd.Series(dtype=str)
                width = min(max(len(str(column)) + 2, int(values.str.len().quantile(.9)) + 2 if len(values) else 12), 36)
                fmt = None
                if column in {"Nota", "NotaMedia", "Valoracion", "MinutosPart", "Score100", "RANK", "Confianza"}:
                    fmt = decimal
                elif column in {"Minutos", "MVP", "Edad", "PartidosV", "MinutosTotal", "MVPtot", "NotaAcum", "Orden", "Jugadores", "Jugadores observados", "Partidos"}:
                    fmt = integer
                elif column == "Fecha":
                    fmt = date_fmt
                sheet.set_column(col_index, col_index, width, fmt)
            if sheet_name in {"Dim_Jugadores", "His_Rank"} and len(df):
                score_col = df.columns.get_loc("Score100") if "Score100" in df.columns else df.columns.get_loc("RANK")
                sheet.conditional_format(1, score_col, len(df), score_col, {"type": "3_color_scale", "min_color": "#FEE2E2", "mid_color": "#FEF3C7", "max_color": "#DCFCE7"})
        if include_raw:
            for table in SCHEMAS:
                sheet_name = f"raw_{table}"[:31]
                df = load_table(table)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                sheet = writer.sheets[sheet_name]
                sheet.freeze_panes(1, 0)
                for col_index, column in enumerate(df.columns):
                    sheet.write(0, col_index, column, header)
                    sheet.set_column(col_index, col_index, min(max(len(column) + 2, 14), 28))
    return buffer.getvalue()
