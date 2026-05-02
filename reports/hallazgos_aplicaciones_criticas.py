import io
import pandas as pd
from datetime import date
from typing import Optional

from core.normalizer import normalizar_df
from core.excel_writer import _crear_wb_vacio, _df_to_sheet, wb_to_buffer
from core.post_cese_service import PostCeseService
from core.account_type_service import AccountTypeService
from core.ad_service import ADService
from core.gdh_service import GDHUserService, GDHUserInfo
from core.utils import to_date

DATE_COLS_APP = {"Fecha Creación", "Ultimo Login", "Fecha Cese"}
DATE_COLS_AD  = {"Fecha Creación AD", "Ultimo Login AD", "Fecha Cese"}

def _find(df: pd.DataFrame, candidates: list) -> Optional[str]:
    up = {str(c).strip().upper(): c for c in df.columns}
    for cand in candidates:
        key = cand.strip().upper()
        if key in up:
            return up[key]
    for cand in candidates:
        key = cand.strip().upper()
        for norm_c, orig_c in up.items():
            if key in norm_c or norm_c in key:
                return orig_c
    return None

def _safe_upper(row, col: Optional[str]) -> Optional[str]:
    if col and pd.notna(row.get(col)):
        return str(row[col]).strip().upper()
    return None

def _calcular_indicadores(
    gdh_user: GDHUserInfo,
    ult_login: Optional[date],
    is_app_active: bool,
    fec_creacion_app: Optional[date],
    fecha_ref: date,
    aplicacion: str,
    postCeseService: PostCeseService,
) -> dict:

    # sinuso 90d
    if not gdh_user.isActivo:
        sin_uso = "Correcto"
    elif fec_creacion_app and (fecha_ref - fec_creacion_app).days <= 90:
        sin_uso = "Correcto"
    elif ult_login and (fecha_ref - ult_login).days <= 90:
        sin_uso = "Correcto"
    else:
        sin_uso = "Incorrecto"

    actividad_post = ( "Incorrecto"
        if postCeseService.es_post_cese(gdh_user.matricula, aplicacion, gdh_user.fecha_cese, ult_login)
        else "Correcto"
    )

    return {
        "activoGDH": "si" if gdh_user.isActivo else "no",
        "cesadoGDH": "si" if gdh_user.isCesado else "no",
        "Fecha Cese": gdh_user.fecha_cese,
        "sinUso>90d": sin_uso,
        "cesadoActivo": "Incorrecto" if gdh_user.isCesado and is_app_active else "Correcto",
        "actividadPostCese": actividad_post,
        "Sin Sustento": "Incorrecto" if not gdh_user.isActivo and not gdh_user.isCesado and is_app_active else "Correcto",
        "Validación Final":  "",
        "Acción Correctiva": "",
    }

def _build_login_map(
    df_login: Optional[pd.DataFrame],
    key_candidates: list,
    val_candidates: list,
) -> dict:
    if df_login is None or df_login.empty:
        return {}
    log = normalizar_df(df_login)
    c_k = _find(log, key_candidates)
    c_v = _find(log, val_candidates)
    if not c_k or not c_v:
        return {}
    return {
        str(r[c_k]).strip().upper(): r[c_v]
        for _, r in log.iterrows()
        if pd.notna(r[c_k])
    }

def _base_row(
    usuario: str,
    gdh_user: GDHUserInfo,
    ult_login: Optional[date],
    is_app_active: bool,
    fecha_ref: date,
    aplicacion: str,
    postCeseService: PostCeseService,
    tipo: str,
    fec_creacion_app: Optional[date],
) -> dict:
    indicadores = _calcular_indicadores(
        gdh_user, ult_login, is_app_active,fec_creacion_app, fecha_ref, aplicacion, postCeseService
    )

    return {
        "Usuario": usuario,
        "Matrícula": gdh_user.matricula if gdh_user.matricula else usuario,
        "Tipo de Cuenta": tipo,
        "Nombre": gdh_user.nombre+" "+gdh_user.apellido_paterno+" "+gdh_user.apellido_materno,
        "Estado": "Activo" if is_app_active else "Bloqueado",
        "Fecha Creación": fec_creacion_app,
        "Ultimo Login": ult_login,
        **indicadores,
    }

def _hoja_exactus(
    df_usr: pd.DataFrame,
    df_login: pd.DataFrame,
    fecha_ref: date,
    gdh_service: GDHUserService,
    accountTypeService: AccountTypeService,
    postCeseService: PostCeseService,
) -> pd.DataFrame:

    usr = normalizar_df(df_usr)
    c_usuario = _find(usr, ["USUARIO"])
    c_nombre = _find(usr, ["NOMBRE"])
    c_activo = _find(usr, ["ACTIVO"])
    c_createdate = _find(usr, ["CREATEDATE"])
    login_map = _build_login_map(
        df_login, ["USUARIO"], ["ULTIMO_LOGUIN"],
    )

    rows = []
    for _, row in usr.iterrows():
        usuario = _safe_upper(row, c_usuario) or ""
        account_info = accountTypeService.get(usuario)
        tipo = account_info.tipo
        matricula = account_info.matricula
        
        if tipo == "servicio" or tipo == "proxy":
            continue

        gdh_user = gdh_service.get_GDH_user(matricula)
        
        if not gdh_user.nombre:
            gdh_user.nombre = str(row[c_nombre]).strip() if c_nombre and pd.notna(row.get(c_nombre)) else ""

        activo_raw = _safe_upper(row, c_activo) or ""
        is_app_active = activo_raw == "S"
        if not is_app_active:
            continue

        fec_creacion = to_date(row[c_createdate]) if c_createdate and pd.notna(row.get(c_createdate)) else None
        ult_login = to_date(login_map.get(usuario))

        rows.append(_base_row(
            usuario, gdh_user, ult_login, is_app_active, fecha_ref,
            "APP_Exactus", postCeseService, tipo, fec_creacion
        ))

    return pd.DataFrame(rows)

