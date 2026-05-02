import pandas as pd
import os
from dataclasses import dataclass
from datetime import date

from core.utils import to_date
from typing import Optional

@dataclass
class GDHUserInfo:
    matricula: str
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    dni: str
    u_organizativa: str
    fecha_alta: Optional[date] = None
    fecha_cese: Optional[date] = None
    isActivo: bool = False
    isCesado: bool = False

class GDHUserService:
    def __init__(self):
        self._cache: dict[str, GDHUserInfo] = {}
        self.path_activos_gdh = "datos/Activos_PrimaAFP.xls"
        self.path_cesados_gdh = "datos/Cesados_PrimaAFP.xls"
        self.cargar_datos()

    def cargar_datos(self) -> None:
        self._cache = {}

        if not os.path.exists(self.path_activos_gdh) or not os.path.exists(self.path_cesados_gdh):
            print(f"Error: Archivos no encontrados.")
            return

        try:
            df_activos = pd.read_excel(self.path_activos_gdh).fillna('')
            print(f"{self.path_activos_gdh} cargado correctamente")

            df_cesados = pd.read_excel(self.path_cesados_gdh).fillna('')
            print(f"{self.path_cesados_gdh} cargado correctamente")

            df_activos.columns = [str(c).strip().upper() for c in df_activos.columns]
            df_cesados.columns = [str(c).strip().upper() for c in df_cesados.columns]

            for _, row in df_activos.iterrows():
                matricula = str(row.get('ID SISTEMA', '')).strip().upper()
                if not matricula or matricula == 'NAN': continue
                
                self._cache[matricula] = GDHUserInfo(
                    matricula=matricula,
                    nombre=str(row.get('NOMBRES', '')).strip().upper(),
                    apellido_paterno=str(row.get('APELLIDO PATERNO', '')).strip().upper(),
                    apellido_materno=str(row.get('APELLIDO MATERNO', '')).strip().upper(),
                    dni=str(row.get('NÚMERO ID', '')).strip().upper(),
                    fecha_alta=to_date(str(row.get('FECHA', '')).strip()),
                    u_organizativa=str(row.get('UNIDAD ORGANIZATIVA', '')).strip().upper(),
                    isActivo=True,
                    isCesado=False
                )

            for _, row in df_cesados.iterrows():
                matricula = str(row.get('ID SISTEMA', '')).strip().upper()
                if not matricula or matricula == 'NAN': continue

                fecha_cese_val = to_date(str(row.get('FECHA', '')).strip())

                if matricula in self._cache:
                    self._cache[matricula].isCesado = True
                    self._cache[matricula].fecha_cese = fecha_cese_val
                else:
                    self._cache[matricula] = GDHUserInfo(
                        matricula=matricula,
                        nombre=str(row.get('NOMBRES', '')).strip().upper(),
                        apellido_paterno=str(row.get('APELLIDO PATERNO', '')).strip().upper(),
                        apellido_materno=str(row.get('APELLIDO MATERNO', '')).strip().upper(),
                        dni=str(row.get('NÚMERO ID', '')).strip().upper(),
                        fecha_alta=None,
                        fecha_cese=fecha_cese_val,
                        u_organizativa=str(row.get('UNIDAD ORGANIZATIVA', '')).strip().upper(),
                        isActivo=False,
                        isCesado=True
                    )

        except Exception as e:
            print(f"Error cargando datos: {e}")

    def get_GDH_user(self, matricula: str) -> GDHUserInfo:
        key = str(matricula).strip().upper() if matricula else ""
        user = self._cache.get(key)
        
        if user:
            return user
            
        return GDHUserInfo( matricula=key, nombre="NO ENCONTRADO", apellido_paterno="",
            apellido_materno="", dni="", u_organizativa="DESCONOCIDO", fecha_alta=None,
            fecha_cese=None, isActivo=False, isCesado=False
        )
    
    def get_full_name(self, matricula: str) -> str:
        key = str(matricula).strip().upper() if matricula else ""
        user = self._cache.get(key)
        
        if user:
            return user.nombre + " " + user.apellido_paterno + " " + user.apellido_materno
        return ""
    
    def get_all_GDH_user(self) -> list[GDHUserInfo]:
        return list(self._cache.values())
    