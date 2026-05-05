import pandas as pd
from datetime import date

def sin_uso(estado:bool, createdAt:date, loginAt:date, fecha_ref:date) -> str:
    if not estado:
        return "Correcto"
    elif createdAt and (fecha_ref - createdAt).days <= 90:
        return "Correcto"
    elif loginAt and (fecha_ref - loginAt).days <= 90:
        return "Correcto"
    else:
        return "Incorrecto"

def to_date(val, format=None):
    if val is None or pd.isna(val):
        return None
    
    if format is not None:
        try:
            if format == "DMA":
                ts = pd.to_datetime(val, dayfirst=True, errors='coerce')
            elif format == "MDA":
                ts = pd.to_datetime(val, dayfirst=False, errors='coerce')
            else:
                ts = pd.to_datetime(val, errors='coerce')

            if not pd.isna(ts) and ts.year > 1900:
                return ts.date()
        except Exception:
            pass

    if hasattr(val, 'date'):
        try:
            d = val.date()
            return d if d.year > 1900 else None
        except Exception:
            return None

    try:
        ts = pd.to_datetime(val, errors='coerce')
        if pd.isna(ts) or ts.year < 1900:
            return None
        return ts.date()
    except Exception:
        return None