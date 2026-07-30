from __future__ import annotations

from typing import Dict, List, Tuple

APP_TITLE = "Scouting Hub v1.1"
APP_SUBTITLE = "Partido → nota → ranking, con la sencillez del Excel"

POSITIONS = ["POR", "LD", "DFC", "LI", "CAD", "CAI", "MCD", "MC", "MP", "ED", "EI", "SD", "DC"]
FOOTS = ["", "Derecha", "Izquierda", "Ambas"]
PLAYER_STATUS = ["Sin valorar", "En radar", "Seguir", "Revisar", "Prioritario", "Descartar", "Fichaje recomendado"]
MANUAL_PRIORITIES = ["", "A", "B+", "B", "C", "D"]
TEAM_TYPES = ["Club", "Selección"]
SOURCE_TYPES = ["", "Partido completo", "Directo", "Torneo", "Vídeo", "Base de datos", "Recomendación", "Entrenador", "Otro"]
VIEWING_TYPES = ["", "Partido completo", "Directo", "Vídeo completo", "Resumen", "Torneo", "Entrenamiento", "Otro"]
RELIABILITY_LEVELS = ["", "Alta", "Media", "Baja"]
TREND_LEVELS = ["", "Sube", "Mantiene", "Baja"]
OPPOSITION_LEVELS = ["", "Muy alto", "Alto", "Medio", "Bajo"]
MATCH_DIFFICULTIES = ["", "Muy alta", "Alta", "Media", "Baja"]
PRIORITY_LABELS = ["A", "B+", "B", "C", "D"]

SCHEMAS: Dict[str, List[str]] = {
    "countries": ["country_id", "name", "normalized_name", "created_at"],
    "competitions": ["competition_id", "name", "normalized_name", "country_id", "level", "season", "ranking_value", "created_at"],
    "teams": ["team_id", "name", "normalized_name", "team_type", "country_id", "competition_id", "created_at"],
    "players": [
        "player_id", "display_name", "normalized_name", "birth_date", "age", "nationality_id",
        "primary_position", "secondary_position", "dominant_foot", "height_cm", "current_team_id",
        "status", "manual_priority", "potential_rating", "primary_role", "secondary_role",
        "tactical_fit", "position_need", "source", "tags", "general_notes", "created_at", "updated_at",
    ],
    "matches": [
        "match_id", "match_date", "competition_id", "home_team_id", "away_team_id", "season",
        "context", "score_home", "score_away", "analyzed", "home_formation", "away_formation", "created_at",
    ],
    "observations": [
        "observation_id", "player_id", "match_id", "team_id", "observed_position", "role",
        "minutes_observed", "viewing_type", "opposition_level", "match_difficulty", "reliability",
        "trend", "technical_rating", "tactical_rating", "physical_rating", "mental_rating",
        "global_rating", "starter", "mvp", "positive_notes", "improvement_notes", "next_step", "created_at",
    ],
    "role_assessments": [
        "assessment_id", "player_id", "match_id", "role_name", "criterion_key", "criterion_label",
        "rating", "note", "created_at",
    ],
    "aliases": ["alias_id", "player_id", "alias", "normalized_alias", "created_at"],
    "lineups": ["lineup_id", "name", "formation", "notes", "created_at"],
    "lineup_slots": ["slot_id", "lineup_id", "slot_key", "slot_label", "player_id", "role_name", "x", "y"],
}

POSITION_WEIGHTS: Dict[str, Dict[str, float]] = {
    "POR": {"technical_rating": .18, "tactical_rating": .27, "physical_rating": .13, "mental_rating": .27, "global_rating": .15},
    "DFC": {"technical_rating": .15, "tactical_rating": .30, "physical_rating": .20, "mental_rating": .20, "global_rating": .15},
    "LD": {"technical_rating": .22, "tactical_rating": .25, "physical_rating": .23, "mental_rating": .15, "global_rating": .15},
    "LI": {"technical_rating": .22, "tactical_rating": .25, "physical_rating": .23, "mental_rating": .15, "global_rating": .15},
    "CAD": {"technical_rating": .24, "tactical_rating": .20, "physical_rating": .27, "mental_rating": .12, "global_rating": .17},
    "CAI": {"technical_rating": .24, "tactical_rating": .20, "physical_rating": .27, "mental_rating": .12, "global_rating": .17},
    "MCD": {"technical_rating": .20, "tactical_rating": .35, "physical_rating": .10, "mental_rating": .20, "global_rating": .15},
    "MC": {"technical_rating": .27, "tactical_rating": .28, "physical_rating": .10, "mental_rating": .20, "global_rating": .15},
    "MP": {"technical_rating": .31, "tactical_rating": .24, "physical_rating": .10, "mental_rating": .20, "global_rating": .15},
    "ED": {"technical_rating": .30, "tactical_rating": .18, "physical_rating": .25, "mental_rating": .12, "global_rating": .15},
    "EI": {"technical_rating": .30, "tactical_rating": .18, "physical_rating": .25, "mental_rating": .12, "global_rating": .15},
    "SD": {"technical_rating": .28, "tactical_rating": .23, "physical_rating": .14, "mental_rating": .20, "global_rating": .15},
    "DC": {"technical_rating": .25, "tactical_rating": .20, "physical_rating": .20, "mental_rating": .20, "global_rating": .15},
}

