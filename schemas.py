from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from models import UserRole, BookingStatus, StudioType # Importamos el nuevo Enum

# ... (User schemas se quedan igual) ...
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    fcm_token: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    avatar_url: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

# --- ARTISTS ---

class ArtistCreate(BaseModel):
    shop_name: str
    bio: str
    styles: List[str]
    
    # Ubicación y Geolocalización (Flutter enviará esto)
    address: str
    latitude: float
    longitude: float
    workspace_type: StudioType # 'shop', 'private', 'mobile'
    show_exact_location: bool
    
    # Contacto
    instagram_handle: str
    whatsapp_number: Optional[str] = None
    website_url: Optional[str] = None
    
    # Documentación para verificar
    business_license_id: str # DNI/NIF
    business_document_url: Optional[str] = None # URL de la foto del certificado
    
    # Horario
    working_hours_start: Optional[str] = "09:00"
    working_hours_end: Optional[str] = "18:00"

class ArtistResponse(BaseModel):
    id: UUID
    shop_name: str
    bio: str
    styles: List[str]
    
    # Datos públicos seguros
    address: str # Quizás quieras ocultar esto si es 'private' y show_exact_location es False
    latitude: float
    longitude: float
    workspace_type: StudioType
    show_exact_location: bool
    
    instagram_handle: str
    whatsapp_number: Optional[str]
    website_url: Optional[str]
    
    is_verified: bool
    
    class Config:
        from_attributes = True

# ... (Bookings, Posts, Reviews, AI Designs se quedan igual) ...
class BookingCreate(BaseModel):
    artist_id: UUID
    idea_description: str
    body_part: str
    size_cm: Optional[str] = None
    booking_date: Optional[datetime] = None
    duration_hours: Optional[float] = None

class BookingUpdate(BaseModel):
    status: Optional[BookingStatus] = None
    price_quote: Optional[float] = None
    booking_date: Optional[datetime] = None
    idea_description: Optional[str] = None
    body_part: Optional[str] = None
    size_cm: Optional[str] = None
    duration_hours: Optional[float] = None
    client_accepted: Optional[bool] = None
    artist_accepted: Optional[bool] = None

class BookingResponse(BaseModel):
    id: UUID
    client_id: UUID
    artist_id: UUID
    status: BookingStatus
    idea_description: str
    body_part: str
    size_cm: Optional[str]
    booking_date: Optional[datetime]
    price_quote: Optional[float]
    client_accepted: bool
    artist_accepted: bool
    duration_hours: Optional[float] = None
    created_at: datetime
    class Config:
        from_attributes = True

class PostCreate(BaseModel):
    image_url: str
    description: Optional[str] = None
    style_tag: Optional[str] = None

class PostResponse(BaseModel):
    id: UUID
    artist_id: UUID
    image_url: str
    description: Optional[str]
    style_tag: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class PostUpdate(BaseModel):
    description: Optional[str] = None
    style_tag: Optional[str] = None

class ReviewCreate(BaseModel):
    booking_id: UUID
    rating: int
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: UUID
    reviewer_id: UUID
    artist_id: UUID
    rating: int
    comment: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class AIDesignCreate(BaseModel):
    prompt_text: str
    image_url: str
    style_tag: Optional[str] = None

class AIDesignResponse(BaseModel):
    id: UUID
    prompt_text: str
    image_url: str
    created_at: datetime
    class Config:
        from_attributes = True

# Mensajería 
class MessageCreate(BaseModel):
    receiver_id: UUID
    content: str
    booking_id: Optional[UUID] = None

class MessageResponse(BaseModel):
    id: UUID
    booking_id: Optional[UUID]
    sender_id: UUID
    receiver_id: UUID
    content: str
    is_read: bool
    created_at: datetime
    class Config:
        from_attributes = True

class ArtistUpdate(BaseModel):
    shop_name: Optional[str] = None
    bio: Optional[str] = None
    styles: Optional[List[str]] = None
    instagram_handle: Optional[str] = None
    
    # Ubicación
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    workspace_type: Optional[StudioType] = None
    
    # Documentos
    business_license_id: Optional[str] = None
    business_document_url: Optional[str] = None # Aquí irá la URL de la foto del certificado
    
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None

class ArtistResponse(BaseModel):
    id: UUID
    shop_name: str
    bio: Optional[str] = None
    styles: Optional[List[str]] = []
    
    # --- CAMPOS QUE FALTABAN ---
    latitude: float   # <--- IMPORTANTE: Sin esto, el mapa no sabe dónde poner el pin
    longitude: float  # <--- IMPORTANTE
    
    # Resto de campos
    address: Optional[str] = None
    workspace_type: Optional[str] = None 
    instagram_handle: Optional[str] = None
    
    is_verified: bool
    business_license_id: Optional[str] = None
    business_document_url: Optional[str] = None
    
    working_hours_start: Optional[str] = "09:00"
    working_hours_end: Optional[str] = "18:00"

    class Config:
        from_attributes = True