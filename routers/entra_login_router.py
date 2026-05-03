from __future__ import annotations
import sqlite3
from typing import Any
from fastapi import APIRouter, HTTPException

DB_PATH = "certs_data.db"
TABLE_ENTRA = "consolidado_login_entra"

router = APIRouter(prefix="/api", tags=["Entra ID Login"])

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_ENTRA} (
                id               TEXT PRIMARY KEY NOT NULL,
                upn              TEXT NOT NULL DEFAULT '',
                mail             TEXT NOT NULL DEFAULT '',
                city             TEXT NOT NULL DEFAULT '',
                display_name     TEXT NOT NULL DEFAULT '',
                account_enabled  INTEGER NOT NULL DEFAULT 0,
                created_date     TEXT NOT NULL DEFAULT '',
                ultimo_login     TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.commit()

init_db()


CAMPOS_VALIDOS = {
    "id", "upn", "mail", "city", "display_name",
    "account_enabled", "created_date", "ultimo_login"
}

def _upsert(conn: sqlite3.Connection, record: dict[str, Any]) -> dict:
    id_val = str(record.get("id", "")).strip()
    if not id_val:
        raise HTTPException(status_code=400, detail="El campo 'id' es obligatorio.")

    campos = {k: v for k, v in record.items() if k in CAMPOS_VALIDOS and k != "id"}

    if "account_enabled" in campos:
        val = campos["account_enabled"]
        campos["account_enabled"] = 1 if val in (True, 1, "true", "True", "1") else 0

    for k in campos:
        if k != "account_enabled":
            campos[k] = str(campos[k]).strip() if campos[k] is not None else ""

    set_clause = ", ".join([f"{k} = excluded.{k}" for k in campos])
    col_names  = ", ".join(["id"] + list(campos.keys()))
    placeholders = ", ".join(["?"] * (1 + len(campos)))
    values = [id_val] + list(campos.values())

    conn.execute(
        f"""
        INSERT INTO {TABLE_ENTRA} ({col_names})
        VALUES ({placeholders})
        ON CONFLICT(id) DO UPDATE SET
            {set_clause}
        """,
        values,
    )
    return {"id": id_val, **campos}

@router.get("/entra-login")
def listar_entra_login():
    with get_conn() as conn:
        cur  = conn.execute(f"SELECT * FROM {TABLE_ENTRA}")
        rows = [dict(r) for r in cur.fetchall()]
    return {"rows": rows}

@router.get("/entra-login/id/{id}")
def obtener_por_id(id: str):
    with get_conn() as conn:
        cur = conn.execute(f"SELECT * FROM {TABLE_ENTRA} WHERE id = ?", (id.strip(),))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"No se encontró registro con id '{id}'.")
    return dict(row)

@router.get("/entra-login/upn/{upn}")
def obtener_por_upn(upn: str):
    with get_conn() as conn:
        cur = conn.execute(f"SELECT * FROM {TABLE_ENTRA} WHERE upn = ?", (upn.strip(),))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"No se encontró registro con upn '{upn}'.")
    return dict(row)

@router.post("/entra-login", status_code=201)
def crear_o_actualizar(data: dict[str, Any]):
    with get_conn() as conn:
        result = _upsert(conn, data)
        conn.commit()
    return {"mensaje": "Registro guardado correctamente.", "registro": result}

@router.post("/entra-login/bulk", status_code=201)
def crear_o_actualizar_bulk(data: list[dict[str, Any]]):
    if not data:
        raise HTTPException(status_code=400, detail="La lista de registros está vacía.")

    resultados, errores = [], []

    with get_conn() as conn:
        for idx, record in enumerate(data):
            try:
                result = _upsert(conn, record)
                resultados.append(result)
            except HTTPException as e:
                errores.append({"indice": idx, "detalle": e.detail})
        conn.commit()

    return {
        "mensaje"   : f"{len(resultados)} registro(s) procesado(s).",
        "registros" : resultados,
        "errores"   : errores,
    }
