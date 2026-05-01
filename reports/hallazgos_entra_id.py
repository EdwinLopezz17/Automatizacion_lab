import io
import pandas as pd
from datetime import date
from typing import Optional

from core.normalizer import normalizar_df
from core.excel_writer import _crear_wb_vacio, _df_to_sheet, wb_to_buffer
from core.post_cese_service import PostCeseService
from core.account_type_service import AccountTypeService
from core.utils import to_date

DATE_COLS_ENTRA = {"Fecha Creación", "Fecha Cese"}

def _find(df, candidates):
    up = {str(c).strip().upper(): c for c in df.columns}
    for c in candidates:
        if c.strip().upper() in up:
            return up[c.strip().upper()]
    for c in candidates:
        key = c.strip().upper()
        for norm_c, orig_c in up.items():
            if key in norm_c or norm_c in key:
                return orig_c
    return None

def generar_reporte_hallazgos_entra_id(
    df_entra_id:    pd.DataFrame,
    df_activos_gdh: pd.DataFrame,
    df_cesados_gdh: pd.DataFrame,
    df_ad_prima:    pd.DataFrame,
    accountTypeService: AccountTypeService,
    postCeseService: PostCeseService
) -> io.BytesIO:

    entra = df_entra_id.copy()
    entra.columns = [str(c).strip() for c in entra.columns]
    gdh = normalizar_df(df_activos_gdh)
    
    ad_raw = df_ad_prima.copy()
    ad_raw.columns = [str(c).strip() for c in ad_raw.columns]
    c_ad_sam_raw  = _find(ad_raw, ["SAMACCOUNTNAME"])
    c_ad_mail_raw = _find(ad_raw, ["MAIL"])
    
    mail_to_sam_ad: dict = {}
    if c_ad_sam_raw and c_ad_mail_raw:
        for _, r in ad_raw.iterrows():
            m = str(r[c_ad_mail_raw]).strip().upper()
            s = str(r[c_ad_sam_raw]).strip().upper()
            if m and m not in ("NAN", "NONE", "") and s and s not in ("NAN", "NONE", ""):
                mail_to_sam_ad[m] = s

    c_gdh_id = _find(gdh, ["ID SISTEMA"])
    gdh_set = {str(r[c_gdh_id]).strip().upper() for _, r in gdh.iterrows() if c_gdh_id and str(r[c_gdh_id]).strip()}

    ces_raw = df_cesados_gdh.copy()
    ces_raw.columns = [str(c).strip() for c in ces_raw.columns]
    c_ces_id_raw  = _find(ces_raw, ["ID SISTEMA"])
    c_ces_fec_raw = _find(ces_raw, ["FECHA"])
    ces_set = set()
    ces_fecha_map = {}
    if c_ces_id_raw:
        for _, r in ces_raw.iterrows():
            k = str(r[c_ces_id_raw]).strip().upper()
            if k:
                ces_set.add(k)
                if c_ces_fec_raw:
                    ces_fecha_map[k] = to_date(r[c_ces_fec_raw])

    c_mail = _find(entra, ["mail"])
    c_upn  = _find(entra, ["userPrincipalName"])
    c_city = _find(entra, ["city"])
    c_disp = _find(entra, ["displayName"])
    c_enab = _find(entra, ["accountEnabled"])
    c_crea = _find(entra, ["createdDateTime"])

    rows = []
    for _, row in entra.iterrows():
        correo_key = ""
        if c_mail:
            val = str(row[c_mail]).strip()
            if val and val.lower() not in ("nan", "none", ""):
                correo_key = val.upper()
        if not correo_key and c_upn:
            val = str(row[c_upn]).strip()
            if val and val.lower() not in ("nan", "none", ""):
                correo_key = val.upper()

   
        if accountTypeService.get(correo_key).tipo == "servicio":
            continue

        matricula = mail_to_sam_ad.get(correo_key, "")
        
        if not matricula:
            if c_city:
                val_city = str(row[c_city]).strip()
                if val_city and val_city.lower() not in ("nan", "none", ""):
                    matricula = val_city.upper()


        tipo = accountTypeService.get(matricula).tipo

        nombre = str(row[c_disp]).strip() if c_disp else ""
        estado = "Activo" if str(row[c_enab]).strip().upper() == "TRUE" else "Bloqueado"
        fec_creacion = to_date(row[c_crea]) if c_crea else None

        mat_key = matricula.upper() if matricula else ""
        es_activo_gdh = "si" if mat_key and mat_key in gdh_set else "no"
        es_cesado_gdh = "si" if mat_key and mat_key in ces_set else "no"
        fecha_cese = ces_fecha_map.get(mat_key) if es_cesado_gdh == "si" else None

        cesado_activo = "INCORRECTO" if (estado == "Activo" and es_cesado_gdh == "si") else "CORRECTO"
        sin_sustento = (
            "INCORRECTO"
            if estado == "Activo" and es_activo_gdh == "no" and es_cesado_gdh == "no"
            else "CORRECTO"
        )

        rows.append({
            "Correo": correo_key.lower(),
            "Matricula (SAM/City)": matricula,
            "Tipo de Cuenta": tipo,
            "Nombre": nombre,
            "Estado": estado,
            "Fecha Creación": fec_creacion,
            "activoGDH": es_activo_gdh,
            "cesadoGDH": es_cesado_gdh,
            "Fecha Cese": fecha_cese,
            "cesadoActivo": cesado_activo,
            "Sin Sustento": sin_sustento,
            "Validación Final": "",
            "Acción Correctiva":""
        })

    df_out = pd.DataFrame(rows)
    wb = _crear_wb_vacio()
    _df_to_sheet(wb, "Entra ID", df_out, date_cols=DATE_COLS_ENTRA)
    return wb_to_buffer(wb)
