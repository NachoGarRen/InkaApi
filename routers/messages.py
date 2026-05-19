from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Set
import database, models, schemas, auth
from utils.notifications import send_push_notification

router = APIRouter(prefix="/messages", tags=["Messages"])

@router.get("/contacts", response_model=List[dict])
def get_message_contacts(
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    # Obtiene todos los mensajes del usuario actual
    messages = db.query(models.Message).filter(
        (models.Message.sender_id == current_user.id) | (models.Message.receiver_id == current_user.id)
    ).all()
    
    # Extraer IDs únicos de contactos y la fecha de su último mensaje
    contact_latest_time = {}
    contact_unread_count = {}
    for msg in messages:
        contact_id = msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id
        if contact_id not in contact_latest_time or msg.created_at > contact_latest_time[contact_id]:
            contact_latest_time[contact_id] = msg.created_at
            
        if msg.receiver_id == current_user.id and not msg.is_read:
            contact_unread_count[contact_id] = contact_unread_count.get(contact_id, 0) + 1
            
    if not contact_latest_time:
        return []
    
    # Obtener los perfiles de los contactos
    contacts = db.query(models.Profile).filter(
        models.Profile.id.in_(list(contact_latest_time.keys()))
    ).all()
    
    result = []
    for profile in contacts:
        contact_dict = {
            "id": str(profile.id),
            "email": profile.email,
            "full_name": profile.full_name,
            "avatar_url": profile.avatar_url,
            "role": profile.role.value,
            "latest_message_time": contact_latest_time[profile.id].isoformat() if contact_latest_time.get(profile.id) else None,
            "unread_count": contact_unread_count.get(profile.id, 0)
        }
        
        # Si es artista, agregar datos adicionales
        if profile.artist_profile:
            contact_dict.update({
                "shop_name": profile.artist_profile.shop_name,
                "styles": profile.artist_profile.styles,
                "is_verified": profile.artist_profile.is_verified,
            })
        
        result.append(contact_dict)
    
    # Ordenar result por latest_message_time descendente
    result.sort(key=lambda x: x.get("latest_message_time", ""), reverse=True)
    
    return result

@router.get("/", response_model=List[schemas.MessageResponse])
def get_messages_with_artist(
    artist_id: str,
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    # Devuelve mensajes entre el usuario actual y el artista especificado
    # Incluyendo mensajes de sistema asociados a sus bookings
    from sqlalchemy import or_

    # Find total bookings between current_user and artist
    bookings = db.query(models.Booking.id).filter(
        or_(
            (models.Booking.client_id == current_user.id) & (models.Booking.artist_id == artist_id),
            (models.Booking.artist_id == current_user.id) & (models.Booking.client_id == artist_id)
        )
    ).all()
    booking_ids = [b[0] for b in bookings]

    messages = db.query(models.Message).filter(
        or_(
            (models.Message.sender_id == current_user.id) & (models.Message.receiver_id == artist_id),
            (models.Message.sender_id == artist_id) & (models.Message.receiver_id == current_user.id),
            models.Message.booking_id.in_(booking_ids) if booking_ids else False
        )
    ).order_by(models.Message.created_at.asc()).all()
    
    # Marcar los mensajes entrantes como leídos
    unread_messages = [m for m in messages if m.receiver_id == current_user.id and not m.is_read]
    if unread_messages:
        for m in unread_messages:
            m.is_read = True
        db.commit()
        
    return messages

@router.post("/", response_model=schemas.MessageResponse)
def send_message(
    message_data: schemas.MessageCreate,
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    # Validación mínima: destino y contenido
    if not message_data.receiver_id or not message_data.content:
        raise HTTPException(status_code=400, detail="receiver_id and content are required")

    new_message = models.Message(
        booking_id=message_data.booking_id,
        sender_id=current_user.id,
        receiver_id=message_data.receiver_id,
        content=message_data.content,
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    # Enviar notificación push al receptor
    try:
        send_push_notification(
            receiver_id=str(new_message.receiver_id),
            title=f"Nuevo mensaje de {current_user.full_name}",
            body=new_message.content if len(new_message.content) < 100 else f"{new_message.content[:97]}...",
            db=db
        )
    except Exception as e:
        print(f"Error enviando push: {e}")
        
    return new_message

@router.post("/upload_image")
async def upload_chat_image(
    file: UploadFile = File(...),
    current_user: models.Profile = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    import uuid
    from utils.storage import upload_file_to_supabase
    
    file_bytes = await file.read()
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    new_filename = f"chat_{current_user.id}_{uuid.uuid4()}.{file_extension}"
    
    public_url = upload_file_to_supabase(
        file_bytes, 
        new_filename, 
        bucket="app-images", 
        folder="chat-images"
    )
    
    if not public_url:
        raise HTTPException(status_code=500, detail="Failed to upload image")
        
    return {"url": public_url}

