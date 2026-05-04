from datetime import date
from services.post_cese_service import PostCeseService
from services.account_type_service import AccountTypeService
from services.ad_service import ADService
from services.gdh_service import GDHUserService

def generar_reporte_hallazgos_ad(fecha_ref: date) -> list[dict]:
    accountTypeService = AccountTypeService()
    postCeseService = PostCeseService()
    ad_service = ADService()
    gdh_service = GDHUserService()

    rows = []

    for userAd in ad_service.get_all_users_info():
        user = userAd.usuario
        nombre = userAd.nombre
        fec_crea = userAd.fecha_creacion
        fec_blq  = userAd.fecha_cambio
        ult_log  = userAd.fecha_ult_login

        info = accountTypeService.get(user)
        tipo = info.tipo
        mat_final = info.matricula

        if tipo == "servicio":
            continue

        user_gdh = gdh_service.get_GDH_user(mat_final)

        fecha_cese = user_gdh.fecha_cese

        #Sin Uso > 90d
        if not userAd.isActivo:
            sin_uso = "Correcto"
        elif fec_crea and (fecha_ref - fec_crea).days <= 30:
            sin_uso = "Correcto"
        elif ult_log and (fecha_ref - ult_log).days <= 90:
            sin_uso = "Correcto"
        else:
            sin_uso = "Incorrecto"

        #Bloqueado > 30d
        blq30 = "Correcto"
        if not userAd.isActivo and user_gdh.isCesado:
            if not fec_blq or (fecha_ref - fec_blq).days > 30:
                blq30 = "Incorrecto"

        #estados y actividad
        cesado_activo  = "Incorrecto" if (userAd.isActivo and user_gdh.isCesado) else "Correcto"
        actividad_post = "Incorrecto" if postCeseService.es_post_cese(mat_final, "Active_Directory",fecha_cese, ult_log) else "Correcto"
        sin_sustento = "Incorrecto" if userAd.isActivo and not user_gdh.isCesado and not user_gdh.isActivo else "Correcto"

        rows.append({
            "Usuario": user,
            "Matricula": mat_final,
            "Tipo de Cuenta": tipo,
            "Nombre": nombre,
            "Unidad organizativa": user_gdh.u_organizativa,
            "Fecha Creación": str(fec_crea) if fec_crea else None,
            "Fecha Bloqueo": str(fec_blq) if fec_blq else None,
            "Ultimo Login": str(ult_log) if ult_log else None,
            "activoGDH": "Si" if user_gdh.isActivo else "No",
            "cesadoGDH": "Si" if user_gdh.isCesado else "No",
            "Estado": "Activo" if userAd.isActivo else "Bloqueado",
            "Fecha Cese": str(fecha_cese) if fecha_cese else None,
            "sinUso>90d": sin_uso,
            "bloqueado>30d": blq30,
            "cesadoActivo": cesado_activo,
            "actividadPostCese": actividad_post,
            "Sin Sustento": sin_sustento,
        })

    return rows
