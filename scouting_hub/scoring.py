from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

from .config import DEFAULT_SCORING_WEIGHTS, POSITION_WEIGHTS, ROLE_PROFILES
from .storage import normalize_text

RATING_COLUMNS = ["technical_rating", "tactical_rating", "physical_rating", "mental_rating", "global_rating"]

RELIABILITY_FACTOR = {"Alta": 1.00, "Media": 0.82, "Baja": 0.64, "": 0.72}
VIEWING_FACTOR = {
    "Partido completo": 1.00, "Directo": 1.04, "Vídeo completo": 0.96, "Resumen": 0.62,
    "Torneo": 0.92, "Entrenamiento": 0.84, "Otro": 0.72, "": 0.72,
}
OPPOSITION_FACTOR = {"Muy alto": 1.08, "Alto": 1.04, "Medio": 1.00, "Bajo": 0.94, "": 1.00}
DIFFICULTY_FACTOR = {"Muy alta": 1.06, "Alta": 1.03, "Media": 1.00, "Baja": 0.96, "": 1.00}
TREND_SCORE = {"Sube": 72.0, "Mantiene": 50.0, "Baja": 28.0, "": 50.0}


def num(value: object, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None or str(value).strip() == "":
            return default
        result = float(value)
        if math.isnan(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def observation_weight(row: pd.Series) -> float:
    minutes = num(row.get("minutes_observed"), 0.0) or 0.0
    minutes_factor = 0.30 + 0.70 * min(max(minutes, 0.0), 90.0) / 90.0
    reliability = RELIABILITY_FACTOR.get(str(row.get("reliability", "")), 0.72)
    viewing = VIEWING_FACTOR.get(str(row.get("viewing_type", "")), 0.72)
    opposition = OPPOSITION_FACTOR.get(str(row.get("opposition_level", "")), 1.00)
    difficulty = DIFFICULTY_FACTOR.get(str(row.get("match_difficulty", "")), 1.00)
    return float(minutes_factor * reliability * viewing * opposition * difficulty)


def weighted_mean(values: Sequence[Tuple[float, float]]) -> Optional[float]:
    usable = [(v, w) for v, w in values if v is not None and w > 0]
    if not usable:
        return None
    total_weight = sum(w for _, w in usable)
    return sum(v * w for v, w in usable) / total_weight if total_weight else None


def weighted_observation_mean(observations: pd.DataFrame, column: str) -> Optional[float]:
    if observations.empty or column not in observations.columns:
        return None
    pairs: List[Tuple[float, float]] = []
    for _, row in observations.iterrows():
        rating = num(row.get(column))
        if rating is None or rating <= 0:
            continue
        pairs.append((rating, observation_weight(row)))
    return weighted_mean(pairs)


def profile_completeness(player: pd.Series, observation_count: int, role_assessment_count: int = 0) -> int:
    weighted_fields = {
        "display_name": 10, "age": 7, "nationality_id": 6, "primary_position": 9,
        "primary_role": 8, "dominant_foot": 5, "height_cm": 4, "current_team_id": 8,
        "status": 5, "potential_rating": 7, "tactical_fit": 7, "position_need": 6,
        "source": 5, "tags": 4, "general_notes": 4,
    }
    score = sum(weight for field, weight in weighted_fields.items() if str(player.get(field, "")).strip())
    score += min(10, observation_count * 5)
    score += min(10, role_assessment_count * 2)
    return int(round(clamp(score)))


def macro_level_score(player: pd.Series, observations: pd.DataFrame) -> int:
    if observations.empty:
        return 0
    position = str(player.get("primary_position", "")).strip()
    if not position:
        nonempty = observations["observed_position"].astype(str).str.strip()
        position = nonempty[nonempty != ""].iloc[-1] if (nonempty != "").any() else ""
    weights = POSITION_WEIGHTS.get(position, {
        "technical_rating": .25, "tactical_rating": .25, "physical_rating": .18,
        "mental_rating": .17, "global_rating": .15,
    })
    parts: List[Tuple[float, float]] = []
    for column, weight in weights.items():
        mean = weighted_observation_mean(observations, column)
        if mean is not None:
            parts.append((mean * 10.0, weight))
    value = weighted_mean(parts)
    return int(round(clamp(value or 0.0)))


def criterion_scores(
    player: pd.Series,
    observations: pd.DataFrame,
    role_assessments: pd.DataFrame,
    role_name: str,
) -> Tuple[Dict[str, float], str]:
    profile = ROLE_PROFILES.get(role_name)
    if not profile:
        return {}, "sin rol"
    result: Dict[str, float] = {}
    detailed = role_assessments[role_assessments["role_name"].astype(str) == role_name] if not role_assessments.empty else pd.DataFrame()
    source = "macros"
    for key, _label, _weight, fallback in profile["criteria"]:  # type: ignore[index]
        value: Optional[float] = None
        if not detailed.empty:
            subset = detailed[detailed["criterion_key"].astype(str) == key]
            ratings = pd.to_numeric(subset.get("rating", pd.Series(dtype=float)), errors="coerce").dropna()
            ratings = ratings[ratings > 0]
            if not ratings.empty:
                value = float(ratings.mean() * 10.0)
                source = "evaluación detallada"
        if value is None:
            macro = weighted_observation_mean(observations, fallback)
            if macro is not None:
                value = macro * 10.0
        if value is not None:
            result[key] = clamp(value)
    return result, source


def role_fit_score(
    player: pd.Series,
    observations: pd.DataFrame,
    role_assessments: pd.DataFrame,
    role_name: str,
) -> Tuple[int, Dict[str, float], str]:
    profile = ROLE_PROFILES.get(role_name)
    if not profile:
        tactical_fit = num(player.get("tactical_fit"), 5.0) or 5.0
        return int(round(clamp(tactical_fit * 10.0))), {}, "encaje manual"
    scores, source = criterion_scores(player, observations, role_assessments, role_name)
    pairs: List[Tuple[float, float]] = []
    for key, _label, weight, _fallback in profile["criteria"]:  # type: ignore[index]
        if key in scores:
            pairs.append((scores[key], weight))
    role_value = weighted_mean(pairs)
    manual_fit = num(player.get("tactical_fit"))
    if role_value is None and manual_fit is None:
        return 50, scores, "sin datos"
    if role_value is None:
        value = (manual_fit or 5.0) * 10.0
        source = "encaje manual"
    elif manual_fit is None:
        value = role_value
    else:
        value = role_value * 0.82 + manual_fit * 10.0 * 0.18
    return int(round(clamp(value))), scores, source


def potential_score(player: pd.Series) -> int:
    manual = num(player.get("potential_rating"))
    if manual is None:
        return 50
    return int(round(clamp(manual * 10.0)))


def need_score(player: pd.Series) -> int:
    manual = num(player.get("position_need"))
    if manual is None:
        return 50
    return int(round(clamp(manual * 10.0)))


def trend_score(observations: pd.DataFrame) -> int:
    if observations.empty:
        return 50
    trends = [TREND_SCORE.get(str(x), 50.0) for x in observations["trend"].tail(3).tolist()]
    if not trends:
        return 50
    weights = list(range(1, len(trends) + 1))
    return int(round(weighted_mean(list(zip(trends, weights))) or 50.0))


def consistency_score(observations: pd.DataFrame) -> int:
    if observations.empty:
        return 0
    ratings = pd.to_numeric(observations.get("global_rating", pd.Series(dtype=float)), errors="coerce").dropna()
    ratings = ratings[ratings > 0]
    if len(ratings) <= 1:
        return 55
    std = float(ratings.std(ddof=0))
    return int(round(clamp(100.0 - std * 22.0)))



def _truthy(value: object) -> bool:
    return normalize_text(value) in {"si", "sí", "true", "1", "yes", "x", "mvp"}


def observation_match_rating(row: pd.Series) -> Optional[float]:
    """Return a 0-10 match rating, using the global mark or the available macros."""
    global_rating = num(row.get("global_rating"))
    if global_rating is not None and global_rating > 0:
        return global_rating
    ratings = [num(row.get(col)) for col in ["technical_rating", "tactical_rating", "physical_rating", "mental_rating"]]
    usable = [value for value in ratings if value is not None and value > 0]
    return sum(usable) / len(usable) if usable else None


def heritage_metrics(player: pd.Series, observations: pd.DataFrame) -> Dict[str, float]:
    """Resumen equivalente a ``Dim_Jugadores`` del Excel y Score Heras 0-100.

    Conserva las señales que hacían útil la hoja original: partidos vistos,
    minutos, nota acumulada y media, MVP, valor competitivo, minutos por
    partido y edad. El ``legacy_raw`` reproduce la fórmula histórica; el
    ``heritage_score`` la regulariza para que un MVP o una sola actuación no
    multipliquen el ranking de forma desproporcionada.
    """
    empty = {
        "matches_seen": 0.0, "total_minutes": 0.0, "avg_minutes": 0.0,
        "average_rating": 0.0, "rating_sum": 0.0, "rated_observations": 0.0,
        "mvp_count": 0.0, "mvp_rate": 0.0, "competition_value": 30.0,
        "heritage_score": 0.0, "performance_adjusted": 0.0, "legacy_raw": 0.0,
    }
    if observations.empty:
        return empty

    match_ids = observations.get("match_id", pd.Series(dtype=str)).astype(str).replace("", pd.NA).dropna()
    matches_seen = int(match_ids.nunique()) if not match_ids.empty else len(observations)
    minutes_series = pd.to_numeric(observations.get("minutes_observed", pd.Series(dtype=float)), errors="coerce").fillna(0)
    total_minutes = float(minutes_series.sum())
    avg_minutes = total_minutes / max(matches_seen, 1)

    ratings = [observation_match_rating(row) for _, row in observations.iterrows()]
    ratings = [float(value) for value in ratings if value is not None and value > 0]
    rating_sum = float(sum(ratings))
    rated_observations = len(ratings)
    average_rating = rating_sum / rated_observations if rated_observations else 0.0

    mvp_count = int(sum(_truthy(value) for value in observations.get("mvp", pd.Series(dtype=str)).tolist()))
    mvp_rate = mvp_count / max(matches_seen, 1)
    comp_values = pd.to_numeric(observations.get("competition_value", pd.Series(dtype=float)), errors="coerce").dropna()
    comp_values = comp_values[(comp_values > 0) & (comp_values <= 50)]
    competition_value = float(comp_values.mean()) if not comp_values.empty else 30.0
    age = num(player.get("age"), 25.0) or 25.0

    if average_rating <= 0:
        return {
            **empty, "matches_seen": float(matches_seen), "total_minutes": total_minutes,
            "avg_minutes": avg_minutes, "mvp_count": float(mvp_count),
            "mvp_rate": mvp_rate, "competition_value": competition_value,
        }

    # Prior bayesiano: dos partidos neutros a 6.0. La primera nota cuenta,
    # pero no decide por sí sola todo el ranking.
    smoothed_rating = (rating_sum + 6.0 * 2.0) / (rated_observations + 2.0)
    rating_score = clamp(smoothed_rating * 10.0)

    # Las mismas señales del Excel, con retornos decrecientes.
    mvp_bonus = min(11.0, 5.0 * math.log1p(mvp_count) + 7.0 * min(mvp_rate, 0.60))
    competition_factor = 0.76 + 0.24 * clamp(competition_value, 1, 50) / 50.0
    minutes_factor = 0.84 + 0.16 * min(max(avg_minutes, 0.0), 90.0) / 90.0
    age_factor = 1.0 + clamp((25.0 - age) * 0.003, -0.04, 0.04)
    evidence_bonus = min(8.0, 2.4 * math.log1p(matches_seen) + 1.2 * math.log1p(total_minutes / 90.0))

    score = clamp((rating_score + mvp_bonus) * competition_factor * minutes_factor * age_factor + evidence_bonus)
    legacy_raw = average_rating * (mvp_count + 1) * competition_value * max(avg_minutes, 1.0) * max(50.0 - age, 1.0)
    # Esta puntuación es solo rendimiento suavizado por la confianza de muestra.
    sample_confidence = clamp(20.0 + 25.0 * min(matches_seen / 3.0, 1.0) + 30.0 * min(total_minutes / 270.0, 1.0) + 25.0 * min(rated_observations / 3.0, 1.0))
    performance_adjusted = adjusted_decision_score(score, sample_confidence)

    return {
        "matches_seen": float(matches_seen), "total_minutes": total_minutes,
        "avg_minutes": avg_minutes, "average_rating": average_rating,
        "rating_sum": rating_sum, "rated_observations": float(rated_observations),
        "mvp_count": float(mvp_count), "mvp_rate": mvp_rate,
        "competition_value": competition_value, "heritage_score": score,
        "performance_adjusted": performance_adjusted, "legacy_raw": legacy_raw,
    }

def confidence_score(player: pd.Series, observations: pd.DataFrame, role_assessments: pd.DataFrame) -> int:
    obs_count = len(observations)
    minutes = float(pd.to_numeric(observations.get("minutes_observed", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not observations.empty else 0.0
    matches = observations["match_id"].astype(str).replace("", pd.NA).dropna().nunique() if not observations.empty else 0
    viewing_diversity = observations["viewing_type"].astype(str).replace("", pd.NA).dropna().nunique() if not observations.empty else 0
    reliability_values = [RELIABILITY_FACTOR.get(str(x), 0.72) for x in observations.get("reliability", pd.Series(dtype=str)).tolist()] if not observations.empty else []
    reliability = (sum(reliability_values) / len(reliability_values)) if reliability_values else 0.50
    completeness = profile_completeness(player, obs_count, len(role_assessments))
    score = 0.0
    score += 24.0 * min(obs_count / 3.0, 1.0)
    score += 24.0 * min(minutes / 270.0, 1.0)
    score += 10.0 * min(matches / 3.0, 1.0)
    score += 8.0 * min(viewing_diversity / 2.0, 1.0)
    score += 10.0 * reliability
    score += 14.0 * completeness / 100.0
    score += 10.0 * consistency_score(observations) / 100.0
    if obs_count == 0:
        score = min(score, 25.0)
    elif obs_count == 1 and minutes < 60:
        score = min(score, 48.0)
    return int(round(clamp(score)))


def adjusted_decision_score(base_score: float, confidence: float) -> float:
    # Shrinkage hacia 50: la poca muestra no premia ni castiga de forma extrema.
    evidence_factor = 0.45 + 0.55 * clamp(confidence) / 100.0
    return clamp(50.0 + (base_score - 50.0) * evidence_factor)


def priority_label(base: float, adjusted: float, confidence: float) -> str:
    if base >= 80 and confidence < 60:
        return "B+"
    if adjusted >= 80 and confidence >= 65:
        return "A"
    if adjusted >= 68:
        return "B"
    if adjusted >= 52:
        return "C"
    return "D"


def next_action(level: float, role_fit: float, base: float, confidence: float) -> str:
    if base >= 80 and confidence >= 70:
        return "Informe completo y decisión fuerte"
    if base >= 76 and confidence < 60:
        return "Segunda observación prioritaria"
    if level >= 72 and confidence < 55:
        return "Validar la señal con 90 minutos"
    if role_fit >= 75 and confidence < 50:
        return "Completar evaluación específica del rol"
    if base < 48 and confidence >= 70:
        return "Descarte razonado o archivo frío"
    if confidence < 35:
        return "No decidir: faltan datos"
    return "Seguimiento normal"


def scoring_breakdown(
    player: pd.Series,
    observations: pd.DataFrame,
    role_assessments: pd.DataFrame,
    weights: Optional[Mapping[str, float]] = None,
    role_override: str = "",
) -> Dict[str, object]:
    selected_role = role_override or str(player.get("primary_role", "")).strip()
    level = macro_level_score(player, observations)
    role_fit, criteria, role_source = role_fit_score(player, observations, role_assessments, selected_role)
    potential = potential_score(player)
    need = need_score(player)
    trend = trend_score(observations)
    confidence = confidence_score(player, observations, role_assessments)
    heritage = heritage_metrics(player, observations)
    score_weights = dict(DEFAULT_SCORING_WEIGHTS)
    if weights:
        score_weights.update({k: float(v) for k, v in weights.items() if k in score_weights})
    total_weight = sum(score_weights.values()) or 1.0
    normalized = {k: v / total_weight for k, v in score_weights.items()}
    base = (
        heritage["heritage_score"] * normalized["heritage"] + role_fit * normalized["role_fit"] +
        potential * normalized["potential"] + need * normalized["need"] + trend * normalized["trend"]
    )
    adjusted = adjusted_decision_score(base, confidence)
    age = num(player.get("age"), 25.0) or 25.0
    age_projection = clamp((24.0 - age) * 0.65, -5.0, 5.0)
    projection = clamp(float(heritage["heritage_score"]) * 0.72 + potential * 0.28 + age_projection)
    label = priority_label(base, adjusted, confidence)
    action = next_action(level, role_fit, base, confidence)
    completion = profile_completeness(player, len(observations), len(role_assessments))

    positive: List[str] = []
    alerts: List[str] = []
    if heritage["heritage_score"] >= 75:
        positive.append(f"score Heras {round(heritage['heritage_score'])}")
    if level >= 75:
        positive.append(f"nivel observado {level}")
    if role_fit >= 75:
        positive.append(f"encaje de rol {role_fit}")
    if potential >= 78:
        positive.append(f"potencial {potential}")
    if confidence >= 70:
        positive.append("evidencia sólida")
    if len(observations) >= 2:
        positive.append("muestra repetida")
    if completion >= 75:
        positive.append("ficha completa")

    if observations.empty:
        alerts.append("sin observaciones")
    elif len(observations) == 1:
        alerts.append("una sola observación")
    if confidence < 45:
        alerts.append("confianza baja")
    if level >= 78 and confidence < 58:
        alerts.append("señal alta con poca muestra")
    if completion < 50:
        alerts.append("ficha incompleta")
    if not selected_role:
        alerts.append("sin rol principal")
    manual_priority = str(player.get("manual_priority", "")).strip()
    if manual_priority and manual_priority != label:
        alerts.append(f"prioridad manual {manual_priority} ≠ modelo {label}")

    return {
        "role": selected_role,
        "level": int(round(level)),
        "heritage_score": round(float(heritage["heritage_score"]), 1),
        "average_rating": round(float(heritage["average_rating"]), 2),
        "rating_sum": round(float(heritage["rating_sum"]), 2),
        "rated_observations": int(heritage["rated_observations"]),
        "matches_seen": int(heritage["matches_seen"]),
        "total_minutes": int(heritage["total_minutes"]),
        "avg_minutes": round(float(heritage["avg_minutes"]), 1),
        "mvp_count": int(heritage["mvp_count"]),
        "mvp_rate": round(float(heritage["mvp_rate"]) * 100.0, 1),
        "competition_value": round(float(heritage["competition_value"]), 1),
        "performance_adjusted": round(float(heritage["performance_adjusted"]), 1),
        "projection_score": round(float(projection), 1),
        "legacy_raw": round(float(heritage["legacy_raw"]), 1),
        "role_fit": int(round(role_fit)),
        "potential": int(round(potential)),
        "need": int(round(need)),
        "trend": int(round(trend)),
        "confidence": int(round(confidence)),
        "completeness": int(round(completion)),
        "base_score": round(base, 1),
        "decision_score": round(adjusted, 1),
        "priority_label": label,
        "next_action": action,
        "positive_signals": positive,
        "alerts": alerts,
        "criteria": criteria,
        "role_source": role_source,
        "observation_count": len(observations),
        "minutes": int(heritage["total_minutes"]),
        "consistency": consistency_score(observations),
    }


def metrics_table(
    players: pd.DataFrame,
    observations: pd.DataFrame,
    role_assessments: pd.DataFrame,
    weights: Optional[Mapping[str, float]] = None,
    role_override: str = "",
) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for _, player in players.iterrows():
        player_id = str(player.get("player_id", ""))
        obs = observations[observations["player_id"].astype(str) == player_id] if not observations.empty else observations
        assessments = role_assessments[role_assessments["player_id"].astype(str) == player_id] if not role_assessments.empty else role_assessments
        score = scoring_breakdown(player, obs, assessments, weights, role_override)
        row = player.to_dict()
        row.update(score)
        row["signals_text"] = " · ".join(score["positive_signals"])
        row["alerts_text"] = " · ".join(score["alerts"])
        rows.append(row)
    return pd.DataFrame(rows)


def percentile(values: pd.Series, value: float) -> int:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return 0
    return int(round((numeric <= value).mean() * 100.0))


def cosine_similarity(vector_a: Mapping[str, float], vector_b: Mapping[str, float]) -> float:
    keys = sorted(set(vector_a) & set(vector_b))
    if not keys:
        return 0.0
    a = [float(vector_a[k]) for k in keys]
    b = [float(vector_b[k]) for k in keys]
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return clamp(dot / (norm_a * norm_b) * 100.0)


def similarity_table(
    reference_player: pd.Series,
    candidate_players: pd.DataFrame,
    observations: pd.DataFrame,
    role_assessments: pd.DataFrame,
    role_name: str,
) -> pd.DataFrame:
    ref_id = str(reference_player.get("player_id", ""))
    ref_obs = observations[observations["player_id"].astype(str) == ref_id] if not observations.empty else observations
    ref_ass = role_assessments[role_assessments["player_id"].astype(str) == ref_id] if not role_assessments.empty else role_assessments
    ref_vector, _ = criterion_scores(reference_player, ref_obs, ref_ass, role_name)
    rows: List[Dict[str, object]] = []
    for _, player in candidate_players.iterrows():
        pid = str(player.get("player_id", ""))
        if pid == ref_id:
            continue
        obs = observations[observations["player_id"].astype(str) == pid] if not observations.empty else observations
        ass = role_assessments[role_assessments["player_id"].astype(str) == pid] if not role_assessments.empty else role_assessments
        vector, source = criterion_scores(player, obs, ass, role_name)
        similarity = cosine_similarity(ref_vector, vector)
        if similarity <= 0:
            continue
        rows.append({
            "player_id": pid,
            "display_name": player.get("display_name", ""),
            "primary_position": player.get("primary_position", ""),
            "age": player.get("age", ""),
            "similarity": round(similarity, 1),
            "source": source,
        })
    return pd.DataFrame(rows).sort_values("similarity", ascending=False) if rows else pd.DataFrame()
