from datetime import date
from services.post_cese_service import PostCeseService
from services.account_type_service import AccountTypeService
from services.ad_service import ADService
from services.gdh_service import GDHUserService
from services.entra_service import EntraIDService
from core.utils import sin_uso

def generar_reporte_hallazgos_entra_id(fecha_ref: date) -> list[dict]:
    accountTypeService = AccountTypeService()
    postCeseService = PostCeseService()
    ad_service = ADService()
    ad_service.sincro_entra()

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

        if tipo == "servicio" or not matricula:
            continue

        userGDH = gdh_service.get_GDH_user(matricula)

        cesado_activo = "Incorrecto" if (entra_user.account_enabled and userGDH.isCesado) else "Correcto"
        act_post_cese = ( 
            "Incorrecto" if postCeseService.es_post_cese(matricula, "APP_ENTRAID", userGDH.fecha_cese, entra_user.ultimo_login) else "Correcto"
        )
        sin_sustento  = "Incorrecto" if (entra_user.account_enabled and not userGDH.isCesado and not userGDH.isActivo) else "Correcto"

        rows.append({
            "Upn": entra_user.upn,
            "Correo": entra_user.mail,
            "Matricula (SAM/City)": matricula,
            "Tipo Creación": entra_user.creaction_type,
            "Tipo de Cuenta": tipo,
            "Nombre": entra_user.display_name,
            "Unidad organizativa": userGDH.u_organizativa,
            "Estado": "Activo" if entra_user.account_enabled else "Bloqueado",
            "Fecha Creación": entra_user.created_date_time if entra_user.created_date_time else None,
            "Fecha Ultimo Loguin": entra_user.ultimo_login if entra_user.ultimo_login else None,
            "activoGDH": "Si" if userGDH.isActivo else "No",
            "cesadoGDH": "Si" if userGDH.isCesado else "No",
            "Fecha Cese": userGDH.fecha_cese if userGDH.fecha_cese else None,
            "sinUso>90d": sin_uso(entra_user.account_enabled, entra_user.created_date_time, entra_user.ultimo_login, fecha_ref),
            "cesadoActivo": cesado_activo,
            "actividadPostCese": act_post_cese,
            "Sin Sustento": sin_sustento,
        })

    return rows
