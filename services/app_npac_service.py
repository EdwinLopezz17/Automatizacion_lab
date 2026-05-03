import pandas as pd
from dataclasses import dataclass
import os
from datetime import date
from core.utils import to_date
from services.ad_service import ADService

@dataclass
class AppNpacUser:
    usuario: str
    isActivo: bool
    full_name: str
    fecha_creacion: date
    fecha_ult_login: date

class AppNpacService:
    def __init__(self):
        self._cache: dict[str, AppNpacUser] = {}
        self.csv_path = "datos/App_NPAC.csv"
        self.cargar_desde_csv()

    def cargar_desde_csv(self) -> None:
        self._cache = {}
        if not os.path.exists(self.csv_path):
            print(f"No existe el archivo {self.csv_path}")
            return
        
        ad_servie = ADService()

        try:
            df = pd.read_csv(self.csv_path)
            df.columns = [c.strip().upper() for c in df.columns]

            for _, row in df.iterrows():
                usuario = str(row.get('SAMACCOUNTNAME', '')).strip().upper()
                
                if usuario:
                    self._cache[usuario] = AppNpacUser(
                        usuario = usuario,
                        isActivo = True,
                        full_name = str(row.get('NAME', '')).strip().upper(),
                        fecha_creacion = ad_servie.get_AD_user(usuario).fecha_creacion,
                        fecha_ult_login = ad_servie.get_AD_user(usuario).fecha_ult_login,
                    )
            print(f"Datos de APP NPAC cargados correctamente")
        except Exception as e:
            print(f"Error: {e}")

    def get_app_npac_user(self, usuario: str) -> AppNpacUser:
        key = str(usuario).strip().upper()
        return self._cache.get(key, AppNpacUser( usuario = "", isActivo = False, full_name = "",
                                               fecha_creacion = None, fecha_ult_login = None
        ))
    
    def get_app_npac_users(self) -> list[AppNpacUser]:
        return list(self._cache.values())
    