from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import database, schemas, models, auth
import os
import requests

router = APIRouter(prefix="/search", tags=["Search"])

def armar_respuesta_feed(resultados, liked_ids=None, saved_ids=None, followed_ids=None):
    """Formatea la respuesta del feed, incluyendo los estados de interacción si el usuario está logueado."""
    liked_ids = liked_ids or set()
    saved_ids = saved_ids or set()
    followed_ids = followed_ids or set()
    
    lista_final = []
    for row in resultados:
        post_id = str(row[0])
        artist_id = str(row[1])
        lista_final.append({
            "id": post_id,
            "artist_id": artist_id,
            "image_url": row[2],
            "description": row[3] if len(row) > 3 else "",
            "style_tag": row[4] if len(row) > 4 else None,
            "ar_image_url": row[5] if len(row) > 5 else None,
            "artist_avatar": row[6] if len(row) > 6 else None,
            "shop_name": row[7] if len(row) > 7 else "Artista",
            "is_liked": post_id in liked_ids,
            "is_saved": post_id in saved_ids,
            "is_following_artist": artist_id in followed_ids,
        })
    return {"results": lista_final}

def _get_user_interaction_sets(user_id, db):
    """Pre-carga en memoria los IDs de posts/artistas con los que el usuario ha interactuado."""
    liked_ids = {str(r[0]) for r in db.execute(
        text("SELECT post_id FROM likes WHERE user_id = :uid"), {"uid": str(user_id)}
    ).fetchall()}
    
    saved_ids = {str(r[0]) for r in db.execute(
        text("SELECT post_id FROM favorites WHERE user_id = :uid"), {"uid": str(user_id)}
    ).fetchall()}
    
    followed_ids = {str(r[0]) for r in db.execute(
        text("SELECT followed_id FROM follows WHERE follower_id = :uid"), {"uid": str(user_id)}
    ).fetchall()}
    
    return liked_ids, saved_ids, followed_ids

@router.get("/feed")
def get_feed(
    limit: int = 30, 
    db: Session = Depends(database.get_db),
    current_user: Optional[models.Profile] = Depends(auth.get_current_user_optional) 
):
    # Pre-cargar estados de interacción si hay usuario logueado
    liked_ids, saved_ids, followed_ids = set(), set(), set()
    if current_user:
        liked_ids, saved_ids, followed_ids = _get_user_interaction_sets(current_user.id, db)

    # Feed inteligente si tiene embedding
    if current_user and current_user.preference_embedding is not None:
        # Asegurarnos de que formateamos bien el vector para pgvector (separado por comas)
        pref_emb = current_user.preference_embedding
        # Si es un numpy array u otro tipo, iteramos y unimos con comas
        vector_str = "[" + ",".join(map(str, pref_emb)) + "]"
        
        resultados = db.execute(
            text(f"""
                SELECT p.id, p.artist_id, p.image_url, p.description, p.style_tag, p.ar_image_url, u.avatar_url, a.shop_name 
                FROM posts p
                LEFT JOIN profiles u ON p.artist_id = u.id
                LEFT JOIN artists a ON p.artist_id = a.id
                ORDER BY p.embedding <=> '{vector_str}'
                LIMIT :limite
            """),
            {"limite": limit}
        ).fetchall()
        
        return armar_respuesta_feed(resultados, liked_ids, saved_ids, followed_ids)

    # Feed cronológico (fallback)
    resultados = db.execute(
        text("""
            SELECT p.id, p.artist_id, p.image_url, p.description, p.style_tag, p.ar_image_url, u.avatar_url, a.shop_name
            FROM posts p
            LEFT JOIN profiles u ON p.artist_id = u.id
            LEFT JOIN artists a ON p.artist_id = a.id
            ORDER BY p.created_at DESC
            LIMIT :limite
        """),
        {"limite": limit}
    ).fetchall()
    
    return armar_respuesta_feed(resultados, liked_ids, saved_ids, followed_ids)

@router.get("/popular")
def get_popular_searches(limit: int = 6, db: Session = Depends(database.get_db)):
    """
    Devuelve los términos más buscados en la plataforma.
    """
    resultados = db.query(models.SearchCache.search_query)\
                   .order_by(models.SearchCache.search_count.desc())\
                   .limit(limit)\
                   .all()
    
    return {"results": [row[0] for row in resultados]}

