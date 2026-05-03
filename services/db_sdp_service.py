import pandas as pd
import os
from dataclasses import dataclass
from datetime import date

from core.utils import to_date
from typing import Optional

@dataclass
class UserDBSdpInfo:
    usuario: str
    isActivo: bool
    fecha_creacion: Optional[date]
    fecha_bloq: Optional[date] = None
    fecha_login: Optional[date] = None

class DBSdpService:
    def __init__(self):
        self._cache: dict[str, UserDBSdpInfo] = {}
        self.path_db_sdp = "datos/BD_SDP.xlsx"
        self.path_db_sdp_login = "datos/BD_SDP_Login.xlsx"
        
        self.cargar_datos()

    def cargar_datos(self) -> None:
        self._cache = {}

        if not os.path.exists(self.path_db_sdp) or not os.path.exists(self.path_db_sdp_login):
            print(f"Error: Archivos no encontrados.")
            return

        try:
            df_db_sdp = pd.read_excel(self.path_db_sdp).fillna('')
            print(f"{self.path_db_sdp} cargado correctamente")

            df_db_sdp_login = pd.read_excel(self.path_db_sdp_login).fillna('')
            print(f"{self.path_db_sdp_login} cargado correctamente")

            df_db_sdp.columns = [str(c).strip().upper() for c in df_db_sdp.columns]
            df_db_sdp_login.columns = [str(c).strip().upper() for c in df_db_sdp_login.columns]

            for _, row in df_db_sdp.iterrows():
                usuario = str(row.get('USERNAME', '')).strip().upper()
                if not usuario or usuario == 'NAN': continue

                self._cache[usuario] = UserDBSdpInfo(
                    usuario = usuario,
                    isActivo = "LOCKED" not in str(row.get('ACCOUNT_STATUS', '')).upper(),
                    fecha_creacion = to_date(str(row.get('CREATED', '')).strip()),
                    fecha_bloq = to_date(str(row.get('LOCK_DATE', '')).strip()),
                    fecha_login = None,
                )

            for _, row in df_db_sdp_login.iterrows():
                usuario = str(row.get('USERNAME', '')).strip().upper()
                if not usuario or usuario == 'NAN': continue

                if usuario in self._cache:
                    self._cache[usuario].fecha_login = to_date(str(row.get('MAX(DAS.TIMESTAMP)', '')).strip())

        except Exception as e:
            print(f"Error cargando datos: {e}")

    def get_UserDBSdp(self, usuario: str) -> UserDBSdpInfo:
        key = str(usuario).strip().upper() if usuario else ""
        user = self._cache.get(key)
        
        if user:
            return user
            
        return UserDBSdpInfo( usuario = "", isActivo = False, fecha_creacion = None,
                                 fecha_bloq= None, fecha_login = None)
    
    def get_all_UsersDBsdp(self) -> list[UserDBSdpInfo]:
        return list(self._cache.values())
    