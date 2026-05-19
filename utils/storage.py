# api/utils/storage.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# ==========================================
# 🛠️ PARCHE PARA ERROR SSL DE WINDOWS
# ==========================================
if "SSL_CERT_FILE" in os.environ:
    del os.environ["SSL_CERT_FILE"]

# Cargamos las variables del .env (por si este módulo se importa antes que main.py)
load_dotenv()

# Las claves ahora se leen del archivo .env, NUNCA hardcodeadas
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "🚨 Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env. "
        "Asegúrate de tener ambas variables definidas."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_file_to_supabase(file_bytes, file_name, bucket="app-images", folder="certificados-higiene"):
    try:
        # Subir a la carpeta especificada dentro del bucket
        path = f"{folder}/{file_name}"
        
        # content-type es importante para que se vea en el navegador
        res = supabase.storage.from_(bucket).upload(
            path=path,
            file=file_bytes,
            file_options={
                "content-type": "image/jpeg",
                "upsert": "true"  # Sobrescribir si el archivo ya existe
            }
        )
        
        # Obtener la URL pública
        public_url = supabase.storage.from_(bucket).get_public_url(path)
        return public_url
    except Exception as e:
        print(f"Error subiendo a Supabase: {e}")
        return None

def delete_file_from_supabase(file_url: str, bucket: str = "app-images"):
    """
    Extrae la ruta del archivo de una URL pública de Supabase y lo elimina.
    Funciona con cualquier bucket (app-images, portfolio-artistas, ar-stencils, etc.)
    """
    if not file_url:
        return False
    try:
        # Estrategia 1: Buscar por /public/bucket/ (formato estándar de Supabase)
        token = f"/public/{bucket}/"
        if token in file_url:
            ruta_archivo = file_url.split(token)[1]
            # Limpiar posibles parámetros de query (como ?t=12345)
            ruta_archivo = ruta_archivo.split('?')[0]
            
            supabase.storage.from_(bucket).remove([ruta_archivo])
            print(f"🗑️ Archivo eliminado del Storage: {ruta_archivo}")
            return True
        
        # Estrategia 2: Buscar por /bucket/ (fallback si la URL tiene otro formato)
        parts = file_url.split(f"/{bucket}/")
        if len(parts) >= 2:
            ruta_archivo = parts[1].split('?')[0]
            supabase.storage.from_(bucket).remove([ruta_archivo])
            print(f"🗑️ Archivo eliminado del Storage (fallback): {ruta_archivo}")
            return True
        
        print(f"⚠️ No se pudo extraer el path del archivo de la URL: {file_url}")
        return False
    except Exception as e:
        print(f"⚠️ Error eliminando archivo del Storage: {e}")
        return False