def _hoja_sdp(
    df_usuarios: pd.DataFrame,
    df_login: Optional[pd.DataFrame],
    gdh_service: GDHUserService,
    fecha_ref: date,
    accountTypeService: AccountTypeService,
    postCeseService:    PostCeseService,
) -> pd.DataFrame:
    if df_usuarios is None or df_usuarios.empty:
        return pd.DataFrame()

    sdp = normalizar_df(df_usuarios)
    c_usuario = _find(sdp, ["COD_USUARIO", "COD USUARIO"])
    c_est = _find(sdp, ["EST_ACTIVO", "EST ACTIVO"])
    c_creacion = _find(sdp, ["FEC_INCLUSION"])
    login_map = _build_login_map(
        df_login, ["COD_USUARIO", "COD USUARIO"],
        ["FECHALOGIN", "FECHA LOGIN", "FECHA_LOGIN"],
    )

    rows = []
    for _, row in sdp.iterrows():
        usuario      = _safe_upper(row, c_usuario) or ""
        account_info = accountTypeService.get(usuario)
        tipo         = account_info.tipo
        if tipo == "servicio" or tipo == "proxy":
            continue

        gdh_user = gdh_service.get_GDH_user(account_info.matricula)

        est_raw = _safe_upper(row, c_est) or ""
        is_app_active = est_raw == "S"
        if not is_app_active:
            continue

        fec_creacion_app = to_date(row[c_creacion]) if c_creacion and pd.notna(row.get(c_creacion)) else None
        ult_login = to_date(login_map.get(usuario))

        rows.append(_base_row(
            usuario, gdh_user, ult_login, is_app_active, fecha_ref,
            "APP_SDP", postCeseService, tipo, fec_creacion_app
        ))

    return pd.DataFrame(rows)

def _hoja_ad_based(
    df_habilitados: pd.DataFrame,
    ad_service: ADService,
    gdh_service: GDHUserService,
    fecha_ref: date,
    aplicacion: str,
    accountTypeService: AccountTypeService,
    postCeseService: PostCeseService,
) -> pd.DataFrame:
    if df_habilitados is None or df_habilitados.empty:
        return pd.DataFrame()

    hab = normalizar_df(df_habilitados)
    c_sam = _find(hab, ["SAMACCOUNTNAME", "SAM ACCOUNT NAME"])

    rows = []
    for _, row in hab.iterrows():
        usuario = _safe_upper(row, c_sam) or ""
        if not usuario:
            continue

        account_info = accountTypeService.get(usuario)
        tipo = account_info.tipo
        if tipo == "servicio" or tipo == "proxy":
            continue

        gdh_user = gdh_service.get_GDH_user(account_info.matricula)
        ad_user = ad_service.get_AD_user(usuario)
 
        indicadores = _calcular_indicadores(
            gdh_user, ad_user.fecha_ult_login, True,ad_user.fecha_creacion, fecha_ref, aplicacion, postCeseService
        )
        rows.append({
            "Usuario": usuario,
            "Matrícula": gdh_user.matricula,
            "Tipo de Cuenta": tipo,
            "Nombre": gdh_user.nombre + " "+gdh_user.apellido_paterno+" "+gdh_user.apellido_materno,
            "Estado": "Activo",
            "Fecha Creación AD": ad_user.fecha_creacion,
            "Ultimo Login AD": ad_user.fecha_ult_login,
            **indicadores,
        })

    return pd.DataFrame(rows)

def generar_reporte_hallazgos_aplicaciones_criticas(
    df_usr_exactus: pd.DataFrame,
    df_login_exactus: pd.DataFrame,
    df_sdp_usuarios: pd.DataFrame,
    df_sdp_login: pd.DataFrame,
    df_npac_habilitados: pd.DataFrame,
    df_sit_habilitados: pd.DataFrame,
    fecha_ref: date,
    accountTypeService: AccountTypeService,
    postCeseService: PostCeseService,
) -> io.BytesIO:

    ad_service = ADService()
    gdh_service = GDHUserService()

    sheets = [
        (
            "App Exactus",
            _hoja_exactus(df_usr_exactus, df_login_exactus, fecha_ref, gdh_service, accountTypeService, postCeseService),
            DATE_COLS_APP,
        ),
        (
            "App SDP",
            _hoja_sdp(df_sdp_usuarios, df_sdp_login, gdh_service, fecha_ref, accountTypeService, postCeseService),
            DATE_COLS_APP,
        ),
        (
            "App SIT",
            _hoja_ad_based(df_sit_habilitados, ad_service, gdh_service, fecha_ref, "APP_SIT", accountTypeService, postCeseService),
            DATE_COLS_AD,
        ),
        (
            "App NPAC",
            _hoja_ad_based(df_npac_habilitados, ad_service, gdh_service, fecha_ref, "APP_NPAC", accountTypeService, postCeseService),
            DATE_COLS_AD,
        ),
    ]

    wb = _crear_wb_vacio()
    for name, df, date_cols in sheets:
        _df_to_sheet(wb, name, df, date_cols=date_cols)

    return wb_to_buffer(wb)
