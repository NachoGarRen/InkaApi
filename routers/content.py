from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import database, models, schemas, auth

# IMPORTS PARA IA Y LIMPIEZA
import os
import requests
import google.generativeai as genai
from PIL import Image
import io
from supabase import create_client, Client  # Para poder borrar archivos del Storage

router = APIRouter(prefix="/content", tags=["Content"])

# --- CONFIGURACIÓN DE IA Y SUPABASE ---
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# --- FUNCIÓN DE VALIDACIÓN IA ---
def validar_imagen_tatuaje(image_url: str) -> bool:
    """
    Descarga la imagen desde la URL y la analiza con Gemini Vision.
    Retorna True si es contenido válido de tatuajes, False si es basura.
    En caso de error, retorna True para no bloquear la app.
    """
    try:
        print(f"[IA SCAN] Analizando imagen: {image_url}")
        
        # Descargamos la imagen temporalmente desde la URL que mandó Flutter
        respuesta_img = requests.get(image_url)
        if respuesta_img.status_code != 200:
            print("[WARNING] No se pudo descargar la imagen para analizarla.")
            return True  # Si no podemos descargarla, la dejamos pasar para no bloquear la app
            
        img = Image.open(io.BytesIO(respuesta_img.content))
        
        # Llamamos al modelo ultrarrápido de visión
        model = genai.GenerativeModel('gemini-flash-latest')
        
        prompt = """
        Eres un moderador estricto para una aplicación profesional de tatuajes.
        Analiza esta imagen y determina si es un tatuaje real, un boceto/diseño de tatuaje, 
        o material válido de un estudio de tatuajes.
        Si es válido, responde ÚNICAMENTE con la palabra: SI
        Si es basura (un perro, un paisaje, un meme, un selfie irrelevante), responde ÚNICAMENTE con la palabra: NO
        """
        
        response = model.generate_content([prompt, img])
        resultado = response.text.strip().upper()
        
        print(f"[IA DETECTED] Filtro IA detecto: {resultado}")
        
        return resultado == "SI"
        
    except Exception as e:
        print(f"[ERROR] Error en Gemini Vision: {e}")
        return True  # Si falla la IA por algún motivo, dejamos pasar la imagen


