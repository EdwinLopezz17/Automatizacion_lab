import io
import pandas as pd

from core.excel_writer import _crear_wb_vacio, _df_to_sheet, wb_to_buffer
from services.post_cese_service import PostCeseService
from services.account_type_service import AccountTypeService
from services.ad_service import ADService
from services.gdh_service import GDHUserService
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
) -> io.BytesIO:
    
    accountTypeService = AccountTypeService()
    ad_service = ADService()
    gdh_service = GDHUserService()

    entra = df_entra_id.copy()
    entra.columns = [str(c).strip() for c in entra.columns]

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

        matricula = ad_service.get_AD_user_by_correo(correo_key).usuario
        
        if not matricula:
            if c_city:
                val_city = str(row[c_city]).strip()
                if val_city and val_city.lower() not in ("nan", "none", ""):
                    matricula = val_city.upper()

        tipo = accountTypeService.get(matricula).tipo

        nombre = str(row[c_disp]).strip() if c_disp else ""
        estado = "Activo" if str(row[c_enab]).strip().upper() == "TRUE" else "Bloqueado"
        fec_creacion = to_date(row[c_crea]) if c_crea else None

        userGDH = gdh_service.get_GDH_user(matricula)

        fecha_cese = userGDH.fecha_cese
        cesado_activo = "Incorrecto" if (estado == "Activo" and userGDH.isCesado) else "Correcto"
        sin_sustento = "Incorrecto" if estado == "Activo" and not userGDH.isCesado and not userGDH.isActivo else "Correcto"

        rows.append({
            "Correo": correo_key.lower(),
            "Matricula (SAM/City)": matricula,
            "Tipo de Cuenta": tipo,
            "Nombre": nombre,
            "Estado": estado,
            "Fecha Creación": fec_creacion,
            "activoGDH": "si" if userGDH.isActivo else "no",
            "cesadoGDH": "si" if userGDH.isCesado else "no",
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
