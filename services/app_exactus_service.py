import pandas as pd
import os
from dataclasses import dataclass
from datetime import date
import traceback
from core.utils import to_date
from typing import Optional

@dataclass
class UserAppExactusInfo:
    usuario: str
    full_name: str
    isActivo: bool
    fecha_creacion: Optional[date]
    fecha_login: Optional[date] = None

class AppExactusService:
    def __init__(self):
        self._cache: dict[str, UserAppExactusInfo] = {}
        self.path_app_exactus = "datos/App_EXACTUS.xlsx"
        self.path_app_exactus_login = "datos/App_EXACTUS_Login.xlsx"

        self.cargar_datos()

    def cargar_datos(self) -> None:
        self._cache = {}

        if not os.path.exists(self.path_app_exactus) or not os.path.exists(self.path_app_exactus_login):
            print(f"Error: Archivos no encontrados.")
            return

        try:
            df_app_exactus = pd.read_excel(self.path_app_exactus).fillna('')
            print(f"{self.path_app_exactus} cargado correctamente")

            df_app_exactus_login = pd.read_excel(self.path_app_exactus_login).fillna('')
            print(f"{self.path_app_exactus_login} cargado correctamente")

            df_app_exactus.columns = [str(c).strip().upper() for c in df_app_exactus.columns]
            df_app_exactus_login.columns = [str(c).strip().upper() for c in df_app_exactus_login.columns]

            for _, row in df_app_exactus.iterrows():
                usuario = str(row.get('USUARIO', '')).strip().upper()
                if not usuario or usuario == 'NAN': continue

                self._cache[usuario] = UserAppExactusInfo(
                    usuario = usuario,
                    full_name = str(row.get('NOMBRE','')).strip(),
                    isActivo = 'S' == str(row.get('ACTIVO','')).strip().upper(),
                    fecha_creacion = to_date(str(row.get('CREATEDATE', '')).strip()),
                    fecha_login = None,
                )

            for _, row in df_app_exactus_login.iterrows():
                usuario = str(row.get('USUARIO', '')).strip().upper()
                if not usuario or usuario == 'NAN': continue

                if usuario in self._cache:
                    self._cache[usuario].fecha_login = to_date(str(row.get('ULTIMO_LOGUIN', '')).strip())

        except Exception as e:
            print(f"Error cargando datos: {e}")
            traceback.print_exc()

    def get_UserAppExactus(self, usuario: str) -> UserAppExactusInfo:
        key = str(usuario).strip().upper() if usuario else ""
        user = self._cache.get(key)
        
        if user:
            return user
            
        return UserAppExactusInfo(usuario = "", full_name = "", isActivo = False,
                                   fecha_creacion = None, fecha_login = None)
    
    def get_all_UsersAppExactus(self) -> list[UserAppExactusInfo]:
        return list(self._cache.values())
    
