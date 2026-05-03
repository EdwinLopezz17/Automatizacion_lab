import pandas as pd
from dataclasses import dataclass
import os
from datetime import date
import traceback
from core.utils import to_date

@dataclass
class DBSitInfo:
    usuario: str
    isActivo: bool
    fecha_creacion: date
    fecha_ult_login: date
    fecha_cambio: date

class DBSitService:
    def __init__(self, csv_path="datos/BD_SIT.csv"):
        self._cache: dict[str, DBSitInfo] = {}
        self.csv_path = csv_path
        self.cargar_desde_csv()

    def cargar_desde_csv(self) -> None:
        self._cache = {}
        if not os.path.exists(self.csv_path):
            print(f"No existe el archivo {self.csv_path}")
            return

        try:
            df = pd.read_csv(self.csv_path)
            df.columns = [c.strip().upper() for c in df.columns]

            for _, row in df.iterrows():
                usuario = str(row.get('LOGINNAME', '')).strip().upper()
                usuario_limpio = usuario.split('\\')[-1]
                
                if usuario_limpio:
                    self._cache[usuario_limpio] = DBSitInfo(
                        usuario = usuario_limpio,
                        isActivo = str(row.get('ISACTIVE', '')).strip().upper() in ["Activo", "1", "YES", "ACTIVO"],
                        fecha_creacion  = to_date(row.get('CREATED'), "DMA"),
                        fecha_ult_login = to_date(row.get('ULTIMOLOGEO'), "DMA"),
                        fecha_cambio    = to_date(row.get('UPDATE'), "DMA"),
                    )
            print(f"DB_Sit cargado correctamente")
        except Exception as e:
            print(f"Error cargando datos: {e}")
            traceback.print_exc()

    def get_DB_Sit_user(self, usuario: str) -> DBSitInfo:
        key = str(usuario).strip().upper()
        return self._cache.get(key, DBSitInfo(usuario = "", isActivo = False, fecha_cambio = None,
                                              fecha_creacion = None, fecha_ult_login = None
        ))
    
    def get_all_DB_Sit_users(self) -> list[DBSitInfo]:
        return list(self._cache.values())
    