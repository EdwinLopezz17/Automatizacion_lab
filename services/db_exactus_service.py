import pandas as pd
import os
from dataclasses import dataclass
from datetime import date

from core.utils import to_date
from typing import Optional

@dataclass
class UserDBExactusInfo:
    usuario: str
    isActivo: bool
    fecha_creacion: Optional[date]
    fecha_bloq: Optional[date] = None
    fecha_login: Optional[date] = None

class DBExactusService:
    def __init__(self):
        self._cache: dict[str, UserDBExactusInfo] = {}
        self.path_db_exactus = "datos/BD_EXACTUS.xlsx"
        self.path_db_exactus_login = "datos/BD_EXACTUS_Login.xlsx"

        self.cargar_datos()

    def cargar_datos(self) -> None:
        self._cache = {}

        if not os.path.exists(self.path_db_exactus) or not os.path.exists(self.path_db_exactus_login):
            print(f"Error: Archivos no encontrados.")
            return

        try:
            df_db_exactus = pd.read_excel(self.path_db_exactus).fillna('')
            print(f"{self.path_db_exactus} cargado correctamente")

            df_db_exactus_login = pd.read_excel(self.path_db_exactus_login).fillna('')
            print(f"{self.path_db_exactus_login} cargado correctamente")

            df_db_exactus.columns = [str(c).strip().upper() for c in df_db_exactus.columns]
            df_db_exactus_login.columns = [str(c).strip().upper() for c in df_db_exactus_login.columns]

            for _, row in df_db_exactus.iterrows():
                usuario = str(row.get('USERNAME', '')).strip().upper()
                if not usuario or usuario == 'NAN': continue

                self._cache[usuario] = UserDBExactusInfo(
                    usuario = usuario,
                    isActivo = "LOCKED" not in str(row.get('ACCOUNT_STATUS', '')).upper(),
                    fecha_creacion = to_date(str(row.get('CREATED', '')).strip()),
                    fecha_bloq = to_date(str(row.get('LOCK_DATE', '')).strip()),
                    fecha_login = None,
                )

            for _, row in df_db_exactus_login.iterrows():
                usuario = str(row.get('USERNAME', '')).strip().upper()
                if not usuario or usuario == 'NAN': continue

                if usuario in self._cache:
                    self._cache[usuario].fecha_login = to_date(str(row.get('MAX(DAS.TIMESTAMP)', '')).strip())

        except Exception as e:
            print(f"Error cargando datos: {e}")

    def get_UserDBExactus(self, usuario: str) -> UserDBExactusInfo:
        key = str(usuario).strip().upper() if usuario else ""
        user = self._cache.get(key)
        
        if user:
            return user
            
        return UserDBExactusInfo( usuario = "", isActivo = False, fecha_creacion = None,
                                 fecha_bloq= None, fecha_login = None)
    
    def get_all_UsersDBExactus(self) -> list[UserDBExactusInfo]:
        return list(self._cache.values())
    
