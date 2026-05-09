import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Optional
from core.utils import to_date
from dotenv import load_dotenv
import os

load_dotenv()

DB_PATH = os.getenv("DB_PATH")
TABLE_ENTRA = "consolidado_login_entra"

@dataclass
class UserEntraIDInfo:
    id: str
    mail: str
    upn: str
    city: str
    display_name: str
    account_enabled: bool
    exist_entra:bool
    creaction_type: str
    created_date_time: Optional[date]
    ultimo_login: Optional[date] = None


class EntraIDService:
    def __init__(self):
        self._cache: dict[str, UserEntraIDInfo] = {}
        self.cargar_datos()

    def cargar_datos(self) -> None:
        self._cache = {}

        if not self._db_existe():
            print(f"Error: base de datos no encontrada en {DB_PATH}")
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.execute(f"SELECT * FROM {TABLE_ENTRA}")
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            print(f"Error leyendo {TABLE_ENTRA}: {e}")
            return

        for row in rows:
            upn = str(row["upn"]).strip()
            if not upn:
                continue
            key = upn.upper()

            self._cache[key] = UserEntraIDInfo(
                id = str(row["id"]).strip(),
                mail = str(row["mail"]).strip(),
                upn = upn,
                city = str(row["city"]).strip(),
                display_name = str(row["display_name"]).strip(),
                account_enabled = bool(row["account_enabled"]),
                created_date_time = to_date(str(row["created_date"]).strip()),
                ultimo_login = to_date(str(row["ultimo_login"]).strip()),
                creaction_type = str(row["user_type"]).strip(),
                exist_entra = bool(row["existe_entra"]),
            )

        print(f"{len(self._cache)} usuarios cargados desde SQLite")

    def _db_existe(self) -> bool:
        import os
        return os.path.exists(DB_PATH)

    def get_UserEntraID(self, user_principal_name: str) -> UserEntraIDInfo:
        key  = str(user_principal_name).strip().upper() if user_principal_name else ""
        user = self._cache.get(key)

        if user:
            return user

        return self.void_info()

    def get_all_UsersEntraID(self) -> list[UserEntraIDInfo]:
        return list(self._cache.values())
    
    def get_active_users(self) -> list[UserEntraIDInfo]:
        return [u for u in self._cache.values() if u.account_enabled]
    
    def get_by_mail(self, mail: str) -> UserEntraIDInfo:
        mail_upper = mail.strip().upper() if mail else ""

        for user in self._cache.values():
            if user.mail.upper() == mail_upper:
                return user
        user_by_upn = self._cache.get(mail_upper)
        if user_by_upn:
            return user_by_upn

        return self.void_info()
    
    def void_info(self) -> UserEntraIDInfo:
        return UserEntraIDInfo(
            id = "", mail = "", upn = "", city = "",
            display_name = "", account_enabled = False,
            exist_entra=False, creaction_type = "",
            created_date_time = None, ultimo_login = None,
        )