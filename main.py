import sys
import traceback

from datetime import date
from pathlib import Path
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from typing import List

from core.file_reader import read_excel
from reports.hallazgos_cesados_v2 import generar_reporte_hallazgos_cesados
from reports.hallazgos_aplicaciones_criticas import generar_reporte_hallazgos_aplicaciones_criticas
from reports.hallazgos_entra_id import generar_reporte_hallazgos_entra_id
from core.account_type_service import AccountTypeService
from core.post_cese_service import PostCeseService
from routers import historico
import services

app = FastAPI(title="Auditoría de Accesos API", version="-.-.-")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(historico.router)

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/reporte/hallazgos-base-datos")
async def reporte_hallazgos_base_datos(
    activos_gdh: UploadFile = File(...),
    cesados_gdh: UploadFile = File(...),
    users_db_sdp: UploadFile = File(...),
    users_db_sdp_login: UploadFile = File(...),
    users_db_exactus: UploadFile = File(None),
    users_db_exactus_login: UploadFile = File(None),
    users_db_sit: UploadFile = File(None),
    fecha_ref: str = Form(""),
):
    try:
        fref = date.fromisoformat(fecha_ref) if fecha_ref else date.today()
        
        postCeseService = PostCeseService()
        accountTypeService = AccountTypeService()

        postCeseService.cargar_desde_db()
        accountTypeService.cargar_desde_db()

        df_gdh     = read_excel(activos_gdh)
        df_cesados = read_excel(cesados_gdh)
        df_sdp     = read_excel(users_db_sdp)
        df_sdp_log = read_excel(users_db_sdp_login)
        df_exa     = read_excel(users_db_exactus)       if (users_db_exactus      and users_db_exactus.filename)      else None
        df_exa_log = read_excel(users_db_exactus_login) if (users_db_exactus_login and users_db_exactus_login.filename) else None
        df_sit     = read_excel(users_db_sit)           if (users_db_sit           and users_db_sit.filename)           else None

        buf = services.generar_reporte_hallazgos_base_datos(
            df_gdh=df_gdh, df_cesados=df_cesados,
            df_sdp=df_sdp, df_sdp_login=df_sdp_log,
            df_exactus=df_exa, df_exactus_login=df_exa_log,
            df_sit=df_sit,
            fecha_ref=fref,
            accountTypeService=accountTypeService,
            postCeseService=postCeseService,
        )
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Hallazgos Base de Datos.xlsx"'},
    )

@app.post("/reporte/hallazgos-ad")
async def reporte_hallazgos_ad(
    fecha_ref: str = Form(""),
):
    try:
        fref = date.fromisoformat(fecha_ref) if fecha_ref else date.today()

        postCeseService = PostCeseService()
        accountTypeService = AccountTypeService()

        postCeseService.cargar_desde_db()
        accountTypeService.cargar_desde_db()
        
        buf = services.generar_reporte_hallazgos_ad(
            fecha_ref=fref,
            accountTypeService=accountTypeService,
            postCeseService=postCeseService,

        )
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Hallazgos Active Directory.xlsx"'},
    )

