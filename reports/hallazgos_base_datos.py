import io
import pandas as pd
from datetime import date
from core.utils import to_date
from core.normalizer import normalizar_df
from core.excel_writer import _crear_wb_vacio, _df_to_sheet, wb_to_buffer
from services.post_cese_service import PostCeseService
from services.account_type_service import AccountTypeService
from services.gdh_service import GDHUserService
from services.db_exactus_service import DBExactusService
from services.db_sdp_service import DBSdpService


def _find(df, candidates):
    up = {c.upper(): c for c in df.columns}
    for c in candidates:
        if c.upper() in up:
            return up[c.upper()]
    return None

def _construir_hoja_db(
    fecha_ref: date,
    gdh_service: GDHUserService,
    pCeseSrv: PostCeseService,
    accTypeSrv: AccountTypeService,
    aplicacion: str,
    db_service,
    get_users_fn: str,
):
    rows = []
    for db_user in getattr(db_service, get_users_fn)():
        tipo = accTypeSrv.get(db_user.usuario).tipo
        if tipo == "servicio" or tipo == "proxy":
            continue

        mat = accTypeSrv.get(db_user.usuario).matricula
        gdh_user = gdh_service.get_GDH_user(mat)
        nombre = gdh_service.get_full_name(mat)

        # sin uso
        if not db_user.isActivo:
            sin_uso = "Correcto"
        elif db_user.fecha_creacion and (fecha_ref - db_user.fecha_creacion).days <= 90:
            sin_uso = "Correcto"
        elif db_user.fecha_login and (fecha_ref - db_user.fecha_login).days <= 90:
            sin_uso = "Correcto"
        else:
            sin_uso = "Incorrecto"

        # blq30
        blq30 = "Correcto"
        if not db_user.isActivo and gdh_user.isCesado:
            if not db_user.fecha_bloq or (fecha_ref - db_user.fecha_bloq).days > 30:
                blq30 = "Incorrecto"

        cesado_activo = "Incorrecto" if (db_user.isActivo and gdh_user.isCesado) else "Correcto"
        act_post_cese = "Incorrecto" if pCeseSrv.es_post_cese(mat, aplicacion, gdh_user.fecha_cese, db_user.fecha_login) else "Correcto"
        sin_sustento = "Incorrecto" if (db_user.isActivo and not gdh_user.isCesado and not gdh_user.isActivo) else "Correcto"

        rows.append({
            "Usuario": db_user.usuario,
            "Matricula": mat,
            "Tipo de Cuenta": tipo,
            "Nombre": nombre,
            "Estado": "activo" if db_user.isActivo else "bloqueado",
            "Fecha Creación": db_user.fecha_creacion,
            "Fecha Bloqueo": db_user.fecha_bloq,
            "Ultimo Login": db_user.fecha_login,
            "activoGDH": "si" if gdh_user.isActivo else "no",
            "cesadoGDH": "si" if gdh_user.isCesado else "no",
            "Fecha Cese": gdh_user.fecha_cese,
            "sinUso>90d": sin_uso,
            "bloqueado>30d": blq30,
            "cesadoActivo": cesado_activo,
            "actividadPostCese": act_post_cese,
            "Sin Sustento": sin_sustento,
            "Validación Final": "",
            "Acción Correctiva": "",
        })

    return pd.DataFrame(rows).sort_values("Nombre", ignore_index=True)

