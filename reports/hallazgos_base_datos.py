import io
import pandas as pd
from datetime import date
from core.normalizer import normalizar_df
from core.excel_writer import _crear_wb_vacio, _df_to_sheet, wb_to_buffer
from core.post_cese_service import PostCeseService
from core.account_type_service import AccountTypeService
from core.gdh_service import GDHUserService
from core.utils import to_date

def _find(df, candidates):
    up = {c.upper(): c for c in df.columns}
    for c in candidates:
        if c.upper() in up:
            return up[c.upper()]
    return None

def _build_login_map(df_login):
    if df_login is None or df_login.empty:
        return {}
    login = normalizar_df(df_login)
    lg_un = _find(login, ["USERNAME"])
    lg_ts = _find(login, ["MAX(DAS.TIMESTAMP)"])
    if not (lg_un and lg_ts):
        return {}
    return {
        str(r[lg_un]).strip().upper(): to_date(r[lg_ts])
        for _, r in login.iterrows()
    }

def _build_gdh_map(df_gdh):
    gdh = normalizar_df(df_gdh)
    gdh_id  = _find(gdh, ["ID SISTEMA"])
    gdh_nom = _find(gdh, ["NOMBRES"])
    gdh_ap  = _find(gdh, ["APELLIDO PATERNO"])
    gdh_am  = _find(gdh, ["APELLIDO MATERNO"])
    if not gdh_id:
        return {}, set()
    gdh_map, gdh_set = {}, set()
    for _, r in gdh.iterrows():
        k = str(r[gdh_id]).strip().upper()
        gdh_set.add(k)
        gdh_map[k] = " ".join(filter(None, [
            str(r.get(gdh_nom, "")).strip(),
            str(r.get(gdh_ap,  "")).strip(),
            str(r.get(gdh_am,  "")).strip(),
        ]))

    return gdh_map, gdh_set

def _build_ces_map(df_ces):
    ces = normalizar_df(df_ces)
    ces_id  = _find(ces, ["ID SISTEMA"])
    ces_nom = _find(ces, ["NOMBRES"])
    ces_ap  = _find(ces, ["APELLIDO PATERNO"])
    ces_am  = _find(ces, ["APELLIDO MATERNO"])
    ces_fec = _find(ces, ["FECHA"])
    if not ces_id:
        return {}, set()
    ces_map, ces_set = {}, set()
    for _, r in ces.iterrows():
        k = str(r[ces_id]).strip().upper()
        ces_set.add(k)
        ces_map[k] = {
            "nombre": " ".join(filter(None, [
                str(r.get(ces_nom, "")).strip(),
                str(r.get(ces_ap,  "")).strip(),
                str(r.get(ces_am,  "")).strip(),
            ])),
            "fecha_cese": to_date(r[ces_fec]) if ces_fec else None,
        }
    return ces_map, ces_set

def _construir_hoja(df_raw, df_login, fecha_ref: date, gdh_service:GDHUserService,
                    pCeseSrv:PostCeseService, accTypeSrv: AccountTypeService , aplicacion: str):
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = normalizar_df(df_raw)
    login_map = _build_login_map(df_login)

    un_col = _find(df, ["USERNAME"])
    st_col = _find(df, ["ACCOUNT_STATUS"])
    lk_col = _find(df, ["LOCK_DATE"])
    cr_col = _find(df, ["CREATED"])

    rows = []
    for _, row in df.iterrows():
        usuario = str(row[un_col]).strip().upper() if un_col else ""
        tipo = accTypeSrv.get(usuario).tipo
        if tipo == "servicio" or tipo == "proxy":
            continue

        mat = accTypeSrv.get(usuario).matricula
        estado_raw = str(row[st_col]).strip().upper() if st_col else ""
        estado = "bloqueado" if "LOCKED" in estado_raw else "activo"
        fec_blq = to_date(row[lk_col]) if lk_col else None
        fec_crea = to_date(row[cr_col]) if cr_col else None
        ult_log = login_map.get(mat)

        gdh_user = gdh_service.get_GDH_user(mat)
        nombre = gdh_service.get_full_name(mat)
        fecha_cese = gdh_user.fecha_cese

        #sin uso
        if estado == "bloqueado":
            sin_uso = "Correcto"
        elif fec_crea and (fecha_ref - fec_crea).days <= 90:
            sin_uso = "Correcto"
        elif ult_log and (fecha_ref - ult_log).days <= 90:
            sin_uso = "Correcto"
        else:
            sin_uso = "Incorrecto"

        #bl30
        blq30 = "Correcto"
        if estado == "bloqueado" and gdh_user.isCesado:
            if not fec_blq or (fecha_ref - fec_blq).days > 30:
                blq30 = "Incorrecto"

        cesado_activo  = "Incorrecto" if (estado == "activo" and gdh_user.isCesado) else "Correcto"
        sin_sustento = "Incorrecto" if estado == "Activo" and not gdh_user.isCesado and not gdh_user.isActivo else "Correcto"

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
            "actividadPostCese": "Incorrecto" if pCeseSrv.es_post_cese (mat, aplicacion, fecha_cese, ult_log) else "Correcto",
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
            sin_uso = "Inorrecto"

        #blq30
        blq30 = "Correcto"
        if estado == "bloqueado":
            if not fec_blq or (fecha_ref - fec_blq).days > 30:
                blq30 = "Incorrecto"

        cesado_activo  = "Incorrecto" if (estado == "activo" and gdh_user.isCesado) else "Correcto"
        sustento = (
            "Correcto"
            if estado == "activo" and (gdh_user.isCesado or gdh_user.isActivo)
            else "Incorrecto"
        )
        
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
            "Sin Sustento": sustento,
            "Validación Final": "",
            "Acción Correctiva": "",
        })

    return pd.DataFrame(rows).sort_values("Nombre", ignore_index=True)

def generar_reporte_hallazgos_base_datos(
    df_sdp, df_sdp_login,
    df_exactus,
    df_exactus_login,
    df_sit,
    fecha_ref: date,
    accountTypeService: AccountTypeService,
    postCeseService: PostCeseService

) -> io.BytesIO:
    
    gdh_service = GDHUserService()

    df_hoja_sdp = _construir_hoja(df_sdp, df_sdp_login, fecha_ref, gdh_service, postCeseService, accountTypeService, "DB_SDP")
    df_hoja_exactus = _construir_hoja(df_exactus, df_exactus_login, fecha_ref, gdh_service, postCeseService, accountTypeService, "DB_EXACTUS")
    df_hoja_sit = _construir_hoja_sit(df_sit, fecha_ref, gdh_service, postCeseService, accountTypeService)

    wb = _crear_wb_vacio()
    _df_to_sheet(wb, "DB SDP", df_hoja_sdp)
    if not df_hoja_exactus.empty:
        _df_to_sheet(wb, "DB EXACTUS", df_hoja_exactus)
    if not df_hoja_sit.empty:
        _df_to_sheet(wb, "DB SIT", df_hoja_sit)
    return wb_to_buffer(wb)
