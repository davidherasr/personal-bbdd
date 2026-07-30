from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scouting_hub.config import SCHEMAS
from scouting_hub.scoring import scoring_breakdown


def main() -> None:
    errors = []
    for table, columns in SCHEMAS.items():
        path = ROOT / "data" / f"{table}.csv"
        if not path.exists():
            errors.append(f"Falta {path}")
            continue
        df = pd.read_csv(path, dtype=str)
        if list(df.columns) != columns:
            errors.append(f"Cabeceras incorrectas en {table}")
        if len(df) != 0:
            errors.append(f"{table}.csv no está vacío")
    player = pd.Series({
        "player_id": "demo", "display_name": "Demo", "primary_position": "MC",
        "primary_role": "Mediocentro organizador", "potential_rating": "8",
        "tactical_fit": "7", "position_need": "6", "age": "21",
        "nationality_id": "x", "dominant_foot": "Derecha", "height_cm": "180",
        "current_team_id": "t", "status": "Seguir", "source": "Directo",
        "general_notes": "demo",
    })
    obs = pd.DataFrame([{col: "" for col in SCHEMAS["observations"]}])
    obs.loc[0, [
        "player_id", "minutes_observed", "viewing_type", "opposition_level",
        "match_difficulty", "reliability", "trend", "technical_rating",
        "tactical_rating", "physical_rating", "mental_rating", "global_rating",
    ]] = ["demo", "90", "Partido completo", "Alto", "Alta", "Alta", "Sube", "8", "8", "7", "8", "8"]
    score = scoring_breakdown(player, obs, pd.DataFrame(columns=SCHEMAS["role_assessments"]))
    if not 0 <= float(score["decision_score"]) <= 100:
        errors.append("El scoring devuelve un valor fuera de rango")
    if errors:
        print("VALIDACIÓN FALLIDA")
        for error in errors:
            print("-", error)
        raise SystemExit(1)
    print("Proyecto válido: CSV vacíos, esquemas correctos y scoring operativo.")


if __name__ == "__main__":
    main()