def _construir_hoja_sit(df_raw, fecha_ref: date, gdh_service:GDHUserService,
                        pCeseSrv:PostCeseService, accTypeSrv: AccountTypeService):
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = normalizar_df(df_raw)

    ln_col = _find(df, ["LOGINNAME"])
    ia_col = _find(df, ["ISACTIVE"])
    cr_col = _find(df, ["CREATED"])
    up_col = _find(df, ["UPDATE"])
    ul_col = _find(df, ["ULTIMOLOGEO"])

    rows = []
    for _, row in df.iterrows():
        raw_login = str(row[ln_col]).strip() if ln_col else ""
        usuario = raw_login.split("\\")[-1].strip().upper() if "\\" in raw_login else raw_login.upper()
        tipo = accTypeSrv.get(usuario).tipo
        if tipo == "servicio" or tipo == "proxy":
            continue

        mat = accTypeSrv.get(usuario).matricula
        ia_raw = str(row[ia_col]).strip().upper() if ia_col else ""
        estado = "activo" if ia_raw == "ACTIVO" else "bloqueado"

        fec_crea = to_date(row[cr_col], "DMA") if cr_col else None
        fec_blq = to_date(row[up_col], "DMA") if up_col else None
        ult_log = to_date(row[ul_col], "DMA") if ul_col else None

        gdh_user = gdh_service.get_GDH_user(mat)
        nombre = gdh_service.get_full_name(mat)
        fecha_cese = gdh_user.fecha_cese

        #sin uso 90d
        if estado == "bloqueado":
            sin_uso = "Correcto"
        elif fec_crea and (fecha_ref - fec_crea).days <= 90:
            sin_uso = "Correcto"
        elif ult_log and (fecha_ref - ult_log).days <= 90:
            sin_uso = "Correcto"
        else:
            sin_uso = "Incorrecto"

        #blq30
        blq30 = "Correcto"
        if estado == "bloqueado":
            if not fec_blq or (fecha_ref - fec_blq).days > 30:
                blq30 = "Incorrecto"

        cesado_activo  = "Incorrecto" if (estado == "activo" and gdh_user.isCesado) else "Correcto"
        sin_sustento = "Incorrecto" if (estado == "activo" and not gdh_user.isCesado and not gdh_user.isActivo) else "Correcto"
        
        rows.append({
            "Usuario": usuario,
            "Matricula": mat,
            "Tipo de Cuenta": tipo,
            "Nombre": nombre,
            "Estado": estado,
            "Fecha Creación": fec_crea,
            "Fecha Bloqueo": fec_blq,
            "Ultimo Login": ult_log,
            "activoGDH": "si" if gdh_user.isActivo else "no",
            "cesadoGDH": "si" if gdh_user.isCesado else "no",
            "Fecha Cese": fecha_cese,
            "sinUso>90d": sin_uso,
            "bloqueado>30d": blq30,
            "cesadoActivo": cesado_activo,
            "actividadPostCese": "Incorrecto" if pCeseSrv.es_post_cese(mat, "DB_SIT", fecha_cese, ult_log) else "Correcto",
            "Sin Sustento": sin_sustento,
            "Validación Final": "",
            "Acción Correctiva": "",
        })

    return pd.DataFrame(rows).sort_values("Nombre", ignore_index=True)

def _construir_hoja_sdp(fecha_ref, gdh_service, pCeseSrv, accTypeSrv, aplicacion):
    return _construir_hoja_db(
        fecha_ref, gdh_service, pCeseSrv, accTypeSrv, aplicacion,
        db_service=DBSdpService(),
        get_users_fn="get_all_UsersDBsdp",
    )

def _construir_hoja_exactus(fecha_ref, gdh_service, pCeseSrv, accTypeSrv, aplicacion):
    return _construir_hoja_db(
        fecha_ref, gdh_service, pCeseSrv, accTypeSrv, aplicacion,
        db_service=DBExactusService(),
        get_users_fn="get_all_UsersDBExactus",
    )

def generar_reporte_hallazgos_base_datos(
    df_sit,
    fecha_ref: date,
) -> io.BytesIO:
    
    accountTypeService = AccountTypeService()
    postCeseService = PostCeseService()
    gdh_service = GDHUserService()

    df_hoja_sdp = _construir_hoja_sdp(fecha_ref, gdh_service, postCeseService, accountTypeService, "DB_SDP")
    df_hoja_exactus = _construir_hoja_exactus(fecha_ref, gdh_service, postCeseService, accountTypeService, "DB_EXACTUS")
    df_hoja_sit = _construir_hoja_sit(df_sit, fecha_ref, gdh_service, postCeseService, accountTypeService)

    wb = _crear_wb_vacio()
    _df_to_sheet(wb, "DB SDP", df_hoja_sdp)
    if not df_hoja_exactus.empty:
        _df_to_sheet(wb, "DB EXACTUS", df_hoja_exactus)
    if not df_hoja_sit.empty:
        _df_to_sheet(wb, "DB SIT", df_hoja_sit)
    return wb_to_buffer(wb)