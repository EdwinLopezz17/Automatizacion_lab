import pandas as pd
from dataclasses import dataclass
import os
from datetime import date

from core.utils import to_date

@dataclass
class ADUserInfo:
    usuario: str
    nombre: str
    correo: str
    rol: str
    isActivo: bool
    fecha_creacion: date
    fecha_ult_login: date
    fecha_cambio: date

class ADService:
    def __init__(self):
        self._cache: dict[str, ADUserInfo] = {}
        self.csv_path = "datos/ad_data.csv"
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
                        correo = str(row.get('MAIL','')).strip(),
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
            usuario="", nombre="No encontrado", correo="n/a", rol="n/a",
            isActivo=False, fecha_creacion=None, fecha_ult_login=None, fecha_cambio=None
        ))
    
    def get_all_users_info(self) -> list[ADUserInfo]:
        return list(self._cache.values())
    
    def get_AD_user_by_correo(self, correo: str) -> ADUserInfo:
        if not correo:
            return self._generar_user_vacio()
            
        target_email = str(correo).strip().lower()

        for user_info in self._cache.values():
            if user_info.correo.strip().lower() == target_email:
                return user_info
        
        return self._generar_user_vacio()
    
    def _generar_user_vacio(self) -> ADUserInfo:
            return ADUserInfo(
                usuario="", 
                nombre="", 
                correo="", 
                rol="",
                isActivo=False, 
                fecha_creacion=None, 
                fecha_ult_login=None, 
                fecha_cambio=None
            )