# criterion tuple: (key, label, weight, fallback macro)
ROLE_PROFILES: Dict[str, Dict[str, object]] = {
    "Portero clásico": {
        "positions": ["POR"],
        "criteria": [
            ("shot_stopping", "Paradas", .24, "technical_rating"),
            ("positioning", "Colocación", .20, "tactical_rating"),
            ("handling", "Blocaje", .16, "technical_rating"),
            ("aerial_control", "Dominio aéreo", .15, "physical_rating"),
            ("communication", "Mando", .13, "mental_rating"),
            ("composure", "Seguridad", .12, "mental_rating"),
        ],
    },
    "Portero líbero": {
        "positions": ["POR"],
        "criteria": [
            ("distribution", "Distribución", .22, "technical_rating"),
            ("sweeping", "Cobertura de espalda", .20, "tactical_rating"),
            ("decision_making", "Decisión", .18, "mental_rating"),
            ("positioning", "Posicionamiento", .15, "tactical_rating"),
            ("speed", "Velocidad", .13, "physical_rating"),
            ("shot_stopping", "Paradas", .12, "technical_rating"),
        ],
    },
    "Central dominante": {
        "positions": ["DFC"],
        "criteria": [
            ("aerial_duels", "Duelo aéreo", .23, "physical_rating"),
            ("ground_duels", "Duelo terrestre", .20, "physical_rating"),
            ("box_defending", "Defensa de área", .19, "tactical_rating"),
            ("aggression", "Agresividad útil", .14, "mental_rating"),
            ("positioning", "Colocación", .14, "tactical_rating"),
            ("passing_security", "Pase seguro", .10, "technical_rating"),
        ],
    },
    "Central corrector": {
        "positions": ["DFC"],
        "criteria": [
            ("covering", "Coberturas", .23, "tactical_rating"),
            ("speed", "Velocidad al espacio", .20, "physical_rating"),
            ("anticipation", "Anticipación", .19, "mental_rating"),
            ("one_v_one", "Defensa 1v1", .16, "tactical_rating"),
            ("positioning", "Colocación", .13, "tactical_rating"),
            ("passing_security", "Pase seguro", .09, "technical_rating"),
        ],
    },
    "Central de salida": {
        "positions": ["DFC"],
        "criteria": [
            ("progressive_passing", "Pase progresivo", .24, "technical_rating"),
            ("press_resistance", "Resistencia a presión", .18, "technical_rating"),
            ("carrying", "Conducción", .16, "technical_rating"),
            ("decision_making", "Decisión", .16, "mental_rating"),
            ("positioning", "Colocación", .14, "tactical_rating"),
            ("defensive_duels", "Duelos defensivos", .12, "physical_rating"),
        ],
    },
    "Lateral defensivo": {
        "positions": ["LD", "LI", "CAD", "CAI"],
        "criteria": [
            ("one_v_one", "Defensa 1v1", .24, "tactical_rating"),
            ("positioning", "Colocación", .19, "tactical_rating"),
            ("recovery", "Retorno", .17, "physical_rating"),
            ("duels", "Duelos", .16, "physical_rating"),
            ("passing_security", "Pase seguro", .13, "technical_rating"),
            ("concentration", "Concentración", .11, "mental_rating"),
        ],
    },
    "Lateral ofensivo": {
        "positions": ["LD", "LI", "CAD", "CAI"],
        "criteria": [
            ("overlapping", "Proyección", .20, "tactical_rating"),
            ("crossing", "Centro", .19, "technical_rating"),
            ("carrying", "Conducción", .17, "technical_rating"),
            ("speed", "Velocidad", .16, "physical_rating"),
            ("final_third", "Último tercio", .15, "technical_rating"),
            ("recovery", "Retorno", .13, "physical_rating"),
        ],
    },
    "Lateral interior": {
        "positions": ["LD", "LI", "CAD", "CAI"],
        "criteria": [
            ("inside_positioning", "Posicionamiento interior", .22, "tactical_rating"),
            ("press_resistance", "Resistencia a presión", .18, "technical_rating"),
            ("passing", "Pase", .18, "technical_rating"),
            ("scanning", "Escaneo", .16, "mental_rating"),
            ("counterpress", "Contrapresión", .14, "tactical_rating"),
            ("recovery", "Retorno", .12, "physical_rating"),
        ],
    },
    "Carrilero": {
        "positions": ["CAD", "CAI", "LD", "LI"],
        "criteria": [
            ("stamina", "Resistencia", .21, "physical_rating"),
            ("width", "Amplitud", .17, "tactical_rating"),
            ("crossing", "Centro", .17, "technical_rating"),
            ("speed", "Velocidad", .16, "physical_rating"),
            ("timing", "Timing de llegada", .16, "tactical_rating"),
            ("defensive_return", "Retorno defensivo", .13, "mental_rating"),
        ],
    },
    "Pivote defensivo": {
        "positions": ["MCD", "MC"],
        "criteria": [
            ("screening", "Protección central", .23, "tactical_rating"),
            ("positioning", "Colocación", .20, "tactical_rating"),
            ("interceptions", "Intercepciones", .18, "mental_rating"),
            ("duels", "Duelos", .15, "physical_rating"),
            ("passing_security", "Pase seguro", .13, "technical_rating"),
            ("discipline", "Disciplina", .11, "mental_rating"),
        ],
    },
    "Mediocentro organizador": {
        "positions": ["MCD", "MC"],
        "criteria": [
            ("progressive_passing", "Pase progresivo", .22, "technical_rating"),
            ("orientation", "Orientación corporal", .18, "technical_rating"),
            ("scanning", "Escaneo", .17, "mental_rating"),
            ("tempo", "Control del ritmo", .17, "tactical_rating"),
            ("press_resistance", "Resistencia a presión", .15, "technical_rating"),
            ("defensive_positioning", "Posición defensiva", .11, "tactical_rating"),
        ],
    },
    "Box to box": {
        "positions": ["MC", "MP", "MCD"],
        "criteria": [
            ("stamina", "Resistencia", .20, "physical_rating"),
            ("arrivals", "Llegada", .18, "tactical_rating"),
            ("ball_carrying", "Conducción", .17, "technical_rating"),
            ("counterpress", "Contrapresión", .16, "tactical_rating"),
            ("duels", "Duelos", .15, "physical_rating"),
            ("decision_making", "Decisión", .14, "mental_rating"),
        ],
    },
    "Interior / mediapunta": {
        "positions": ["MC", "MP", "SD"],
        "criteria": [
            ("between_lines", "Entre líneas", .22, "tactical_rating"),
            ("final_pass", "Último pase", .20, "technical_rating"),
            ("turning", "Giro y recepción", .17, "technical_rating"),
            ("creativity", "Creatividad", .16, "mental_rating"),
            ("arrivals", "Llegada", .14, "tactical_rating"),
            ("counterpress", "Contrapresión", .11, "physical_rating"),
        ],
    },
    "Extremo abierto": {
        "positions": ["ED", "EI", "MP"],
        "criteria": [
            ("one_v_one", "Desborde 1v1", .24, "technical_rating"),
            ("acceleration", "Aceleración", .18, "physical_rating"),
            ("crossing", "Centro", .17, "technical_rating"),
            ("width", "Fijación en amplitud", .15, "tactical_rating"),
            ("final_action", "Última acción", .15, "mental_rating"),
            ("defensive_work", "Trabajo defensivo", .11, "tactical_rating"),
        ],
    },
    "Extremo interior": {
        "positions": ["ED", "EI", "SD", "MP"],
        "criteria": [
            ("inside_carrying", "Conducción interior", .22, "technical_rating"),
            ("finishing", "Finalización", .19, "technical_rating"),
            ("combination", "Combinación", .17, "technical_rating"),
            ("off_ball", "Desmarque", .16, "tactical_rating"),
            ("acceleration", "Aceleración", .14, "physical_rating"),
            ("counterpress", "Contrapresión", .12, "mental_rating"),
        ],
    },
    "Delantero móvil": {
        "positions": ["DC", "SD", "ED", "EI"],
        "criteria": [
            ("mobility", "Movilidad", .21, "tactical_rating"),
            ("runs", "Rupturas", .19, "physical_rating"),
            ("link_play", "Apoyo y asociación", .17, "technical_rating"),
            ("finishing", "Finalización", .17, "technical_rating"),
            ("pressing", "Presión", .14, "mental_rating"),
            ("decision_making", "Decisión", .12, "mental_rating"),
        ],
    },
    "Delantero referencia": {
        "positions": ["DC"],
        "criteria": [
            ("hold_up", "Juego de espaldas", .22, "technical_rating"),
            ("aerial_duels", "Duelo aéreo", .20, "physical_rating"),
            ("box_presence", "Presencia en área", .18, "tactical_rating"),
            ("finishing", "Finalización", .17, "technical_rating"),
            ("strength", "Fuerza", .13, "physical_rating"),
            ("link_play", "Descarga", .10, "mental_rating"),
        ],
    },
    "Delantero presionante": {
        "positions": ["DC", "SD"],
        "criteria": [
            ("pressing", "Presión", .23, "tactical_rating"),
            ("work_rate", "Ritmo de trabajo", .19, "mental_rating"),
            ("speed", "Velocidad", .16, "physical_rating"),
            ("runs", "Rupturas", .15, "tactical_rating"),
            ("finishing", "Finalización", .15, "technical_rating"),
            ("link_play", "Asociación", .12, "technical_rating"),
        ],
    },
}

