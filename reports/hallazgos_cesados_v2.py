import io
import pandas as pd
from core.utils import to_date

from core.normalizer import normalizar_df, find_col
from core.excel_writer import _crear_wb_vacio as crear_wb_vacio, wb_to_buffer, _df_to_sheet, DATE_COLS_CESADOS
from services.post_cese_service import PostCeseService
from services.ad_service import ADService
from services.gdh_service import GDHUserService
from services.db_exactus_service import DBExactusService
from services.db_sdp_service import DBSdpService
from services.app_exactus_service import AppExactusService
from services.app_sdp_service import AppSdpService
from services.entra_service import EntraIDService

def _to_str(val) -> str:
    if val is None: return ""
    try:
        if pd.isna(val): return ""
    except Exception: pass
    return str(val).strip()

def _norm(val) -> str:
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    return str(val).strip().upper()

def _safe_isna(val) -> bool:
    try: return bool(pd.isna(val))
    except Exception: return False

def _build_set(df, key_col) -> set:
    if df is None or df.empty or not key_col: return set()
    return {_norm(_to_str(v)) for v in df[key_col].dropna()}

def generar_reporte_hallazgos_cesados(
    df_sit_hab, df_npac_hab, df_db_sit
) -> io.BytesIO:
    
    postCeseService = PostCeseService()
    ad_service = ADService()
    gdh_service = GDHUserService()
    db_exactus_service = DBExactusService()
    db_sdp_service = DBSdpService()
    app_sdp_service = AppSdpService()
    app_exactus_service = AppExactusService()
    entra_service = EntraIDService()

    _n = lambda df: normalizar_df(df) if (df is not None and not df.empty) else pd.DataFrame()

    sit_hab = _n(df_sit_hab)
    npac_hab = _n(df_npac_hab)

    c_sit = find_col(sit_hab, ["SAMACCOUNTNAME", "SAM ACCOUNT NAME"])
    sit_set = _build_set(sit_hab, c_sit)
    c_npac = find_col(npac_hab, ["SAMACCOUNTNAME", "SAM ACCOUNT NAME"])
    npac_set = _build_set(npac_hab, c_npac)

    dbsit_active, dbsit_login = {}, {}
    if df_db_sit is not None and not df_db_sit.empty:
        orig_norm = normalizar_df(df_db_sit.copy())
        orig_raw = df_db_sit.copy()
        orig_raw.columns = [str(c).strip() for c in orig_raw.columns]

        c_ln = find_col(orig_norm, ["LOGINNAME", "LOGIN NAME"])
        c_ac = find_col(orig_norm, ["ISACTIVE", "IS ACTIVE", "ACTIVO"])
        c_ul_raw = find_col(orig_raw,  ["ULTIMOLOGEO", "ULTIMO LOGEO", "ULTIMO_LOGEO", "LAST LOGIN", "UltimoLogeo"])

        if c_ln:
            orig_norm = orig_norm.reset_index(drop=True)
            orig_raw  = orig_raw.reset_index(drop=True)
            for i in range(len(orig_norm)):
                row_norm = orig_norm.iloc[i]
                row_raw  = orig_raw.iloc[i]
                raw_key = _to_str(row_norm[c_ln])
                key = _norm(raw_key.split("\\")[-1]) if "\\" in raw_key else _norm(raw_key)
                if not key:
                    continue
                if c_ac:
                    dbsit_active[key] = _to_str(row_norm[c_ac])
                if c_ul_raw:
                    raw_fecha = row_raw[c_ul_raw]
                    if not _safe_isna(raw_fecha) and key not in dbsit_login:
                        dbsit_login[key] = to_date(raw_fecha)
                    elif key not in dbsit_login:
                        dbsit_login[key] = ""

    VAL_CESADO_ACTIVO = ["AD Nipa", "Entra ID", "Usr Exactus", "DB Exactus",
                         "Usr SDP", "DB SDP", "Usr SIT", "DB SIT", "Usr NPAC"]

    rows = []
    for userCesado in gdh_service.get_cesados_GDH_user():
        matricula = userCesado.matricula
        ad_user = ad_service.get_AD_user(matricula)
        entra_user = entra_service.get_by_mail(ad_user.correo)

        app_exactus_user = app_exactus_service.get_UserAppExactus(matricula)
        app_sdp_user = app_sdp_service.get_UserAppSdp(matricula)

        usr_sit  = "Incorrecto" if userCesado.matricula in sit_set  else "Correcto"
        usr_npac = "Incorrecto" if userCesado.matricula in npac_set else "Correcto"

        isactive = _to_str(dbsit_active.get(matricula, ""))
        db_sit_val = "Incorrecto" if isactive == "ACTIVO" else "Correcto"
        db_sit_login = dbsit_login.get(matricula, "")

        db_sdp_user = db_sdp_service.get_UserDBSdp(matricula)
        db_sdp_val = "Incorrecto" if db_sdp_user.isActivo else "Correcto"

        db_exa_user = db_exactus_service.get_UserDBExactus(matricula)
        db_exa_val = "Incorrecto" if db_exa_user.isActivo else "Correcto"

        ad_nipa_val = "Incorrecto" if ad_user.isActivo else "Correcto"
        ad_nipa_login = ad_user.fecha_ult_login
        postCeseADNipa = postCeseService.es_post_cese(matricula, "Active_Directory", userCesado.fecha_cese, ad_nipa_login)
 
        postCeseEntraID = postCeseService.es_post_cese(matricula, "APP_ENTRAID", userCesado.fecha_cese, entra_user.ultimo_login)
        postCeseAppExa =  postCeseService.es_post_cese (matricula, "APP_Exactus", userCesado.fecha_cese, app_exactus_user.fecha_login)
        postCeseDBExa = postCeseService.es_post_cese (matricula, "DB_EXACTUS", userCesado.fecha_cese, db_exa_user.fecha_login)
        postCeseAppSDP = postCeseService.es_post_cese (matricula, "APP_SDP", userCesado.fecha_cese, app_sdp_user.fecha_login)
        postCEseDBSDP = postCeseService.es_post_cese (matricula, "DB_SDP", userCesado.fecha_cese, db_sdp_user.fecha_login)
        postCeseDBSIT = postCeseService.es_post_cese (matricula, "DB_SIT", userCesado.fecha_cese, db_sit_login)

        r = {
            "Matricula": matricula,
            "Nombre": userCesado.nombre +" "+userCesado.apellido_paterno+" "+userCesado.apellido_materno,
            "Unidad organizativa": userCesado.u_organizativa,
            "Fecha de Cese": userCesado.fecha_cese,
            "AD Nipa": ad_nipa_val,
            "Ultimo Login AD Nipa": ad_nipa_login,
            "PostCese AD Nipa": "Incorrecto" if postCeseADNipa else "Correcto",
            "Entra ID": "Incorrecto" if entra_user.account_enabled else "Correcto",
            "Entra ID Ultimo Login": entra_user.ultimo_login,
            "PostCese Entra ID": "Incorrecto" if postCeseEntraID else "Correcto",
            "Usr Exactus": "Incorrecto" if app_exactus_user.isActivo else "Correcto",
            "Usr Exactus Ultimo Login": app_exactus_user.fecha_login,
            "PostCese Exactus App": "Incorrecto" if postCeseAppExa else "Correcto",
            "DB Exactus": db_exa_val,
            "DB Exactus Ultimo Login": db_exa_user.fecha_login,
            "PostCese DB Exactus": "Incorrecto" if postCeseDBExa else "Correcto",
            "Usr SDP": "Incorrecto" if app_sdp_user.isActivo else "Correcto",
            "Usr SDP Ultimo Login": app_sdp_user.fecha_login,
            "PostCese SDP App": "Incorrecto" if postCeseAppSDP else "Correcto",
            "DB SDP":db_sdp_val, 
            "DB SDP Ultimo Login":db_sdp_user.fecha_login,
            "PostCese DB SDP": "Incorrecto" if postCEseDBSDP else "Correcto",
            "DB SIT":db_sit_val,
            "DB SIT Ultimo Login":db_sit_login,
            "PostCese DB SIT": "Incorrecto" if postCeseDBSIT else "Correcto",
            "Usr NPAC":usr_npac,
            "Usr SIT":usr_sit,
        }
        
        r["Validación Cesado Activo"] = "Incorrecto" if any(r.get(c) == "Incorrecto" for c in VAL_CESADO_ACTIVO) else "Correcto"
        r["Validación Post Cese"] = "Incorrecto" if postCeseADNipa or postCeseEntraID or postCeseAppExa or postCeseDBExa or postCeseAppSDP or postCEseDBSDP or postCeseDBSIT else "Correcto"
        rows.append(r)

    df_out = pd.DataFrame(rows)

    wb = crear_wb_vacio()
    _df_to_sheet(wb, "Hallazgos Cesados", df_out, date_cols=DATE_COLS_CESADOS)
    return wb_to_buffer(wb)
