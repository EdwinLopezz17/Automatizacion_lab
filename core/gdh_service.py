import pandas as pd
from dataclasses import dataclass
import os
from datetime import date

from core.utils import to_date

@dataclass
class GDHUserInfo:
    usuario: str
    nombre: str
    corre: str
    rol: str
    isActivo: bool
    fecha_creacion: date
    fecha_ult_login: date
    fecha_cambio: date

class ADService:
    def __init__(self, csv_path="datos/ad_data.csv"):
        self._cache: dict[str, GDHUserInfo] = {}
        self.csv_path = csv_path
        self.cargar_desde_csv()

    def cargar_desde_csv(self) -> None:
        self._cache = {}
        if not os.path.exists(self.csv_path):
            return

        try:
            df = pd.read_csv(self.csv_path)
            df.columns = [c.strip().upper() for c in df.columns]

            for _, row in df.iterrows():
                usuario = str(row.get('SAMACCOUNTNAME', '')).strip().upper()
                
                if usuario:
                    self._cache[usuario] = ADUserInfo(
                        usuario = str(row.get('SAMACCOUNTNAME','')).strip(),
                        nombre = str(row.get('DISPLAYNAME','')).strip(),
                        corre = str(row.get('MAIL','')).strip(),
                        rol = str(row.get('IPPHONE','')).strip(),
                        isActivo = str(row.get('ENABLED', '')).strip().upper() in ["TRUE", "1", "YES"],
                        fecha_creacion = to_date(row.get('WHENCREATED')),
                        fecha_ult_login = to_date(row.get('LASTLOGON')),
                        fecha_cambio = to_date(row.get('WHENCHANGED'))
                    )
            print(f"Datos extraids del AD correctamente")
        except Exception as e:
            print(f"Error: {e}")

    def get_AD_user(self, usuario: str) -> ADUserInfo:
        key = str(usuario).strip().upper()
        return self._cache.get(key, ADUserInfo(
            usuario=key, nombre="No encontrado", corre="n/a", rol="n/a",
            isActivo=False, fecha_creacion=None, fecha_ult_login=None, fecha_cambio=None
        ))
    
    def get_all_users_info(self) -> list[ADUserInfo]:
        return list(self._cache.values())
