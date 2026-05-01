from __future__ import annotations
import sqlite3
from typing import Any
from fastapi import APIRouter, HTTPException

DB_PATH = "certs_data.db"
TABLE_CUENTAS = "consolidado_cuentas"
TABLE_POST_CESE = "consolidado_post_ceses"

router = APIRouter(prefix="/api", tags=["Gestión de Excepciones"])

APPS_PERMITIDAS = [
    "DB_SDP", "DB_EXACTUS", "DB_SIT", "Active_Directory",
    "APP_Exactus", "APP_SDP", "APP_SIT", "APP_NPAC", "APP_ENTRAID"
]

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_CUENTAS} (
                usuario TEXT NOT NULL DEFAULT '',
                tipo_cuenta TEXT NOT NULL DEFAULT '',
                matricula TEXT NOT NULL DEFAULT ''
            )
        """)

        apps_sql = ", ".join([f"'{a}'" for a in APPS_PERMITIDAS])
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_POST_CESE} (
                usuario      TEXT NOT NULL,
                app_or_db    TEXT NOT NULL CHECK (app_or_db IN ({apps_sql})),
                fecha_login  TEXT NOT NULL
            )
        """)
        conn.commit()

init_db()

def get_columns() -> list[str]:
    with get_conn() as conn:
        cur = conn.execute(f"PRAGMA table_info({TABLE_CUENTAS})")
        return [row["name"] for row in cur.fetchall()]

@router.get("/consolidado-historico")
def consolidado_page():
    with get_conn() as conn:
        cur = conn.execute(f"SELECT rowid AS __rowid, * FROM {TABLE_CUENTAS}")
        rows = [dict(r) for r in cur.fetchall()]
    return {"rows": rows}

@router.get("/consolidado-historico")
def listar_consolidado():
    cols = get_columns()
    with get_conn() as conn:
        cur  = conn.execute(f"SELECT rowid AS __rowid, * FROM {TABLE_CUENTAS}")
        rows = [dict(r) for r in cur.fetchall()]
    return {"columns": cols, "rows": rows}

@router.post("/consolidado-historico", status_code=201)
def crear_registro(data: dict[str, Any]):
    cols = get_columns()
    fields = {k: v for k, v in data.items() if k in cols}
    if not fields:
        raise HTTPException(status_code=400, detail="No hay campos válidos")

    placeholders = ", ".join(["?"] * len(fields))
    col_names    = ", ".join(fields.keys())
    values       = list(fields.values())

    with get_conn() as conn:
        cur = conn.execute(f"INSERT INTO {TABLE_CUENTAS} ({col_names}) VALUES ({placeholders})", values)
        conn.commit()
        return {"rowid": cur.lastrowid, "mensaje": "Creado"}

@router.put("/consolidado-historico/{rowid}")
def actualizar_registro(rowid: int, data: dict[str, Any]):
    cols = get_columns()
    fields = {k: v for k, v in data.items() if k in cols}
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [rowid]

    with get_conn() as conn:
        cur = conn.execute(f"UPDATE {TABLE_CUENTAS} SET {set_clause} WHERE rowid = ?", values)
        conn.commit()
        return {"mensaje": "Actualizado"}

@router.delete("/consolidado-historico/{rowid}")
def eliminar_registro(rowid: int):
    with get_conn() as conn:
        cur = conn.execute(f"DELETE FROM {TABLE_CUENTAS} WHERE rowid = ?", (rowid,))
        conn.commit()
        return {"mensaje": "Eliminado"}
    

#POST CESE END POINTs
@router.get("/post-ceses")
def listar_post_ceses():
    with get_conn() as conn:
        cur = conn.execute(f"SELECT rowid AS __rowid, * FROM {TABLE_POST_CESE}")
        rows = [dict(r) for r in cur.fetchall()]
    return {"rows": rows}

@router.post("/post-ceses", status_code=201)
def crear_post_cese(data: dict[str, Any]):
    app_val = data.get("app_or_db")
    
    if app_val not in APPS_PERMITIDAS:
        raise HTTPException(
            status_code=400, 
            detail=f"Aplicación no permitida. Valores válidos: {APPS_PERMITIDAS}"
        )

    with get_conn() as conn:
        try:
            conn.execute(
                f"INSERT INTO {TABLE_POST_CESE} (usuario, app_or_db, fecha_login) VALUES (?, ?, ?)",
                (data.get("usuario", "").upper().strip(), app_val, data.get("fecha_login", ""))
            )
            conn.commit()
            return {"mensaje": "Excepción registrada correctamente"}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Error de integridad en los datos.")

@router.put("/post-ceses/{rowid}")
def actualizar_post_cese(rowid: int, data: dict[str, Any]):
    with get_conn() as conn:
        fields = {k: v for k, v in data.items() if k in ["usuario", "app_or_db", "fecha_login"]}
        set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
        values = list(fields.values()) + [rowid]
        cur = conn.execute(f"UPDATE {TABLE_POST_CESE} SET {set_clause} WHERE rowid = ?", values)
        conn.commit()
        return {"mensaje": "Registro actualizado"}

@router.delete("/post-ceses/{rowid}")
def eliminar_post_cese(rowid: int):
    with get_conn() as conn:
        conn.execute(f"DELETE FROM {TABLE_POST_CESE} WHERE rowid = ?", (rowid,))
        conn.commit()
        return {"mensaje": "Registro eliminado"}
    
