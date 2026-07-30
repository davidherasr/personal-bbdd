from __future__ import annotations

import io
import json
import os
import re
import shutil
import tempfile
import unicodedata
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from .config import DEFAULT_SCORING_WEIGHTS, SCHEMAS

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("SCOUTING_DATA_DIR", str(BASE_DIR / "data")))
SETTINGS_PATH = DATA_DIR / "settings.json"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def table_path(table: str) -> Path:
    if table not in SCHEMAS:
        raise KeyError(f"Tabla desconocida: {table}")
    return DATA_DIR / f"{table}.csv"


def empty_table(table: str) -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEMAS[table])


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for table in SCHEMAS:
        path = table_path(table)
        if not path.exists():
            atomic_write_csv(path, empty_table(table))
    if not SETTINGS_PATH.exists():
        save_settings({"scoring_weights": DEFAULT_SCORING_WEIGHTS})


def atomic_write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".csv", prefix="tmp_", dir=path.parent, delete=False, encoding="utf-8", newline="") as temp:
        temp_path = Path(temp.name)
        df.to_csv(temp, index=False)
    os.replace(temp_path, path)


def migrate_dataframe(table: str, df: pd.DataFrame) -> pd.DataFrame:
    schema = SCHEMAS[table]
    out = df.copy().fillna("")
    # Compatibilidad básica con v0.7.
    aliases = {
        "players": {
            "priority_manual": "manual_priority",
            "potential": "potential_rating",
        },
        "matches": {
            "match_name": "_legacy_match_name",
        },
    }
    for old, new in aliases.get(table, {}).items():
        if old in out.columns and new not in out.columns:
            out[new] = out[old]
    for col in schema:
        if col not in out.columns:
            out[col] = ""
    if table == "players":
        out["normalized_name"] = out["display_name"].map(normalize_text)
        # Convierte potencial categórico antiguo a escala 0-10.
        mapping = {"Muy alto": "9", "Alto": "8", "Medio-alto": "7", "Medio": "5.5", "Bajo": "3.5", "Muy bajo": "2"}
        out["potential_rating"] = out["potential_rating"].map(lambda x: mapping.get(str(x), x))
        if "updated_at" in out.columns:
            out["updated_at"] = out["updated_at"].where(out["updated_at"].astype(str).str.len() > 0, out.get("created_at", ""))
    elif table in {"countries", "competitions", "teams"}:
        out["normalized_name"] = out["name"].map(normalize_text)
    elif table == "aliases":
        out["normalized_alias"] = out["alias"].map(normalize_text)
    elif table == "matches" and "_legacy_match_name" in out.columns:
        # El nombre antiguo era solo visual; local y visitante siguen siendo la fuente de verdad.
        out = out.drop(columns=["_legacy_match_name"], errors="ignore")
    return out[schema].fillna("")


def load_table(table: str) -> pd.DataFrame:
    ensure_storage()
    path = table_path(table)
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
    except pd.errors.EmptyDataError:
        df = empty_table(table)
    migrated = migrate_dataframe(table, df)
    if list(migrated.columns) != list(df.columns) or migrated.shape[1] != df.shape[1]:
        atomic_write_csv(path, migrated)
    return migrated


def save_table(table: str, df: pd.DataFrame) -> None:
    ensure_storage()
    atomic_write_csv(table_path(table), migrate_dataframe(table, df))


def append_row(table: str, row: Dict[str, object]) -> str:
    df = load_table(table)
    id_col = SCHEMAS[table][0]
    prefix = {
        "countries": "cty", "competitions": "cmp", "teams": "team", "players": "ply",
        "matches": "mat", "observations": "obs", "role_assessments": "ras",
        "aliases": "als", "lineups": "lin", "lineup_slots": "slot",
    }[table]
    row = dict(row)
    row.setdefault(id_col, new_id(prefix))
    row.setdefault("created_at", now_str())
    complete = {col: row.get(col, "") for col in SCHEMAS[table]}
    df.loc[len(df)] = [complete[col] for col in SCHEMAS[table]]
    save_table(table, df)
    return str(complete[id_col])


def update_row(table: str, id_value: str, updates: Dict[str, object]) -> bool:
    df = load_table(table)
    id_col = SCHEMAS[table][0]
    mask = df[id_col].astype(str) == str(id_value)
    if not mask.any():
        return False
    for key, value in updates.items():
        if key in df.columns:
            df.loc[mask, key] = value
    if table == "players":
        df.loc[mask, "updated_at"] = now_str()
    save_table(table, df)
    return True


