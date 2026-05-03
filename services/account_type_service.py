import sqlite3
import pandas as pd
from dataclasses import dataclass
import re

@dataclass
class AccountInfo:
    tipo: str
    matricula: str

class AccountTypeService:
    def __init__(self, db_path: str = "certs_data.db"):
        self._cache: dict[str, AccountInfo] = {}
        self.db_path = db_path

        self.cargar_desde_db()

    def cargar_desde_db(self) -> None:
        self._cache = {}
        try:
            conn = sqlite3.connect(self.db_path)
            df_srv = pd.read_sql_query("SELECT usuario, tipo_cuenta, matricula FROM consolidado_cuentas", conn)
            conn.close()

            if df_srv.empty:
                return
            
            for _, r in df_srv.iterrows():
                usuario = str(r['usuario']).strip().upper()
                if usuario:
                    self._cache[usuario] = AccountInfo(
                        tipo=str(r['tipo_cuenta']).strip().lower(),
                        matricula=str(r['matricula']).strip().upper()
                    )

        except Exception as e:
            print(f"Error cargando tipos de cuenta desde DB: {e}")

    def get(self, usuario: str) -> AccountInfo:
        key = str(usuario).strip().upper()
        if key in self._cache:
            return self._cache[key]

        tipo_calculado = "sin clasificar"
        
        if not key:
            return AccountInfo(tipo=tipo_calculado, matricula="")

        if re.match(r'^[TSP]\d+', key):
            tipo_calculado = "usuario"
        
        elif re.match(r'^X[PST]\d+', key):
            tipo_calculado = "proxy"

        return AccountInfo(
            tipo=tipo_calculado,
            matricula=key
        )
