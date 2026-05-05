from datetime import date
from services.post_cese_service import PostCeseService
from services.account_type_service import AccountTypeService
from services.gdh_service import GDHUserService
from services.db_exactus_service import DBExactusService
from services.db_sdp_service import DBSdpService
from services.db_sit_service import DBSitService
from core.utils import sin_uso

def _construir_filas_db(
    fecha_ref: date,
    gdh_service: GDHUserService,
    pCeseSrv: PostCeseService,
    accTypeSrv: AccountTypeService,
    aplicacion: str,
    db_service,
    get_users_fn: str,
) -> list[dict]:
    rows = []
    for db_user in getattr(db_service, get_users_fn)():
        tipo = accTypeSrv.get(db_user.usuario).tipo
        if tipo == "servicio" or tipo == "proxy":
            continue

        mat = accTypeSrv.get(db_user.usuario).matricula
        gdh_user = gdh_service.get_GDH_user(mat)
        nombre = gdh_service.get_full_name(mat)

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
            "Unidad organizativa":gdh_user.u_organizativa,
            "Estado": "Activo" if db_user.isActivo else "Bloqueado",
            "Fecha Creación": str(db_user.fecha_creacion) if db_user.fecha_creacion else None,
            "Fecha Bloqueo": str(db_user.fecha_bloq) if db_user.fecha_bloq else None,
            "Ultimo Login": str(db_user.fecha_login) if db_user.fecha_login else None,
            "activoGDH": "Si" if gdh_user.isActivo else "No",
            "cesadoGDH": "Si" if gdh_user.isCesado else "No",
            "Fecha Cese": str(gdh_user.fecha_cese) if gdh_user.fecha_cese else None,
            "sinUso>90d": sin_uso(db_user.isActivo, db_user.fecha_creacion, db_user.fecha_login, fecha_ref),
            "bloqueado>30d": blq30,
            "cesadoActivo": cesado_activo,
            "actividadPostCese": act_post_cese,
            "Sin Sustento": sin_sustento,
        })

    return sorted(rows, key=lambda r: r["Nombre"] or "")


def _construir_filas_sit(
    db_sit_srv: DBSitService,
    fecha_ref: date,
    gdh_service: GDHUserService,
    pCeseSrv: PostCeseService,
    accTypeSrv: AccountTypeService,
) -> list[dict]:
    rows = []
    for db_sit_user in db_sit_srv.get_all_DB_Sit_users():
        tipo = accTypeSrv.get(db_sit_user.usuario).tipo
        if tipo == "servicio" or tipo == "proxy":
            continue

        mat = accTypeSrv.get(db_sit_user.usuario).matricula
        gdh_user = gdh_service.get_GDH_user(mat)
        nombre = gdh_service.get_full_name(mat)
        fecha_cese = gdh_user.fecha_cese

        # sin uso 90d
        if not db_sit_user.isActivo:
            sin_uso = "Correcto"
        elif db_sit_user.fecha_creacion and (fecha_ref - db_sit_user.fecha_creacion).days <= 90:
            sin_uso = "Correcto"
        elif db_sit_user.fecha_ult_login and (fecha_ref - db_sit_user.fecha_ult_login).days <= 90:
            sin_uso = "Correcto"
        else:
            sin_uso = "Incorrecto"

        # blq30
        if not gdh_user.isCesado or db_sit_user.isActivo:
            blq30 = "Correcto"
        elif db_sit_user.fecha_creacion and (fecha_ref - db_sit_user.fecha_creacion).days <= 30:
            blq30 = "Correcto"
        elif not db_sit_user.fecha_cambio or (fecha_ref - db_sit_user.fecha_cambio).days > 30:
            blq30 = "Incorrecto"
        else:
            blq30 = "Incorrecto"

        cesado_activo = "Incorrecto" if (db_sit_user.isActivo and gdh_user.isCesado) else "Correcto"
        sin_sustento = "Incorrecto" if (db_sit_user.isActivo and not gdh_user.isCesado and not gdh_user.isActivo) else "Correcto"

        rows.append({
            "Usuario": db_sit_user.usuario,
            "Matricula": mat,
            "Tipo de Cuenta": tipo,
            "Nombre": nombre,
            "Unidad organizativa":gdh_user.u_organizativa,
            "Estado": "Activo" if db_sit_user.isActivo else "Bloqueado",
            "Fecha Creación": str(db_sit_user.fecha_creacion) if db_sit_user.fecha_creacion else None,
            "Fecha Bloqueo": str(db_sit_user.fecha_cambio) if db_sit_user.fecha_cambio else None,
            "Ultimo Login": str(db_sit_user.fecha_ult_login) if db_sit_user.fecha_ult_login else None,
            "activoGDH": "Si" if gdh_user.isActivo else "No",
            "cesadoGDH": "Si" if gdh_user.isCesado else "No",
            "Fecha Cese": str(fecha_cese) if fecha_cese else None,
            "sinUso>90d": sin_uso,
            "bloqueado>30d": blq30,
            "cesadoActivo": cesado_activo,
            "actividadPostCese": "Incorrecto" if pCeseSrv.es_post_cese(mat, "DB_SIT", fecha_cese, db_sit_user.fecha_ult_login) else "Correcto",
            "Sin Sustento": sin_sustento,
        })

    return sorted(rows, key=lambda r: r["Nombre"] or "")

def generar_reporte_hallazgos_base_datos(fecha_ref: date) -> dict[str, list[dict]]:
    accountTypeService = AccountTypeService()
    postCeseService = PostCeseService()
    gdh_service = GDHUserService()
    db_sit_service = DBSitService()

    return {
        "DB_SDP": _construir_filas_db(
            fecha_ref, gdh_service, postCeseService, accountTypeService, "DB_SDP",
            db_service=DBSdpService(),
            get_users_fn="get_all_UsersDBsdp",
        ),
        "DB_EXACTUS": _construir_filas_db(
            fecha_ref, gdh_service, postCeseService, accountTypeService, "DB_EXACTUS",
            db_service=DBExactusService(),
            get_users_fn="get_all_UsersDBExactus",
        ),
        "DB_SIT": _construir_filas_sit(
            db_sit_service, fecha_ref, gdh_service, postCeseService, accountTypeService,
        ),
    }