def delete_rows(table: str, ids: Iterable[str]) -> int:
    df = load_table(table)
    id_col = SCHEMAS[table][0]
    ids_set = {str(x) for x in ids}
    before = len(df)
    df = df[~df[id_col].astype(str).isin(ids_set)].copy()
    save_table(table, df)
    return before - len(df)


def get_settings() -> Dict[str, object]:
    ensure_storage()
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {}
    data.setdefault("scoring_weights", DEFAULT_SCORING_WEIGHTS.copy())
    return data


def save_settings(settings: Dict[str, object]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = SETTINGS_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, SETTINGS_PATH)


def backup_zip_bytes() -> bytes:
    ensure_storage()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for table in SCHEMAS:
            path = table_path(table)
            zf.writestr(f"data/{table}.csv", path.read_bytes())
        zf.writestr("data/settings.json", SETTINGS_PATH.read_bytes())
        zf.writestr("manifest.json", json.dumps({"version": "1.0", "created_at": now_str(), "tables": list(SCHEMAS)}, ensure_ascii=False, indent=2))
    return buffer.getvalue()


def excel_backup_bytes() -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for table in SCHEMAS:
            load_table(table).to_excel(writer, sheet_name=table[:31], index=False)
    return buffer.getvalue()


def _safe_zip_member(name: str) -> bool:
    path = Path(name)
    return not path.is_absolute() and ".." not in path.parts


def restore_zip_bytes(data: bytes) -> Tuple[int, List[str]]:
    ensure_storage()
    restored = 0
    messages: List[str] = []
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        names = set(zf.namelist())
        if any(not _safe_zip_member(name) for name in names):
            raise ValueError("El ZIP contiene rutas no seguras.")
        for table in SCHEMAS:
            candidates = [f"data/{table}.csv", f"{table}.csv"]
            member = next((x for x in candidates if x in names), None)
            if not member:
                member = next((x for x in names if Path(x).name == f"{table}.csv"), None)
            if not member:
                continue
            with zf.open(member) as fh:
                try:
                    df = pd.read_csv(fh, dtype=str).fillna("")
                except pd.errors.EmptyDataError:
                    df = empty_table(table)
            save_table(table, df)
            restored += 1
        settings_member = next((x for x in ["data/settings.json", "settings.json"] if x in names), None)
        if not settings_member:
            settings_member = next((x for x in names if Path(x).name == "settings.json"), None)
        if settings_member:
            with zf.open(settings_member) as fh:
                settings = json.loads(fh.read().decode("utf-8"))
            save_settings(settings)
    if restored == 0:
        messages.append("No se encontró ninguna tabla reconocible.")
    return restored, messages


def restore_excel(uploaded: object) -> int:
    xls = pd.ExcelFile(uploaded)
    restored = 0
    for table in SCHEMAS:
        if table in xls.sheet_names:
            save_table(table, pd.read_excel(xls, sheet_name=table, dtype=str).fillna(""))
            restored += 1
    return restored


def reset_all_data() -> None:
    ensure_storage()
    for table in SCHEMAS:
        save_table(table, empty_table(table))
    save_settings({"scoring_weights": DEFAULT_SCORING_WEIGHTS.copy()})


def snapshot_data(label: str = "pre_restore") -> Path:
    ensure_storage()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_DIR / "snapshots" / f"{label}_{stamp}.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(backup_zip_bytes())
    return path


def import_csv(table: str, uploaded: object, replace: bool = False) -> Tuple[int, int]:
    try:
        incoming = pd.read_csv(uploaded, dtype=str).fillna("")
    except pd.errors.EmptyDataError:
        incoming = empty_table(table)
    incoming = migrate_dataframe(table, incoming)
    if replace:
        save_table(table, incoming)
        return len(incoming), 0
    current = load_table(table)
    id_col = SCHEMAS[table][0]
    existing_ids = set(current[id_col].astype(str))
    rows = incoming[~incoming[id_col].astype(str).isin(existing_ids)].copy()
    combined = pd.concat([current, rows], ignore_index=True)
    save_table(table, combined)
    return len(rows), len(incoming) - len(rows)


def copy_empty_templates(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for table in SCHEMAS:
        empty_table(table).to_csv(target_dir / f"{table}_template.csv", index=False)
