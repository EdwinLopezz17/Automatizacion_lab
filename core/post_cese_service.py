import sqlite3
from datetime import date, datetime, time

class PostCeseService:
    def __init__(self, db_path: str = "certs_data.db"):
        self.db_path = db_path
        self._excepciones: set[tuple] = set()

    def cargar_desde_db(self) -> None:
        self._excepciones = set()
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute("SELECT usuario, app_or_db, fecha_login FROM consolidado_post_ceses")
            for r in cur.fetchall():
                usr = str(r[0]).strip().upper()
                app = str(r[1]).strip().upper()
                fec = str(r[2]).strip()
                self._excepciones.add((usr, app, fec))
            conn.close()
        except Exception as e:
            print(f"Error cargando excepciones desde SQLite: {e}")

    def es_post_cese(self, usuario: str, aplicacion: str, fecha_cese, ultimo_login) -> bool:
        if ultimo_login is None or str(ultimo_login).strip() in ["", "NaT", "nan", "None"]:
            return False
        
        if fecha_cese is None or str(fecha_cese).strip() in ["", "NaT", "nan", "None"]:
            return False

        try:
            dt_cese = self._to_datetime(fecha_cese)
            dt_login = self._to_datetime(ultimo_login)

            dt_cese_final = datetime.combine(dt_cese.date(), time(23, 59, 59))

            if dt_login <= dt_cese_final:
                return False
            
            f_login_str = dt_login.strftime('%Y-%m-%d')
            key = (str(usuario).upper().strip(), str(aplicacion).upper().strip(), f_login_str)
            
            if key in self._excepciones:
                return False

            return True

        except Exception as e:
            print(f"Error comparando fechas para {usuario}: {e}")
            return False

    def _to_datetime(self, val):
        if isinstance(val, datetime):
            return val
        if isinstance(val, date):
            return datetime.combine(val, time(0, 0))
        return datetime.fromisoformat(str(val).split(" ")[0])

