import io
import pandas as pd
from datetime import date
from dataclasses import dataclass, field
from typing import Optional

from core.normalizer import normalizar_df
from core.excel_writer import _crear_wb_vacio, _df_to_sheet, wb_to_buffer
from core.post_cese_service import PostCeseService
from core.account_type_service import AccountTypeService
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

def _full_name(row, c_nom, c_ap, c_am) -> str:
    parts = [
        str(row[c]).strip()
        for c in (c_nom, c_ap, c_am)
        if c and pd.notna(row.get(c))
    ]
    return " ".join(filter(None, parts))

@dataclass
class GdhContext:
    activos_set: set  = field(default_factory=set)
    cesados_set: set  = field(default_factory=set)
    nombre_map: dict = field(default_factory=dict)
    fecha_cese_map: dict = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        df_activos: Optional[pd.DataFrame],
        df_cesados: Optional[pd.DataFrame],
    ) -> "GdhContext":
        ctx = cls()

        if df_activos is not None and not df_activos.empty:
            act   = normalizar_df(df_activos)
            c_id  = _find(act, ["ID SISTEMA", "ID_SISTEMA"])
            c_nom = _find(act, ["NOMBRES"])
            c_ap  = _find(act, ["APELLIDO PATERNO"])
            c_am  = _find(act, ["APELLIDO MATERNO"])
            if c_id:
                for _, r in act.iterrows():
                    k = _safe_upper(r, c_id)
                    if k:
                        ctx.activos_set.add(k)
                        ctx.nombre_map.setdefault(k, _full_name(r, c_nom, c_ap, c_am))

        if df_cesados is not None and not df_cesados.empty:
            ces   = normalizar_df(df_cesados)
            c_id  = _find(ces, ["ID SISTEMA", "ID_SISTEMA"])
            c_nom = _find(ces, ["NOMBRES"])
            c_ap  = _find(ces, ["APELLIDO PATERNO"])
            c_am  = _find(ces, ["APELLIDO MATERNO"])
            c_fec = _find(ces, ["FECHA"])
            if c_id:
                for _, r in ces.iterrows():
                    k = _safe_upper(r, c_id)
                    if k:
                        ctx.cesados_set.add(k)
                        ctx.nombre_map.setdefault(k, _full_name(r, c_nom, c_ap, c_am))
                        ctx.fecha_cese_map[k] = to_date(r[c_fec]) if c_fec else None

        return ctx

def _calcular_indicadores(
    usuario:            str,
    estado:             str,
    tipo:               str,
    fec_creacion:       Optional[date],
    ult_login:          Optional[date],
    ctx:                GdhContext,
    fecha_ref:          date,
    aplicacion:         str,
    postCeseService:    PostCeseService,
) -> dict:
    activo_gdh = "si" if usuario in ctx.activos_set else "no"
    cesado_gdh = "si" if usuario in ctx.cesados_set else "no"
    fecha_cese = ctx.fecha_cese_map.get(usuario) if cesado_gdh == "si" else None

    es_activo  = estado == "Activo"

    if not es_activo:
        sin_uso = "CORRECTO"
    elif fec_creacion and (fecha_ref - fec_creacion).days <= 90:
        sin_uso = "CORRECTO"
    elif ult_login and (fecha_ref - ult_login).days <= 90:
        sin_uso = "CORRECTO"
    else:
        sin_uso = "INCORRECTO"

    cesado_activo = "INCORRECTO" if es_activo and cesado_gdh == "si" else "CORRECTO"

    actividad_post = (
        "INCORRECTO"
        if postCeseService.es_post_cese(usuario, aplicacion, fecha_cese, ult_login)
        else "CORRECTO"
    )

    sin_sustento = (
        "INCORRECTO"
        if es_activo and activo_gdh == "no" and cesado_gdh == "no"
        else "CORRECTO"
    )

    return {
        "activoGDH":         activo_gdh,
        "cesadoGDH":         cesado_gdh,
        "Fecha Cese":        fecha_cese,
        "sinUso>90d":        sin_uso,
        "cesadoActivo":      cesado_activo,
        "actividadPostCese": actividad_post,
        "Sin Sustento":      sin_sustento,
        "Validación Final":  "",
        "Acción Correctiva": "",
    }