# ================= POSTS (Solo Artistas) =================
@router.post("/posts", response_model=schemas.PostResponse)
def create_post(
    post: schemas.PostCreate,
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    # Verificar si es artista
    if current_user.role != models.UserRole.ARTISTA:
        raise HTTPException(status_code=403, detail="Only artists can create posts")
    
    # Buscamos el ID del artista asociado al perfil
    if not current_user.artist_profile:
        raise HTTPException(status_code=400, detail="Artist profile not configured")

    # 👇 FILTRO ANTI-BASURA CON LIMPIEZA AUTOMÁTICA 👇
    if hasattr(post, 'image_url') and post.image_url:
        es_valida = validar_imagen_tatuaje(post.image_url)
        
        if not es_valida:
            print("[IA REJECTED] IA rechazo la imagen. Procediendo a borrarla del Storage de Supabase...")
            try:
                # Extraemos la ruta del archivo de la URL de Supabase
                # Ejemplo URL: https://...supabase.co/storage/v1/object/public/app-images/fotos/mi_tatuaje.jpg
                partes_url = post.image_url.split('/public/app-images/')
                if len(partes_url) > 1:
                    ruta_archivo = partes_url[1]  # Esto nos da: "fotos/mi_tatuaje.jpg"
                    
                    # Le decimos a Supabase que elimine el archivo basura
                    supabase.storage.from_("app-images").remove([ruta_archivo])
                    print(f"[OK] Archivo basura eliminado del Bucket: {ruta_archivo}")
            except Exception as e:
                print(f"[ERROR] Error intentando borrar la imagen huerfana: {e}")

            # Lanzamos el error para que Flutter se entere y el Post NUNCA se guarde en BD
            raise HTTPException(
                status_code=400, 
                detail="Imagen rechazada: Nuestra IA ha detectado que no es un tatuaje o diseño válido."
            )
    # 👆 FIN DEL FILTRO Y LIMPIEZA 👆

    # Si todo es correcto, guardamos el post en la base de datos
    new_post = models.Post(
        artist_id=current_user.artist_profile.id,
        **post.dict()
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

@router.get("/posts", response_model=List[schemas.PostResponse])
def get_feed(skip: int = 0, limit: int = 20, db: Session = Depends(database.get_db)):
    return db.query(models.Post).offset(skip).limit(limit).all()

# ================= REVIEWS (Clientes) =================
@router.post("/reviews", response_model=schemas.ReviewResponse)
def create_review(
    review: schemas.ReviewCreate,
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    # Verificar que la reserva existe
    booking = db.query(models.Booking).filter(models.Booking.id == review.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Verificar que el usuario es el cliente de esa reserva
    if booking.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only review your own bookings")

    new_review = models.Review(
        booking_id=booking.id,
        reviewer_id=current_user.id,
        artist_id=booking.artist_id,
        rating=review.rating,
        comment=review.comment
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

# ================= AI DESIGNS =================
@router.post("/ai-designs", response_model=schemas.AIDesignResponse)
def save_ai_design(
    design: schemas.AIDesignCreate,
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    # Aquí es donde guardarías el resultado de una generación por IA
    new_design = models.AIDesign(
        user_id=current_user.id,
        **design.dict()
    )
    db.add(new_design)
    db.commit()
    db.refresh(new_design)
    return new_design

@router.get("/ai-designs/me", response_model=List[schemas.AIDesignResponse])
def get_my_ai_designs(
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    return db.query(models.AIDesign).filter(models.AIDesign.user_id == current_user.id).all()

import uuid

# ================= LIKES Y FAVORITOS (Flujo TikTok) =================

def actualizar_vector_usuario(user_uuid, post_uuid, db: Session):
    try:
        post = db.query(models.Post).filter_by(id=post_uuid).first()
        if not post or not post.embedding: return

        perfil = db.query(models.Profile).filter_by(id=user_uuid).first()
        if not perfil:
            # En teoría el perfil siempre existe por el token, pero es buena práctica
            perfil = models.Profile(id=user_uuid, preference_embedding=post.embedding)
            db.add(perfil)
        elif not perfil.preference_embedding:
            perfil.preference_embedding = post.embedding
        else:
            # MEDIA MÓVIL: 90% pasado + 10% presente
            vector_actualizado = [
                (viejo * 0.9) + (nuevo * 0.1) 
                for viejo, nuevo in zip(perfil.preference_embedding, post.embedding)
            ]
            perfil.preference_embedding = vector_actualizado

        db.commit()
    except Exception as e:
        print(f"Error en worker asíncrono: {e}")

@router.post("/likes/{post_id}")
def toggle_like(
    post_id: str,
    background_tasks: BackgroundTasks,
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    like = db.query(models.Like).filter_by(user_id=current_user.id, post_id=post_uuid).first()
    if like:
        db.delete(like)
        db.commit()
        return {"status": "unliked"}
    else:
        new_like = models.Like(user_id=current_user.id, post_id=post_uuid)
        db.add(new_like)
        db.commit()
        
        # Disparamos el trabajador en la sombra para la Fase 3
        background_tasks.add_task(actualizar_vector_usuario, current_user.id, post_uuid, db)
        
        return {"status": "liked"}

@router.post("/favorites/{post_id}")
def toggle_favorite(
    post_id: str,
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post_id format")

    fav = db.query(models.Favorite).filter_by(user_id=current_user.id, post_id=post_uuid).first()
    if fav:
        db.delete(fav)
        db.commit()
        return {"status": "unfavorited"}
    else:
        new_fav = models.Favorite(user_id=current_user.id, post_id=post_uuid)
        db.add(new_fav)
        db.commit()
        return {"status": "favorited"}

# ================= SEGUIDORES =================
@router.post("/follow/{artist_id}")
def toggle_follow(
    artist_id: str,
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    try:
        artist_uuid = uuid.UUID(artist_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de artista inválido")

    follow = db.query(models.Follow).filter_by(
        follower_id=current_user.id, followed_id=artist_uuid
    ).first()

    if follow:
        db.delete(follow)
        db.commit()
        return {"status": "unfollowed"}
    else:
        new_follow = models.Follow(follower_id=current_user.id, followed_id=artist_uuid)
        db.add(new_follow)
        db.commit()
        return {"status": "followed"}

# ================= EDICIÓN DE POSTS =================
@router.patch("/posts/{post_id}")
def update_post(
    post_id: str,
    post_update: schemas.PostUpdate,
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de post inválido")

    post = db.query(models.Post).filter(models.Post.id == post_uuid).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    
    # Seguridad: Solo el dueño del post puede editarlo
    if post.artist_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este post")
    
    if post_update.description is not None:
        post.description = post_update.description
    if post_update.style_tag is not None:
        post.style_tag = post_update.style_tag
        
    db.commit()
    db.refresh(post)
    return {"status": "updated", "post_id": str(post.id)}