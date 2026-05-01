import pandas as pd
import requests
import os

def procesar_excel_a_api():
    # 1. Pedir la ruta del archivo
    ruta_archivo = input("Por favor, arrastra el archivo Excel aquí o escribe la ruta: ").strip()
    
    # Limpiar comillas en caso de que se haya arrastrado el archivo a la terminal
    ruta_archivo = ruta_archivo.replace('"', '').replace("'", "")

    if not os.path.exists(ruta_archivo):
        print("Error: El archivo no existe.")
        return

    try:
        # 2. Leer el Excel
        # Si las fechas no se leen bien, pandas las tratará como texto
        df = pd.read_excel(ruta_archivo)
        
        # Verificar que las columnas existan
        columnas_requeridas = ['usuario', 'app_or_db', 'fecha_login']
        if not all(col in df.columns for col in columnas_requeridas):
            print(f"Error: El Excel debe contener las columnas: {columnas_requeridas}")
            return

        url_api = "http://127.0.0.1:8000/api/post-ceses"
        print(f"\nIniciando envío de {len(df)} registros...\n")

        # 3. Recorrer cada registro
        for index, fila in df.iterrows():
            # Convertir fecha a string (formato YYYY-MM-DD) si es un objeto datetime
            fecha = fila['fecha_login']
            if hasattr(fecha, 'strftime'):
                fecha_str = fecha.strftime('%Y-%m-%d')
            else:
                fecha_str = str(fecha)

            payload = {
                "usuario": str(fila['usuario']),
                "app_or_db": str(fila['app_or_db']),
                "fecha_login": fecha_str
            }

            try:
                response = requests.post(url_api, json=payload)
                
                if response.status_code == 200 or response.status_code == 201:
                    print(f"[OK] Registro {index + 1}: Usuario {payload['usuario']} enviado.")
                else:
                    print(f"[ERROR] Registro {index + 1}: Status {response.status_code} - {response.text}")
            
            except requests.exceptions.RequestException as e:
                print(f"[CRITICAL] Error de conexión en registro {index + 1}: {e}")

        print("\nProceso finalizado.")

    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    procesar_excel_a_api()