def _build_login_map(
    df_login:       Optional[pd.DataFrame],
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

def _build_ad_maps(df_ad: Optional[pd.DataFrame]) -> tuple[dict, dict]:
    creacion_map: dict = {}
    login_map:    dict = {}
    if df_ad is None or df_ad.empty:
        return creacion_map, login_map
    ad    = normalizar_df(df_ad)
    c_sam = _find(ad, ["SAMACCOUNTNAME", "SAM ACCOUNT NAME"])
    c_cre = _find(ad, ["WHENCREATED", "WHEN CREATED"])
    c_log = _find(ad, ["LASTLOGON", "LASTLOGONDATE", "LAST LOGON"])
    if not c_sam:
        return creacion_map, login_map
    for _, r in ad.iterrows():
        k = _safe_upper(r, c_sam)
        if k:
            if c_cre:
                creacion_map[k] = to_date(r[c_cre]) if pd.notna(r.get(c_cre)) else None
            if c_log:
                login_map[k]    = to_date(r[c_log]) if pd.notna(r.get(c_log)) else None
    return creacion_map, login_map

def _base_row(
    usuario:            str,
    matricula:          str,
    tipo:               str,
    nombre:             str,
    estado:             str,
    fec_creacion:       Optional[date],
    ult_login:          Optional[date],
    ctx:                GdhContext,
    fecha_ref:          date,
    aplicacion:         str,
    postCeseService:    PostCeseService,
) -> dict:
    indicadores = _calcular_indicadores(
        usuario, estado, tipo, fec_creacion, ult_login,
        ctx, fecha_ref, aplicacion, postCeseService,
    )
    return {
        "Usuario":        usuario,
        "Matrícula":      matricula,
        "Tipo de Cuenta": tipo,
        "Nombre":         nombre,
        "Estado":         estado,
        "Fecha Creación": fec_creacion,
        "Ultimo Login":   ult_login,
        **indicadores,
    }

def _hoja_exactus(
    df_usr:             pd.DataFrame,
    df_login:           pd.DataFrame,
    ctx:                GdhContext,
    fecha_ref:          date,
    accountTypeService: AccountTypeService,
    postCeseService:    PostCeseService,
) -> pd.DataFrame:

    usr = normalizar_df(df_usr)
    c_usuario    = _find(usr, ["USUARIO"])
    c_nombre     = _find(usr, ["NOMBRE"])
    c_activo     = _find(usr, ["ACTIVO"])
    c_createdate = _find(usr, ["CREATEDATE"])
    login_map    = _build_login_map(
        df_login, ["USUARIO"], ["ULTIMO_LOGUIN"],
    )

    rows = []
    for _, row in usr.iterrows():
        usuario      = _safe_upper(row, c_usuario) or ""
        account_info = accountTypeService.get(usuario)
        tipo         = account_info.tipo
        matricula    = account_info.matricula
        
        if tipo == "servicio" or tipo == "proxy":
            continue

        nombre       = str(row[c_nombre]).strip() if c_nombre and pd.notna(row.get(c_nombre)) else ""
        activo_raw   = _safe_upper(row, c_activo) or ""
        estado       = "Activo" if activo_raw == "S" else ("Bloqueado" if activo_raw == "N" else activo_raw)
        fec_creacion = to_date(row[c_createdate]) if c_createdate and pd.notna(row.get(c_createdate)) else None
        ult_login    = to_date(login_map.get(usuario))

        rows.append(_base_row(
            usuario, matricula, tipo, nombre, estado,
            fec_creacion, ult_login, ctx, fecha_ref,
            "APP_Exactus", postCeseService,
        ))

    return pd.DataFrame(rows)

def _hoja_sdp(
    df_usuarios:        pd.DataFrame,
    df_login:           Optional[pd.DataFrame],
    ctx:                GdhContext,
    fecha_ref:          date,
    accountTypeService: AccountTypeService,
    postCeseService:    PostCeseService,
) -> pd.DataFrame:
    if df_usuarios is None or df_usuarios.empty:
        return pd.DataFrame()

    sdp        = normalizar_df(df_usuarios)
    c_usuario  = _find(sdp, ["COD_USUARIO", "COD USUARIO"])
    c_est      = _find(sdp, ["EST_ACTIVO", "EST ACTIVO"])
    c_creacion = _find(sdp, ["FEC_INCLUSION"])
    login_map  = _build_login_map(
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

        matricula    = account_info.matricula
        est_raw      = _safe_upper(row, c_est) or ""
        estado       = "Activo" if est_raw == "S" else "Bloqueado"
        fec_creacion = to_date(row[c_creacion]) if c_creacion and pd.notna(row.get(c_creacion)) else None
        ult_login    = to_date(login_map.get(usuario))
        nombre       = ctx.nombre_map.get(usuario, "")

        rows.append(_base_row(
            usuario, matricula, tipo, nombre, estado,
            fec_creacion, ult_login, ctx, fecha_ref,
            "APP_SDP", postCeseService,
        ))

    return pd.DataFrame(rows)

def _hoja_ad_based(
    df_habilitados: pd.DataFrame,
    df_ad_prima: Optional[pd.DataFrame],
    ctx: GdhContext,
    fecha_ref: date,
    aplicacion: str,
    accountTypeService: AccountTypeService,
    postCeseService: PostCeseService,
) -> pd.DataFrame:
    if df_habilitados is None or df_habilitados.empty:
        return pd.DataFrame()

    hab   = normalizar_df(df_habilitados)
    c_sam = _find(hab, ["SAMACCOUNTNAME", "SAM ACCOUNT NAME"])

    ad_creacion_map, ad_login_map = _build_ad_maps(df_ad_prima)

    rows = []
    for _, row in hab.iterrows():
        usuario = _safe_upper(row, c_sam) or ""
        if not usuario:
            continue

        account_info = accountTypeService.get(usuario)
        tipo         = account_info.tipo
        if tipo == "servicio" or tipo == "proxy":
            continue

        matricula    = account_info.matricula
        fec_creacion = ad_creacion_map.get(usuario)
        ult_login    = ad_login_map.get(usuario)
        nombre       = ctx.nombre_map.get(usuario, "")

        indicadores = _calcular_indicadores(
            usuario, "Activo", tipo, fec_creacion, ult_login,
            ctx, fecha_ref, aplicacion, postCeseService,
        )
        rows.append({
            "Usuario":           usuario,
            "Matrícula":         matricula,
            "Tipo de Cuenta":    tipo,
            "Nombre":            nombre,
            "Estado":            "Activo",
            "Fecha Creación AD": fec_creacion,
            "Ultimo Login AD":   ult_login,
            **indicadores,
        })

    return pd.DataFrame(rows)

def generar_reporte_hallazgos_aplicaciones_criticas(
    df_usr_exactus:      pd.DataFrame,
    df_login_exactus:    pd.DataFrame,
    df_sdp_usuarios:     pd.DataFrame,
    df_sdp_login:        pd.DataFrame,
    df_npac_habilitados: pd.DataFrame,
    df_sit_habilitados:  pd.DataFrame,
    df_activos_gdh:      pd.DataFrame,
    df_cesados_gdh:      pd.DataFrame,
    df_ad_prima:         pd.DataFrame,
    fecha_ref:           date,
    accountTypeService:  AccountTypeService,
    postCeseService:     PostCeseService,
) -> io.BytesIO:

    ctx = GdhContext.build(df_activos_gdh, df_cesados_gdh)

    sheets = [
        (
            "App Exactus",
            _hoja_exactus(df_usr_exactus, df_login_exactus, ctx, fecha_ref, accountTypeService, postCeseService),
            DATE_COLS_APP,
        ),
        (
            "App SDP",
            _hoja_sdp(df_sdp_usuarios, df_sdp_login, ctx, fecha_ref, accountTypeService, postCeseService),
            DATE_COLS_APP,
        ),
        (
            "App SIT",
            _hoja_ad_based(df_sit_habilitados,  df_ad_prima, ctx, fecha_ref, "APP_SIT",  accountTypeService, postCeseService),
            DATE_COLS_AD,
        ),
        (
            "App NPAC",
            _hoja_ad_based(df_npac_habilitados, df_ad_prima, ctx, fecha_ref, "APP_NPAC", accountTypeService, postCeseService),
            DATE_COLS_AD,
        ),
    ]

    wb = _crear_wb_vacio()
    for name, df, date_cols in sheets:
        _df_to_sheet(wb, name, df, date_cols=date_cols)

    return wb_to_buffer(wb)