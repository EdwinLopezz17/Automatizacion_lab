import io
import pandas as pd
from datetime import date
from core.normalizer import normalizar_df
from core.excel_writer import _crear_wb_vacio, _df_to_sheet, wb_to_buffer
from core.post_cese_service import PostCeseService
from core.account_type_service import AccountTypeService
from core.ad_service import ADService
from core.utils import to_date

def _find(df, candidates):
    up = {str(c).strip().upper(): c for c in df.columns}
    for c in candidates:
        if c.strip().upper() in up:
            return up[c.strip().upper()]
    return None

def generar_reporte_hallazgos_ad(
    df_gdh: pd.DataFrame,
    df_cesados: pd.DataFrame,
    fecha_ref: date,
    accountTypeService: AccountTypeService,
    postCeseService: PostCeseService
) -> io.BytesIO:

    ad_service = ADService()

    gdh = normalizar_df(df_gdh)
    ces = normalizar_df(df_cesados)

    gdh_id  = _find(gdh, ["ID SISTEMA"])
    gdh_set = {str(r[gdh_id]).strip().upper() for _, r in gdh.iterrows()} if gdh_id else set()

    ces_id  = _find(ces, ["ID SISTEMA"])
    ces_fec = _find(ces, ["FECHA"])
    ces_set = set()
    ces_map = {}
    if ces_id:
        for _, r in ces.iterrows():
            k = str(r[ces_id]).strip().upper()
            ces_set.add(k)
            ces_map[k] = to_date(r[ces_fec]) if ces_fec else None


    rows = []

    for userAd in ad_service.get_all_users_info():
        user = userAd.usuario
        nombre = userAd.nombre
        estado  = "Activo" if userAd.isActivo else "Bloqueado"
        fec_crea = userAd.fecha_creacion
        fec_blq  = userAd.fecha_cambio
        ult_log  = userAd.fecha_ult_login

        info = accountTypeService.get(user)
        tipo = info.tipo
        mat_final = info.matricula

        if tipo == "servicio":
            continue

        activo_gdh = "si" if mat_final in gdh_set else "no"
        is_cesado  = "si" if mat_final in ces_set else "no"
        fecha_cese = ces_map.get(mat_final) if is_cesado == "si" else None

        es_medible = tipo in ("usuario", "cuenta pa")

        #Sin Uso > 90d
        if not es_medible or estado == "Bloqueado":
            sin_uso = "Correcto"
        elif fec_crea and (fecha_ref - fec_crea).days <= 30:
            sin_uso = "Correcto"
        elif ult_log and (fecha_ref - ult_log).days <= 90:
            sin_uso = "Correcto"
        else:
            sin_uso = "Incorrecto"

        #Bloqueado > 30d
        blq30 = "Correcto"
        if estado == "Bloqueado" and es_medible and is_cesado == "si":
            if not fec_blq or (fecha_ref - fec_blq).days > 30:
                blq30 = "Incorrecto"

        #estados y actividad
        cesado_activo  = "Incorrecto" if (estado == "Activo" and is_cesado == "si") else "Correcto"
        actividad_post = "Incorrecto" if postCeseService.es_post_cese(mat_final, "Active_Directory",fecha_cese, ult_log) else "Correcto"
        sustento       = "Incorrecto" if (es_medible and estado == "Activo" and activo_gdh == "no" and is_cesado == "no") else "Correcto"

        rows.append({
            "Usuario": user,
            "Matricula": mat_final,
            "Tipo de Cuenta": tipo,
            "Nombre": nombre,
            "Fecha Creación": fec_crea,
            "Fecha Bloqueo": fec_blq,
            "Ultimo Login": ult_log,
            "activoGDH": activo_gdh,
            "cesadoGDH": is_cesado,
            "Estado": estado,
            "Fecha Cese": fecha_cese,
            "sinUso>90d": sin_uso,
            "bloqueado>30d": blq30,
            "cesadoActivo": cesado_activo,
            "actividadPostCese": actividad_post,
            "Sin Sustento": sustento,
        })

    df_out = pd.DataFrame(rows)
    wb = _crear_wb_vacio()
    _df_to_sheet(wb, "Active Directory", df_out)
    return wb_to_buffer(wb)