ROLE_NAMES = list(ROLE_PROFILES.keys())

DEFAULT_SCORING_WEIGHTS = {
    # El rendimiento observado es el núcleo, como en la BBDD Excel original.
    "heritage": 0.60,
    "role_fit": 0.15,
    "potential": 0.10,
    "need": 0.10,
    "trend": 0.05,
}

FORMATION_TEMPLATES: Dict[str, List[Tuple[str, str, int, int]]] = {
    "4-3-3": [
        ("GK", "Portero", 7, 50), ("RB", "Lateral D", 25, 85), ("RCB", "Central D", 22, 62),
        ("LCB", "Central I", 22, 38), ("LB", "Lateral I", 25, 15), ("DM", "Pivote", 43, 50),
        ("RCM", "Interior D", 58, 68), ("LCM", "Interior I", 58, 32), ("RW", "Extremo D", 78, 83),
        ("LW", "Extremo I", 78, 17), ("ST", "Delantero", 91, 50),
    ],
    "4-2-3-1": [
        ("GK", "Portero", 7, 50), ("RB", "Lateral D", 25, 85), ("RCB", "Central D", 22, 62),
        ("LCB", "Central I", 22, 38), ("LB", "Lateral I", 25, 15), ("RDM", "Pivote D", 45, 62),
        ("LDM", "Pivote I", 45, 38), ("RW", "Extremo D", 70, 83), ("AM", "Mediapunta", 70, 50),
        ("LW", "Extremo I", 70, 17), ("ST", "Delantero", 90, 50),
    ],
    "3-4-3": [
        ("GK", "Portero", 7, 50), ("RCB", "Central D", 22, 70), ("CB", "Central", 20, 50),
        ("LCB", "Central I", 22, 30), ("RWB", "Carrilero D", 48, 88), ("RCM", "Medio D", 50, 62),
        ("LCM", "Medio I", 50, 38), ("LWB", "Carrilero I", 48, 12), ("RW", "Extremo D", 78, 78),
        ("LW", "Extremo I", 78, 22), ("ST", "Delantero", 91, 50),
    ],
    "5-4-1": [
        ("GK", "Portero", 7, 50), ("RWB", "Carrilero D", 30, 88), ("RCB", "Central D", 22, 68),
        ("CB", "Central", 20, 50), ("LCB", "Central I", 22, 32), ("LWB", "Carrilero I", 30, 12),
        ("RM", "Banda D", 57, 82), ("RCM", "Medio D", 52, 60), ("LCM", "Medio I", 52, 40),
        ("LM", "Banda I", 57, 18), ("ST", "Delantero", 89, 50),
    ],
}


FORMATION_SLOT_POSITIONS = {
    "GK": "POR", "RB": "LD", "RCB": "DFC", "CB": "DFC", "LCB": "DFC", "LB": "LI",
    "RWB": "CAD", "LWB": "CAI", "DM": "MCD", "RDM": "MCD", "LDM": "MCD",
    "RCM": "MC", "LCM": "MC", "RM": "ED", "LM": "EI", "AM": "MP",
    "RW": "ED", "LW": "EI", "ST": "DC",
}