@app.post("/reporte/hallazgos-cesados")
async def reporte_hallazgos_cesados(
    cesados_gdh:            UploadFile = File(...),
    users_db_sit:           UploadFile = File(None),
    users_db_sdp:           UploadFile = File(...),
    users_db_sdp_login:     UploadFile = File(...),
    users_db_exactus:       UploadFile = File(None),
    users_db_exactus_login: UploadFile = File(None),
    ad_prima:               UploadFile = File(...),
    usr_exactus:            UploadFile = File(...),
    login_exactus:          UploadFile = File(...),
    sit_habilitados:        UploadFile = File(...),
    npac_habilitados:       UploadFile = File(...),
    sdp_usuarios:           UploadFile = File(...),
    sdp_login:              UploadFile = File(...),
    entra_id_files:         List[UploadFile] = File(...),
    usuarios_entra_id:      UploadFile = File(None),
):
    try:

        postCeseService = PostCeseService()
        accountTypeService = AccountTypeService()

        postCeseService.cargar_desde_db()
        accountTypeService.cargar_desde_db()

        buf = generar_reporte_hallazgos_cesados(
            df_cesados            = read_excel(cesados_gdh),
            df_usr_exactus        = read_excel(usr_exactus),
            df_login_exactus      = read_excel(login_exactus),
            df_sit_hab            = read_excel(sit_habilitados),
            df_npac_hab           = read_excel(npac_habilitados),
            df_sdp_usr            = read_excel(sdp_usuarios),
            df_sdp_login          = read_excel(sdp_login),
            df_db_sit             = read_excel(users_db_sit)           if (users_db_sit           and users_db_sit.filename)           else None,
            df_db_sdp             = read_excel(users_db_sdp),
            df_db_sdp_login       = read_excel(users_db_sdp_login),
            df_db_exactus         = read_excel(users_db_exactus)       if (users_db_exactus       and users_db_exactus.filename)       else None,
            df_db_exactus_login   = read_excel(users_db_exactus_login) if (users_db_exactus_login and users_db_exactus_login.filename) else None,
            df_ad_prima           = read_excel(ad_prima),
            dfs_entra_id          = [read_excel(f) for f in entra_id_files if f and f.filename],
            df_usuarios_entra_id  = read_excel(usuarios_entra_id) if (usuarios_entra_id and usuarios_entra_id.filename) else None,
            accountTypeService=accountTypeService,
            postCeseService=postCeseService,
        )
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Hallazgos Cesados.xlsx"'},
    )

@app.post("/reporte/hallazgos-aplicaciones-criticas")
async def reporte_hallazgos_aplicaciones_criticas(
    usr_exactus:            UploadFile = File(...),
    login_exactus:          UploadFile = File(...),
    sdp_usuarios:           UploadFile = File(...),
    sdp_login:              UploadFile = File(...),
    npac_habilitados:       UploadFile = File(...),
    sit_habilitados:        UploadFile = File(...),
    activos_gdh:            UploadFile = File(...),
    cesados_gdh:            UploadFile = File(...),
    ad_prima:               UploadFile = File(...),
    fecha_ref:              str        = Form(""),
):
    try:
        fref = date.fromisoformat(fecha_ref) if fecha_ref else date.today()
        
        postCeseService = PostCeseService()
        accountTypeService = AccountTypeService()

        postCeseService.cargar_desde_db()
        accountTypeService.cargar_desde_db()


        buf = generar_reporte_hallazgos_aplicaciones_criticas(
            df_usr_exactus      = read_excel(usr_exactus),
            df_login_exactus    = read_excel(login_exactus),
            df_sdp_usuarios     = read_excel(sdp_usuarios),
            df_sdp_login        = read_excel(sdp_login),
            df_npac_habilitados = read_excel(npac_habilitados),
            df_sit_habilitados  = read_excel(sit_habilitados),
            df_activos_gdh      = read_excel(activos_gdh),
            df_cesados_gdh      = read_excel(cesados_gdh),
            df_ad_prima         = read_excel(ad_prima),
            fecha_ref           = fref,
            accountTypeService=accountTypeService,
            postCeseService=postCeseService,
        )
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Hallazgos Aplicaciones Criticas.xlsx"'},
    )

@app.post("/reporte/hallazgos-entra-id")
async def reporte_hallazgos_entra_id(
    activos_gdh: UploadFile = File(...),
    cesados_gdh: UploadFile = File(...),
    ad_prima: UploadFile = File(...),
    usuarios_entra_id: UploadFile = File(...),
):
    try:
        postCeseService = PostCeseService()
        accountTypeService = AccountTypeService()

        postCeseService.cargar_desde_db()
        accountTypeService.cargar_desde_db()

        buf = generar_reporte_hallazgos_entra_id(
            df_entra_id    = read_excel(usuarios_entra_id),
            df_activos_gdh = read_excel(activos_gdh),
            df_cesados_gdh = read_excel(cesados_gdh),
            df_ad_prima    = read_excel(ad_prima),
            postCeseService=postCeseService,
            accountTypeService=accountTypeService,
        )
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Hallazgos EntraID.xlsx"'},
    )