@router.get("/tattoos")
def search_tattoos(
    query: str = Query(..., description="Lo que el usuario está buscando (ej: 'lobo oscuro')"),
    limit: int = Query(20, description="Cuántos resultados devolver"),
    db: Session = Depends(database.get_db),
    current_user: Optional[models.Profile] = Depends(auth.get_current_user_optional)
):
    # =======================================================
    # ⚡ 1. LA CACHÉ: ¿Alguien ha buscado esto antes?
    # =======================================================
    # Buscamos la frase exacta en minúsculas para evitar duplicados (Lobo vs lobo)
    clean_query = query.strip().lower()
    
    # Usamos SQL puro (text) porque SQLAlchemy a veces se lía con los vectores
    cache_result = db.execute(
        text("SELECT embedding FROM search_cache WHERE search_query = :q"),
        {"q": clean_query}
    ).fetchone()

    vector_busqueda = None

    if cache_result and cache_result[0] is not None:
        print(f"[CACHE HIT] Usando vector guardado para: '{clean_query}'")
        vector_busqueda = cache_result[0]
        # Incrementar contador de popularidad (Caché Hit)
        try:
            db.execute(
                text("UPDATE search_cache SET search_count = search_count + 1 WHERE search_query = :q"),
                {"q": clean_query}
            )
            db.commit()
        except Exception:
            db.rollback()
    else:
        # =======================================================
        # 🧠 2. SIN CACHÉ: Llamamos a Gemini para crear el vector
        # =======================================================
        print(f"[GEMINI] Buscando significado de: '{clean_query}'")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"error": "Falta GEMINI_API_KEY"}

        url_embed = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={api_key}"
        payload = {
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": clean_query}]}
        }
        
        respuesta = requests.post(url_embed, json=payload)
        
        if respuesta.status_code == 200:
            # Extraemos los números y los limitamos a 768 dimensiones
            vector_busqueda = respuesta.json()['embedding']['values'][:768]
            
            # 💾 ¡Guardamos en caché para el siguiente usuario!
            vector_str = "[" + ",".join(map(str, vector_busqueda)) + "]"
            try:
                # Usamos ON CONFLICT para manejar condiciones de carrera de forma segura
                db.execute(
                    text("""
                    INSERT INTO search_cache (search_query, embedding, search_count) 
                    VALUES (:q, :v, 1) 
                    ON CONFLICT (search_query) 
                    DO UPDATE SET search_count = search_cache.search_count + 1
                    """),
                    {"q": clean_query, "v": vector_str}
                )
                db.commit()
                print("[CACHE SAVE] Nueva busqueda guardada en cache.")
            except Exception as e:
                print(f"[WARNING] Aviso al guardar cache: {e}")
                db.rollback()
        else:
            return {"error": "Fallo al comunicar con la IA de búsqueda"}

    # =======================================================
    # 🎯 3. BÚSQUEDA MATEMÁTICA EN LA BASE DE DATOS
    # =======================================================
    if vector_busqueda:
        # Convertimos la lista de Python al formato "[0.1, 0.2...]" para Postgres
        if isinstance(vector_busqueda, list):
             vector_str = "[" + ",".join(map(str, vector_busqueda)) + "]"
        else:
             vector_str = vector_busqueda # Si viene de caché ya es un string/vector de la DB

        # 🚀 NOVEDAD: Alimentamos el algoritmo del Feed "Para ti" con esta búsqueda
        if current_user:
            import json
            try:
                # Asegurarnos de que tenemos una lista de floats
                if isinstance(vector_busqueda, str):
                    vector_list = json.loads(vector_busqueda)
                else:
                    vector_list = list(vector_busqueda)
                
                # Solucionado el error de validación para arrays de numpy: usar 'is None' o revisar tamaño
                if current_user.preference_embedding is None or len(current_user.preference_embedding) == 0:
                    current_user.preference_embedding = vector_list
                else:
                    # Media móvil: 70% preferencias antiguas + 30% la búsqueda actual
                    current_user.preference_embedding = [
                        (float(viejo) * 0.7) + (float(nuevo) * 0.3)
                        for viejo, nuevo in zip(current_user.preference_embedding, vector_list)
                    ]
                db.commit()
                print("[FEED ALGORITHM] Vector del usuario actualizado con su última búsqueda.")
            except Exception as e:
                db.rollback()
                print(f"[ERROR] Fallo al actualizar preferencias con la búsqueda: {e}")

        # Magia de pgvector: El operador <=> calcula la "Distancia Coseno" 
        # (qué tan similares son los conceptos de 0 a 1).
        # Ordenamos de menor distancia (más parecido) a mayor.
        resultados = db.execute(
            text("""
                SELECT id, artist_id, image_url, description, style_tag, ar_image_url 
                FROM posts 
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> :vector
                LIMIT :limite
            """),
            {"vector": vector_str, "limite": limit}
        ).fetchall()

        # Convertimos el resultado a una lista de diccionarios que Flutter entienda
        lista_final = []
        for row in resultados:
            lista_final.append({
                "id": row[0],
                "artist_id": row[1],
                "image_url": row[2],
                "description": row[3],
                "style_tag": row[4],
                "ar_image_url": row[5]
            })

        return {"query": clean_query, "results": lista_final}
    
    return {"query": clean_query, "results": []}