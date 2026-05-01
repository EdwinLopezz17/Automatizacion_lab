import pandas as pd

def to_date(val, format=None):
    if val is None or pd.isna(val):
        return None

    if hasattr(val, 'date'):
        try:
            d = val.date()
            return d if d.year > 1900 else None
        except Exception:
            return None
    try:
        if format == "DMA":
            ts = pd.to_datetime(val, dayfirst=True, errors='coerce')
        elif format == "MDA":
            ts = pd.to_datetime(val, dayfirst=False, errors='coerce')
        else:
            ts = pd.to_datetime(val, errors='coerce')

        if pd.isna(ts) or ts.year < 1900:
            return None

        return ts.date()

    except Exception:
        return None