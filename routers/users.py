from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from typing import List
import database, models, schemas, auth
from utils.storage import upload_file_to_supabase, delete_file_from_supabase
import time

router = APIRouter(prefix="/users", tags=["Users"])

# Obtener mi perfil (datos privados incluidos)
@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.Profile = Depends(auth.get_current_user)):
    return current_user

@router.get("/me/favorites", response_model=List[schemas.PostResponse])
def get_my_favorites(
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    # Join explícito para obtener los Posts que el usuario ha guardado
    favorites = db.query(models.Post).join(
        models.Favorite, 
        models.Favorite.post_id == models.Post.id
    ).filter(models.Favorite.user_id == current_user.id).all()
    return favorites

@router.get("/me/following")
def get_my_following(
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    followed_artists = db.query(models.Artist).join(
        models.Follow, models.Artist.id == models.Follow.followed_id
    ).filter(models.Follow.follower_id == current_user.id).all()
    
    # Devolvemos datos serializables manualmente para incluir avatar
    result = []
    for artist in followed_artists:
        profile = db.query(models.Profile).filter(models.Profile.id == artist.id).first()
        result.append({
            "id": str(artist.id),
            "shop_name": artist.shop_name,
            "bio": artist.bio,
            "styles": artist.styles or [],
            "avatar_url": profile.avatar_url if profile else None,
            "is_verified": artist.is_verified,
        })
    return result

# Obtener perfil público de otro usuario/artista por ID
@router.get("/{user_id}", response_model=schemas.UserResponse)
def read_user(user_id: str, db: Session = Depends(database.get_db)):
    user = db.query(models.Profile).filter(models.Profile.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Actualizar mi avatar o nombre
@router.patch("/me", response_model=schemas.UserResponse)
def update_user_me(
    update_data: schemas.UserUpdate,
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    print(f"DEBUG: Actualizando usuario {current_user.id} con datos: {update_data.dict(exclude_unset=True)}")
    if update_data.full_name:
        current_user.full_name = update_data.full_name
    if update_data.email:
        # Verificar que el email no esté en uso por otro usuario
        existing_user = db.query(models.Profile).filter(
            models.Profile.email == update_data.email,
            models.Profile.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = update_data.email
    if update_data.avatar_url:
        current_user.avatar_url = update_data.avatar_url
    
    if update_data.new_password:
        if not update_data.current_password:
            raise HTTPException(status_code=400, detail="Current password is required to set a new one")
        if not auth.verify_password(update_data.current_password, current_user.password):
            raise HTTPException(status_code=403, detail="Incorrect current password")
        current_user.password = auth.get_password_hash(update_data.new_password)
    
    if update_data.fcm_token:
        current_user.fcm_token = update_data.fcm_token
    
    db.commit()
    db.refresh(current_user)
    return current_user

# Subir avatar
@router.post("/me/avatar", response_model=schemas.UserResponse)
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    # Generar nombre único para el avatar
    timestamp = int(time.time())
    filename = f"avatar_{current_user.id}_{timestamp}.jpg"
    file_bytes = await file.read()
    
    # Borrar avatar anterior si existe
    if current_user.avatar_url:
        delete_file_from_supabase(current_user.avatar_url, bucket="app-images")
        
    public_url = upload_file_to_supabase(file_bytes, filename, bucket="app-images", folder="avatars")
    
    if not public_url:
        raise HTTPException(status_code=500, detail="Fallo al subir avatar a Supabase")
        
    current_user.avatar_url = public_url
    db.commit()
    db.refresh(current_user)
    
    return current_user