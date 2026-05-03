import io
import pandas as pd
from datetime import date
from typing import Optional

from core.excel_writer import _crear_wb_vacio, _df_to_sheet, wb_to_buffer
from services.post_cese_service import PostCeseService
from services.account_type_service import AccountTypeService
from services.gdh_service import GDHUserService, GDHUserInfo
from services.app_exactus_service import AppExactusService
from services.app_sdp_service import AppSdpService
from services.app_sit_service import AppSitService
from services.app_npac_service import AppNpacService

DATE_COLS_APP = {"Fecha Creación", "Ultimo Login", "Fecha Cese"}
DATE_COLS_AD  = {"Fecha Creación AD", "Ultimo Login AD", "Fecha Cese"}

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
        "Nombre": f"{gdh_user.nombre} {gdh_user.apellido_paterno} {gdh_user.apellido_materno}",
        "Estado": "Activo" if is_app_active else "Bloqueado",
        "Fecha Creación": fec_creacion_app,
        "Ultimo Login": ult_login,
        **indicadores,
    }

def _hoja_exactus(
    app_exactus_service: AppExactusService,
    fecha_ref: date,
    gdh_service: GDHUserService,
    accountTypeService: AccountTypeService,
    postCeseService: PostCeseService,
) -> pd.DataFrame:

    rows = []
    for app_exactus in app_exactus_service.get_all_UsersAppExactus():
        account_info = accountTypeService.get(app_exactus.usuario)
        tipo = account_info.tipo
        matricula = account_info.matricula
        
        if tipo in ("servicio", "proxy") or not app_exactus.isActivo:
            continue

        gdh_user = gdh_service.get_GDH_user(matricula)

        rows.append(_base_row( 
            app_exactus.usuario, gdh_user, app_exactus.fecha_login, app_exactus.isActivo, fecha_ref,
            "APP_EXACTUS", postCeseService, tipo, app_exactus.fecha_creacion
        ))

    return pd.DataFrame(rows)

def _hoja_sdp(
    app_sdp_service: AppSdpService,
    fecha_ref: date,
    gdh_service: GDHUserService,
    accountTypeService: AccountTypeService,
    postCeseService:    PostCeseService,
) -> pd.DataFrame:

    rows = []
    for app_sdp in app_sdp_service.get_all_UsersAppSdp():
        account_info = accountTypeService.get(app_sdp.usuario)
        tipo = account_info.tipo
        if tipo in ("servicio", "proxy") or not app_sdp.isActivo:
            continue

        gdh_user = gdh_service.get_GDH_user(account_info.matricula)

        rows.append(_base_row( 
            app_sdp.usuario, gdh_user, app_sdp.fecha_login, app_sdp.isActivo, fecha_ref,
            "APP_SDP", postCeseService, tipo, app_sdp.fecha_creacion
        ))

    return pd.DataFrame(rows)

def _hoja_app_sit(
    app_sit_service: AppSitService,
    gdh_service: GDHUserService,
    fecha_ref: date,
    aplicacion: str,
    accountTypeService: AccountTypeService,
    postCeseService: PostCeseService,
) -> pd.DataFrame:

    rows = []
    for app_sit_user in app_sit_service.get_app_sit_users():

        account_info = accountTypeService.get(app_sit_user.usuario)
        tipo = account_info.tipo
        if tipo == "servicio" or tipo == "proxy":
            continue

        gdh_user = gdh_service.get_GDH_user(account_info.matricula)

        indicadores = _calcular_indicadores(
            gdh_user, app_sit_user.fecha_ult_login, True,app_sit_user.fecha_creacion, fecha_ref, aplicacion, postCeseService
        )
        rows.append({
            "Usuario": app_sit_user.usuario,
            "Matrícula": gdh_user.matricula,
            "Tipo de Cuenta": tipo,
            "Nombre": gdh_user.nombre + " "+gdh_user.apellido_paterno+" "+gdh_user.apellido_materno,
            "Estado": "Activo",
            "Fecha Creación AD": app_sit_user.fecha_creacion,
            "Ultimo Login AD": app_sit_user.fecha_ult_login,
            **indicadores,
        })

    return pd.DataFrame(rows)

def _hoja_app_npac(
    app_npac_service:AppNpacService,
    gdh_service: GDHUserService,
    fecha_ref: date,
    aplicacion: str,
    accountTypeService: AccountTypeService,
    postCeseService: PostCeseService,
) -> pd.DataFrame:

    rows = []
    for app_npac_user in app_npac_service.get_app_npac_users():

        account_info = accountTypeService.get(app_npac_user.usuario)
        tipo = account_info.tipo
        if tipo == "servicio" or tipo == "proxy":
            continue

        gdh_user = gdh_service.get_GDH_user(account_info.matricula)

        indicadores = _calcular_indicadores(
            gdh_user, app_npac_user.fecha_ult_login, True, app_npac_user.fecha_creacion, fecha_ref, aplicacion, postCeseService
        )
        rows.append({
            "Usuario": app_npac_user.usuario,
            "Matrícula": gdh_user.matricula,
            "Tipo de Cuenta": tipo,
            "Nombre": gdh_user.nombre + " "+gdh_user.apellido_paterno+" "+gdh_user.apellido_materno,
            "Estado": "Activo",
            "Fecha Creación AD": app_npac_user.fecha_creacion,
            "Ultimo Login AD": app_npac_user.fecha_ult_login,
            **indicadores,
        })

    return pd.DataFrame(rows)

def generar_reporte_hallazgos_aplicaciones_criticas(
    fecha_ref: date,
) -> io.BytesIO:

    accountTypeService = AccountTypeService()
    postCeseService = PostCeseService()
    gdh_service = GDHUserService()
    app_sdp_service = AppSdpService()
    app_exactus_service = AppExactusService()
    app_sit_service = AppSitService()
    app_npac_service = AppNpacService()
    
    sheets = [
        (
            "App Exactus",
            _hoja_exactus(app_exactus_service, fecha_ref, gdh_service, accountTypeService, postCeseService),
            DATE_COLS_APP,
        ),
        (
            "App SDP",
            _hoja_sdp(app_sdp_service, fecha_ref, gdh_service, accountTypeService, postCeseService),
            DATE_COLS_APP,
        ),
        (
            "App SIT",
            _hoja_app_sit(app_sit_service, gdh_service, fecha_ref, "APP_SIT", accountTypeService, postCeseService),
            DATE_COLS_AD,
        ),
        (
            "App NPAC",
            _hoja_app_npac(app_npac_service, gdh_service, fecha_ref, "APP_NPAC", accountTypeService, postCeseService),
            DATE_COLS_AD,
        ),
    ]

    wb = _crear_wb_vacio()
    for name, df, date_cols in sheets:
        _df_to_sheet(wb, name, df, date_cols=date_cols)

    return wb_to_buffer(wb)