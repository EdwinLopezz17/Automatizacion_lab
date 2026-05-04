import sys
import traceback

from datetime import date
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Form

from reports.hallazgos_cesados_v2 import generar_reporte_hallazgos_cesados
from reports.hallazgos_aplicaciones_criticas import generar_reporte_hallazgos_aplicaciones_criticas
from reports.hallazgos_entra_id import generar_reporte_hallazgos_entra_id
from reports.hallazgos_base_datos import generar_reporte_hallazgos_base_datos
from reports.hallazgos_ad import generar_reporte_hallazgos_ad
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
async def reporte_hallazgos_base_datos( fecha_ref: str = Form("")):
    try:
        fref = date.fromisoformat(fecha_ref)

        data = generar_reporte_hallazgos_base_datos(fecha_ref=fref)
        return {"data": data}

    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

@app.post("/reporte/hallazgos-ad")
async def reporte_hallazgos_ad(fecha_ref: str = Form("")):
    try:
        fref = date.fromisoformat(fecha_ref)
        print(f"Fehca detectada para trabajar: {fref}")
        
        data = generar_reporte_hallazgos_ad(fecha_ref=fref)
        return {"data": data}

    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

@app.post("/reporte/hallazgos-cesados")
async def reporte_hallazgos_cesados():
    try:
        data = generar_reporte_hallazgos_cesados()
        return {"data": data}

    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

@app.post("/reporte/hallazgos-aplicaciones-criticas")
async def reporte_hallazgos_aplicaciones_criticas( fecha_ref: str = Form("")):
    try:
        fref = date.fromisoformat(fecha_ref)

        data = generar_reporte_hallazgos_aplicaciones_criticas(fecha_ref=fref)
        return {"data": data}

    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

@app.post("/reporte/hallazgos-entra-id")
async def reporte_hallazgos_entra_id():
    try:
        data = generar_reporte_hallazgos_entra_id()
        return {"data": data}

    except Exception:
        raise HTTPException(status_code=500, detail=traceback.format_exc())
