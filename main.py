import os
import requests 
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware  
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import engine, Base, get_db
from dotenv import load_dotenv # <--- IMPORTANTE: Añadido para leer el .env
from routers import users, auth, artists, search # 👈 Añade 'search' aquí
# Cargar las variables secretas del .env
load_dotenv()

# --- PARCHE PARA EL ERROR DE SSL ---
if "SSL_CERT_FILE" in os.environ:
    del os.environ["SSL_CERT_FILE"]

# Importamos TODOS los routers
from routers import auth, artists, bookings, users, content, messages, tattoo_ar

# IMPORTANTE: En producción (Render) no usamos create_all porque puede bloquear el arranque 
# si la conexión de Supabase tarda en responder. Las tablas ya existen.
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tattoo Art API with Supabase")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

app.include_router(auth.router)
app.include_router(users.router)  
app.include_router(artists.router)
app.include_router(bookings.router)
app.include_router(content.router)
app.include_router(messages.router)
app.include_router(search.router) 
app.include_router(tattoo_ar.router) 

# --- NUESTRO ENDPOINT NUCLEAR Y AUTOPILOTO DE IA ---
@app.get("/buscar-tatuajes-ia")
def buscar_tatuajes_ia(idea: str, db: Session = Depends(get_db)):
    try:
        print(f"🧠 Buscando idea: {idea}")
        
        # 👇 MAGIA: Ahora lee la clave nueva del .env sin exponerla 👇
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise Exception("🚨 No se encontró la GEMINI_API_KEY en el archivo .env")

        # 1. Le preguntamos a Google qué modelos tienes habilitados de verdad
        url_models = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res_models = requests.get(url_models)
        
        if res_models.status_code != 200:
            raise Exception(f"No se pudo consultar a Google: {res_models.text}")
        
        modelos_disponibles = res_models.json().get("models", [])
        
        # Buscamos automáticamente el primero que sirva para convertir texto a números
        modelo_embedding = None
        for m in modelos_disponibles:
            if "embedContent" in m.get("supportedGenerationMethods", []):
                modelo_embedding = m["name"]
                break
                
        if not modelo_embedding:
            raise Exception("🚨 TU API KEY NO TIENE NINGÚN MODELO DE BÚSQUEDA ACTIVADO.")
            
        print(f"✅ ¡Hack superado! Google nos dice que usemos el modelo oculto: {modelo_embedding}")
        
        # 2. Ahora sí, disparamos la petición con el modelo exacto
        url_embed = f"https://generativelanguage.googleapis.com/v1beta/{modelo_embedding}:embedContent?key={api_key}"
        
        payload = {
            "model": modelo_embedding,
            "content": {
                "parts": [{"text": idea}]
            }
        }
        
        respuesta = requests.post(url_embed, json=payload)
        
        if respuesta.status_code != 200:
            raise Exception(f"Fallo al generar el vector: {respuesta.text}")
            
        # Extraemos la lista y LA RECORTAMOS a 768 exactos ✂️
        datos = respuesta.json()
        vector_busqueda = datos['embedding']['values'][:768]
        
        print("✅ ¡Números generados! Buscando tatuajes en Supabase...")
        
        # 3. Buscamos en Supabase usando CAST para que Python no se confunda
        query = text("SELECT * FROM buscar_tatuajes(CAST(:vector AS vector(768)), 3)")
        resultados = db.execute(query, {"vector": str(vector_busqueda)}).mappings().all()
        
        return [dict(row) for row in resultados]
    except Exception as e:
        print(f"❌ Error en la IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- RUTA DE PRUEBA ORIGINAL ---
@app.get("/")
def read_root():
    return {"status": "online", "db": "supabase"}