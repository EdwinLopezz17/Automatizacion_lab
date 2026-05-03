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
from reports.hallazgos_base_datos import generar_reporte_hallazgos_base_datos
from reports.hallazgos_ad import generar_reporte_hallazgos_ad
from services.account_type_service import AccountTypeService
from services.post_cese_service import PostCeseService
from routers import historico
from routers import entra_login_router

app = FastAPI(title="Auditoría de Accesos API", version="-.-.-")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(historico.router)
app.include_router(entra_login_router.router)

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
    users_db_sit: UploadFile = File(None),
    fecha_ref: str = Form(""),
):
    try:
        fref = date.fromisoformat(fecha_ref) if fecha_ref else date.today()

        df_sit     = read_excel(users_db_sit) if (users_db_sit and users_db_sit.filename) else None

        buf = generar_reporte_hallazgos_base_datos(
            df_sit=df_sit,
            fecha_ref=fref,
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
        
        buf = generar_reporte_hallazgos_ad(
            fecha_ref=fref,
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
    users_db_sit: UploadFile = File(None),
    sit_habilitados: UploadFile = File(...),
    npac_habilitados: UploadFile = File(...),
):
    try:
        buf = generar_reporte_hallazgos_cesados(
            df_sit_hab = read_excel(sit_habilitados),
            df_npac_hab = read_excel(npac_habilitados),
            df_db_sit = read_excel(users_db_sit) if (users_db_sit and users_db_sit.filename) else None,
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
    npac_habilitados: UploadFile = File(...),
    sit_habilitados: UploadFile = File(...),
    fecha_ref: str = Form(""),
):
    try:
        fref = date.fromisoformat(fecha_ref) if fecha_ref else date.today()

        buf = generar_reporte_hallazgos_aplicaciones_criticas(
            df_npac_habilitados = read_excel(npac_habilitados),
            df_sit_habilitados = read_excel(sit_habilitados),
            fecha_ref = fref,
        )
    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Hallazgos Aplicaciones Criticas.xlsx"'},
    )

@app.post("/reporte/hallazgos-entra-id")
async def reporte_hallazgos_entra_id():
    try:
        buf = generar_reporte_hallazgos_entra_id()

    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Hallazgos EntraID.xlsx"'},
    )
