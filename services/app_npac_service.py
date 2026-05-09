import pandas as pd
from dataclasses import dataclass, field
import os
from datetime import date
from services.ad_service import ADService

@dataclass
class AppNpacUser:
    usuario: str
    isActivo: bool
    full_name: str
    fecha_creacion: date
    fecha_ult_login: date
    grupos: list[str] = field(default_factory=list)

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
        
        ad_service = ADService()

        try:
            df = pd.read_csv(self.csv_path)
            df.columns = [c.strip().upper() for c in df.columns]

            for _, row in df.iterrows():
                usuario = str(row.get('SAMACCOUNTNAME', '')).strip().upper()
                grupo = str(row.get('GRUPO', '')).strip().upper()
                
                if not usuario: continue
                if usuario not in self._cache:
                    self._cache[usuario] = AppNpacUser(
                        usuario = usuario,
                        isActivo = True,
                        full_name = str(row.get('NAME', '')).strip().upper(),
                        fecha_creacion = ad_service.get_AD_user(usuario).fecha_creacion,
                        fecha_ult_login = ad_service.get_AD_user(usuario).fecha_ult_login,
                        grupos = []
                    )
                if grupo and grupo not in self._cache[usuario].grupos:
                    self._cache[usuario].grupos.append(grupo)
                    
            print(f"Datos de APP NPAC cargados correctamente")
        except Exception as e:
            print(f"Error: {e}")

    def get_app_npac_user(self, usuario: str) -> AppNpacUser:
        key = str(usuario).strip().upper()
        return self._cache.get(key, AppNpacUser( usuario = "", isActivo = False, full_name = "",
                                               fecha_creacion = None, fecha_ult_login = None, grupos=[]
        ))
    
    def get_app_npac_users(self) -> list[AppNpacUser]:
        return list(self._cache.values())
    