import pandas as pd
import os
from dataclasses import dataclass
from datetime import date
import traceback
from core.utils import to_date
from typing import Optional

@dataclass
class UserAppSdpInfo:
    usuario: str
    isActivo: bool
    fecha_creacion: Optional[date]
    fecha_login: Optional[date] = None

class AppSdpService:
    def __init__(self):
        self._cache: dict[str, UserAppSdpInfo] = {}
        self.path_app_sdp = "datos/App_SDP.xlsx"
        self.path_app_sdp_login = "datos/App_SDP_Login.xlsx"

        self.cargar_datos()

    def cargar_datos(self) -> None:
        self._cache = {}

        if not os.path.exists(self.path_app_sdp) or not os.path.exists(self.path_app_sdp_login):
            print(f"Error: Archivos no encontrados.")
            return

        try:
            df_app_sdp = pd.read_excel(self.path_app_sdp).fillna('')
            print(f"{self.path_app_sdp} cargado correctamente")

            df_app_sdp_login = pd.read_excel(self.path_app_sdp_login).fillna('')
            print(f"{self.path_app_sdp_login} cargado correctamente")

            df_app_sdp.columns = [str(c).strip().upper() for c in df_app_sdp.columns]
            df_app_sdp_login.columns = [str(c).strip().upper() for c in df_app_sdp_login.columns]

            for _, row in df_app_sdp.iterrows():
                usuario = str(row.get('COD_USUARIO', '')).strip().upper()
                if not usuario or usuario == 'NAN': continue

                self._cache[usuario] = UserAppSdpInfo(
                    usuario = usuario,
                    isActivo = 'S' == str(row.get('EST_ACTIVO','')).strip().upper(),
                    fecha_creacion = to_date(str(row.get('FEC_INCLUSION', '')).strip()),
                    fecha_login = None,
                )

            for _, row in df_app_sdp_login.iterrows():
                usuario = str(row.get('COD_USUARIO', '')).strip().upper()
                if not usuario or usuario == 'NAN': continue

                if usuario in self._cache:
                    self._cache[usuario].fecha_login = to_date(str(row.get('FECHALOGIN', '')).strip())

        except Exception as e:
            print(f"Error cargando datos: {e}")
            traceback.print_exc()

    def get_UserAppSdp(self, usuario: str) -> UserAppSdpInfo:
        key = str(usuario).strip().upper() if usuario else ""
        user = self._cache.get(key)
        
        if user:
            return user
            
        return UserAppSdpInfo(usuario = "", isActivo=False, fecha_creacion = None, fecha_login = None)
    
    def get_all_UsersAppSdp(self) -> list[UserAppSdpInfo]:
        return list(self._cache.values())
    