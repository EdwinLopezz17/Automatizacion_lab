from services.post_cese_service import PostCeseService
from services.ad_service import ADService
from services.gdh_service import GDHUserService
from services.db_exactus_service import DBExactusService
from services.db_sdp_service import DBSdpService
from services.app_exactus_service import AppExactusService
from services.app_sdp_service import AppSdpService
from services.entra_service import EntraIDService
from services.db_sit_service import DBSitService
from services.app_sit_service import AppSitService
from services.app_npac_service import AppNpacService

def generar_reporte_hallazgos_cesados() -> list[dict]:

    postCeseService = PostCeseService()
    ad_service = ADService()
    gdh_service = GDHUserService()
    db_exactus_service = DBExactusService()
    db_sdp_service = DBSdpService()
    db_sit_service = DBSitService()
    app_sdp_service = AppSdpService()
    app_exactus_service = AppExactusService()
    entra_service = EntraIDService()
    app_sit_service = AppSitService()
    app_npac_service = AppNpacService()

    VAL_CESADO_ACTIVO = ["AD Nipa", "Entra ID", "Usr Exactus", "DB Exactus",
                         "Usr SDP", "DB SDP", "Usr SIT", "DB SIT", "Usr NPAC"]

    rows = []
    for userCesado in gdh_service.get_cesados_GDH_user():
        matricula = userCesado.matricula
        ad_user = ad_service.get_AD_user(matricula)
        entra_user = entra_service.get_by_mail(ad_user.correo)
        db_sit_user = db_sit_service.get_DB_Sit_user(matricula)

        app_exactus_user = app_exactus_service.get_UserAppExactus(matricula)
        app_sdp_user = app_sdp_service.get_UserAppSdp(matricula)
        app_sit_user = app_sit_service.get_app_sit_user(matricula)
        app_npac_user = app_npac_service.get_app_npac_user(matricula)

        db_sdp_user = db_sdp_service.get_UserDBSdp(matricula)
        db_exa_user = db_exactus_service.get_UserDBExactus(matricula)

        postCeseADNipa = postCeseService.es_post_cese(matricula, "Active_Directory", userCesado.fecha_cese, ad_user.fecha_ult_login)
        postCeseEntraID = postCeseService.es_post_cese(matricula, "APP_ENTRAID", userCesado.fecha_cese, entra_user.ultimo_login)
        postCeseAppExa = postCeseService.es_post_cese(matricula, "APP_Exactus", userCesado.fecha_cese, app_exactus_user.fecha_login)
        postCeseDBExa = postCeseService.es_post_cese(matricula, "DB_EXACTUS", userCesado.fecha_cese, db_exa_user.fecha_login)
        postCeseAppSDP = postCeseService.es_post_cese(matricula, "APP_SDP", userCesado.fecha_cese, app_sdp_user.fecha_login)
        postCeseDBSDP = postCeseService.es_post_cese(matricula, "DB_SDP", userCesado.fecha_cese, db_sdp_user.fecha_login)
        postCeseDBSIT = postCeseService.es_post_cese(matricula, "DB_SIT", userCesado.fecha_cese, db_sit_user.fecha_ult_login)

        r = {
            "Matricula": matricula,
            "Nombre": f"{userCesado.nombre} {userCesado.apellido_paterno} {userCesado.apellido_materno}",
            "Unidad organizativa": userCesado.u_organizativa,
            "Fecha de Cese": userCesado.fecha_cese if userCesado.fecha_cese else None,
            "AD Nipa": "Incorrecto" if ad_user.isActivo else "Correcto",
            "Ultimo Login AD Nipa": ad_user.fecha_ult_login if ad_user.fecha_ult_login else None,
            "PostCese AD Nipa": "Incorrecto" if postCeseADNipa else "Correcto",
            "Entra ID": "Incorrecto" if entra_user.account_enabled else "Correcto",
            "Entra ID Ultimo Login": entra_user.ultimo_login if entra_user.ultimo_login else None,
            "PostCese Entra ID": "Incorrecto" if postCeseEntraID else "Correcto",
            "Usr Exactus": "Incorrecto" if app_exactus_user.isActivo else "Correcto",
            "Usr Exactus Ultimo Login": app_exactus_user.fecha_login if app_exactus_user.fecha_login else None,
            "PostCese Exactus App": "Incorrecto" if postCeseAppExa else "Correcto",
            "DB Exactus": "Incorrecto" if db_exa_user.isActivo else "Correcto",
            "DB Exactus Ultimo Login": db_exa_user.fecha_login if db_exa_user.fecha_login else None,
            "PostCese DB Exactus": "Incorrecto" if postCeseDBExa else "Correcto",
            "Usr SDP": "Incorrecto" if app_sdp_user.isActivo else "Correcto",
            "Usr SDP Ultimo Login": app_sdp_user.fecha_login if app_sdp_user.fecha_login else None,
            "PostCese SDP App": "Incorrecto" if postCeseAppSDP else "Correcto",
            "DB SDP": "Incorrecto" if db_sdp_user.isActivo else "Correcto",
            "DB SDP Ultimo Login": db_sdp_user.fecha_login if db_sdp_user.fecha_login else None,
            "PostCese DB SDP": "Incorrecto" if postCeseDBSDP else "Correcto",
            "DB SIT": "Incorrecto" if db_sit_user.isActivo else "Correcto",
            "DB SIT Ultimo Login": db_sit_user.fecha_ult_login if db_sit_user.fecha_ult_login else None,
            "PostCese DB SIT": "Incorrecto" if postCeseDBSIT else "Correcto",
            "Usr NPAC": "Incorrecto" if app_sit_user.isActivo else "Correcto",
            "Usr SIT": "Incorrecto" if app_npac_user.isActivo else "Correcto",
        }

        r["Validación Cesado Activo"] = "Incorrecto" if any(r.get(c) == "Incorrecto" for c in VAL_CESADO_ACTIVO) else "Correcto"
        r["Validación Post Cese"] = "Incorrecto" if any([
            postCeseADNipa, postCeseEntraID, postCeseAppExa, postCeseDBExa,
            postCeseAppSDP, postCeseDBSDP, postCeseDBSIT,
        ]) else "Correcto"

        rows.append(r)

    return rows