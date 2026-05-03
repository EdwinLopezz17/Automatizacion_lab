import pandas as pd
from fastapi import HTTPException, UploadFile

def limpiar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    columnas_fantasma = [c for c in df.columns if 'Unnamed' in str(c)]
    for col in columnas_fantasma:
        if df[col].isnull().all():
            df = df.drop(columns=[col])

    df = df.loc[:, df.columns.notnull()]
    df = df.dropna(how='all')
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(axis=1, how='all')

    return df

def read_excel(upload: UploadFile, sheet_name=0):
    if not upload:
        return None

    try:
        upload.file.seek(0)
        filename = upload.filename.lower()
        
        print(f"\nPROCESANDO: {upload.filename}")

        if filename.endswith('.csv'):
            result = pd.read_csv(upload.file, sep=None, engine='python', encoding='utf-8-sig')
            if sheet_name is None:
                result = {"CSV_DATA": result}
            
        elif filename.endswith(('.xlsx', '.xls')):
            xl = pd.ExcelFile(upload.file)
            print(f"Pestañas encontradas en el archivo: {xl.sheet_names}")
            upload.file.seek(0)
            
            result = pd.read_excel(upload.file, sheet_name=sheet_name)
            
        else:
            raise ValueError("Formato de archivo no soportado. Use .csv, .xlsx o .xls")

        if isinstance(result, dict):
            for sheet in result:
                result[sheet] = limpiar_dataframe(result[sheet])
                print(f" Hoja: [{sheet}] | {len(result[sheet].columns)} columnas reales tras limpieza")
        else:
            result = limpiar_dataframe(result)
            cols = result.columns.tolist()
            print(f"Columnas reales detectadas ({len(cols)}): {cols}")

        return result

    except Exception as exc:
        print(f"Error detallado en {upload.filename}: {str(exc)}")
        raise HTTPException(
            status_code=400,
            detail=f"Error al procesar '{upload.filename}': {str(exc)}"
        )
    