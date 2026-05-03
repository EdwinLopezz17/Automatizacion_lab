import io
import pandas as pd

from core.excel_writer import _crear_wb_vacio, _df_to_sheet, wb_to_buffer
from services.post_cese_service import PostCeseService
from services.account_type_service import AccountTypeService
from services.ad_service import ADService
from services.gdh_service import GDHUserService
from services.entra_service import EntraIDService

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

def generar_reporte_hallazgos_entra_id() -> io.BytesIO:
    
    accountTypeService = AccountTypeService()
    postCeseService = PostCeseService()
    ad_service = ADService()
    gdh_service = GDHUserService()
    entra_service = EntraIDService()

    rows = []
    for entra_user in entra_service.get_all_UsersEntraID():
    
        matricula = ad_service.get_AD_user_by_correo(entra_user.mail).usuario
        if not matricula:
            matricula = entra_user.city

        tipo = accountTypeService.get(entra_user.mail).tipo
        if tipo == "sin clasificar":
            tipo = accountTypeService.get(matricula).tipo

        if tipo == "servicio":
            continue

        userGDH = gdh_service.get_GDH_user(matricula)

        fecha_cese = userGDH.fecha_cese
        cesado_activo = "Incorrecto" if (entra_user.account_enabled and userGDH.isCesado) else "Correcto"
        sin_sustento = "Incorrecto" if (entra_user.account_enabled and not userGDH.isCesado and not userGDH.isActivo) else "Correcto"

        rows.append({
            "Correo": entra_user.mail,
            "Matricula (SAM/City)": matricula,
            "Tipo de Cuenta": tipo,
            "Nombre": entra_user.display_name,
            "Estado": "Activo" if entra_user.account_enabled else "Bloqueado",
            "Fecha Creación": entra_user.created_date_time,
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
