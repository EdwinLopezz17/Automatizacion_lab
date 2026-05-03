import io
import pandas as pd
from datetime import date
from core.excel_writer import _crear_wb_vacio, _df_to_sheet, wb_to_buffer
from services.post_cese_service import PostCeseService
from services.account_type_service import AccountTypeService
from services.gdh_service import GDHUserService
from services.db_exactus_service import DBExactusService
from services.db_sdp_service import DBSdpService
from services.db_sit_service import DBSitService

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

def _construir_hoja_sit(db_sit_srv:DBSitService, fecha_ref: date, gdh_service:GDHUserService,
                        pCeseSrv:PostCeseService, accTypeSrv: AccountTypeService):

    rows = []
    for db_sit_user in db_sit_srv.get_all_DB_Sit_users():
        
        tipo = accTypeSrv.get(db_sit_user.usuario).tipo
        if tipo == "servicio" or tipo == "proxy":
            continue

        mat = accTypeSrv.get(db_sit_user.usuario).matricula

        gdh_user = gdh_service.get_GDH_user(mat)
        nombre = gdh_service.get_full_name(mat)
        fecha_cese = gdh_user.fecha_cese

        #sin uso 90d
        if not db_sit_user.isActivo:
            sin_uso = "Correcto"
        elif db_sit_user.fecha_creacion and (fecha_ref - db_sit_user.fecha_creacion).days <= 90:
            sin_uso = "Correcto"
        elif db_sit_user.fecha_ult_login and (fecha_ref - db_sit_user.fecha_ult_login).days <= 90:
            sin_uso = "Correcto"
        else:
            sin_uso = "Incorrecto"

        #blq30
        if not gdh_user.isCesado or db_sit_user.isActivo:
            blq30 = "Correcto"
        elif db_sit_user.fecha_creacion and (fecha_ref - db_sit_user.fecha_creacion).days <= 30:
            blq30 = "Correcto"
        elif not db_sit_user.fecha_cambio or (fecha_ref - db_sit_user.fecha_cambio).days > 30:
                blq30 = "Incorrecto"
        else:
            blq30 = "Incorrecto"

        cesado_activo  = "Incorrecto" if (db_sit_user.isActivo and gdh_user.isCesado) else "Correcto"
        sin_sustento = "Incorrecto" if (db_sit_user.isActivo and not gdh_user.isCesado and not gdh_user.isActivo) else "Correcto"
        
        rows.append({
            "Usuario": db_sit_user.usuario,
            "Matricula": mat,
            "Tipo de Cuenta": tipo,
            "Nombre": nombre,
            "Estado": "Activo" if db_sit_user.isActivo else "Bloqueado",
            "Fecha Creación": db_sit_user.fecha_creacion,
            "Fecha Bloqueo": db_sit_user.fecha_cambio,
            "Ultimo Login": db_sit_user.fecha_ult_login,
            "activoGDH": "si" if gdh_user.isActivo else "no",
            "cesadoGDH": "si" if gdh_user.isCesado else "no",
            "Fecha Cese": fecha_cese,
            "sinUso>90d": sin_uso,
            "bloqueado>30d": blq30,
            "cesadoActivo": cesado_activo,
            "actividadPostCese": "Incorrecto" if pCeseSrv.es_post_cese(mat, "DB_SIT", fecha_cese, db_sit_user.fecha_ult_login) else "Correcto",
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
    fecha_ref: date,
) -> io.BytesIO:
    
    accountTypeService = AccountTypeService()
    postCeseService = PostCeseService()
    gdh_service = GDHUserService()
    db_sit_service = DBSitService()

    df_hoja_sdp = _construir_hoja_sdp(fecha_ref, gdh_service, postCeseService, accountTypeService, "DB_SDP")
    df_hoja_exactus = _construir_hoja_exactus(fecha_ref, gdh_service, postCeseService, accountTypeService, "DB_EXACTUS")
    df_hoja_sit = _construir_hoja_sit(db_sit_service, fecha_ref, gdh_service, postCeseService, accountTypeService)

    wb = _crear_wb_vacio()
    _df_to_sheet(wb, "DB SDP", df_hoja_sdp)
    if not df_hoja_exactus.empty:
        _df_to_sheet(wb, "DB EXACTUS", df_hoja_exactus)
    if not df_hoja_sit.empty:
        _df_to_sheet(wb, "DB SIT", df_hoja_sit)
    return wb_to_buffer(wb)
