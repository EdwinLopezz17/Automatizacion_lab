import unicodedata
import pandas as pd
import os
import sys
import json
from typing import Optional

def _limpiar_str(valor) -> str:
    if pd.isna(valor):
        return ""
    s = str(valor)
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")
    return s.strip().upper()

def normalizar_df(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {col: df[col].apply(_limpiar_str) for col in df.columns},
        index=df.index
    )

def _get_config_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_column_name(df: pd.DataFrame, app_name: str, col_key: str) -> str:

    ruta_json = os.path.join(_get_config_path(), "columns.json")

    try:
        with open(ruta_json, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}

    candidatos = config.get(app_name, {}).get(col_key, [col_key])

    real_col = find_col(df, candidatos)

    if not real_col:
        raise ValueError(f"No se encontró la columna para '{col_key}' en la app '{app_name}'. "
                         f"Candidatos probados: {candidatos}")
    return real_col

def find_col(df, candidates):
    norm_map = {_limpiar_str(c): c for c in df.columns}
    for cand in candidates:
        key = _limpiar_str(cand)
        if key in norm_map:
            return norm_map[key]
    for cand in candidates:
        key = _limpiar_str(cand)
        for norm_c, orig_c in norm_map.items():
            if key in norm_c or norm_c in key:
                return orig_c
    return None

