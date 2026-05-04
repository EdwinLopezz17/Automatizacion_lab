import os

def generar_contexto_proyecto(ruta_raiz, archivo_salida):
    extensiones_validas = ('.py', '.js', '.css', '.json')
    carpetas_ignoradas = {'.html', '.git', '__pycache__','env', 'venv', '.vscode', 'node_modules'}
    archivo_script = os.path.basename(__file__)

    with open(archivo_salida, 'w', encoding='utf-8') as f_out:
        for raiz, dirs, archivos in os.walk(ruta_raiz):
            dirs[:] = [d for d in dirs if d not in carpetas_ignoradas]

            for nombre_archivo in archivos:
                if nombre_archivo == archivo_script or nombre_archivo == archivo_salida:
                    continue

                if nombre_archivo.endswith(extensiones_validas):
                    ruta_completa = os.path.join(raiz, nombre_archivo)
                    f_out.write(f"//{ruta_completa}\n")
                    
                    try:
                        with open(ruta_completa, 'r', encoding='utf-8') as f_in:
                            f_out.write(f_in.read())
                    except Exception as e:
                        f_out.write(f"Error al leer archivo: {e}")
                    
                    f_out.write("\n\n")

    print(f"Proceso terminado. Archivo generado: {archivo_salida}")

ruta_del_proyecto = "./" 
nombre_del_txt = "contexto_proyecto.txt"

generar_contexto_proyecto(ruta_del_proyecto, nombre_del_txt)
