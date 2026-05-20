import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Float, Text, DateTime, Enum, Numeric, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base
from pgvector.sqlalchemy import Vector

# --- ENUMS ---
class UserRole(str, enum.Enum):
    cliente = "cliente"
    artista = "artista"
    admin = "admin"

class BookingStatus(str, enum.Enum):
    pendiente = "pendiente"
    contactado = "contactado"
    aceptado = "aceptado"
    rechazado = "rechazado"
    finalizado = "finalizado"

# Nuevo Enum para el tipo de espacio de trabajo
class StudioType(str, enum.Enum):
    shop = "shop"       # Local comercial
    private = "private" # Estudio privado / Casa
    mobile = "mobile"   # Guest spot / Viajero

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    avatar_url = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.cliente)
    password = Column(String) 
    preference_embedding = Column(Vector(768), nullable=True) # Para el algoritmo de Feed
    fcm_token = Column(String, nullable=True) # Token para notificaciones push
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    artist_profile = relationship("Artist", back_populates="profile", uselist=False)
    bookings_as_client = relationship("Booking", back_populates="client", foreign_keys="Booking.client_id")
    # simulations, reviews_given, etc...

class Artist(Base):
    __tablename__ = "artists"
    id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), primary_key=True)
    
    # Info Básica
    shop_name = Column(String)
    bio = Column(Text)
    styles = Column(ARRAY(String)) 
    
    # Verificación y Contacto
    instagram_handle = Column(String) # Vital para validar portafolio
    whatsapp_number = Column(String, nullable=True)
    website_url = Column(String, nullable=True)
    
    # Documentación (Privado)
    business_license_id = Column(String, nullable=True) # DNI o CIF
    business_document_url = Column(String, nullable=True) # URL de la foto del certificado higiénico
    certificate_hash = Column(String, nullable=True) # Hash para evitar duplicados entre artistas
    is_verified = Column(Boolean, default=False) # Por defecto NADIE entra verificado
    
    # Ubicación Avanzada
    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    workspace_type = Column(Enum(StudioType), default=StudioType.shop)
    show_exact_location = Column(Boolean, default=True) # False = Privacidad (Estudios privados)
    
    # Horario Laboral
    working_hours_start = Column(String, default="09:00")
    working_hours_end = Column(String, default="18:00")

    # Relaciones
    profile = relationship("Profile", back_populates="artist_profile")
    posts = relationship("Post", back_populates="artist")
    bookings = relationship("Booking", back_populates="artist", foreign_keys="Booking.artist_id")

# ... (Booking, Post, Message se quedan igual) ...
class Post(Base):
    __tablename__ = "posts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artist_id = Column(UUID(as_uuid=True), ForeignKey("artists.id"), nullable=False)
    image_url = Column(String, nullable=False)
    description = Column(Text)
    style_tag = Column(String)
    ar_image_url = Column(String, nullable=True)
    embedding = Column(Vector(768), nullable=True)    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    artist = relationship("Artist", back_populates="posts")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    artist_id = Column(UUID(as_uuid=True), ForeignKey("artists.id"), nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.pendiente)
    idea_description = Column(Text, nullable=False)
    body_part = Column(String, nullable=False)
    size_cm = Column(String)
    price_quote = Column(Numeric, nullable=True)
    booking_date = Column(DateTime(timezone=True), nullable=True)
    duration_hours = Column(Float, nullable=True)
    client_accepted = Column(Boolean, default=False)
    artist_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    client = relationship("Profile", foreign_keys=[client_id])
    artist = relationship("Artist", foreign_keys=[artist_id])
    messages = relationship("Message", back_populates="booking")

class Message(Base):
    __tablename__ = "messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"))
    sender_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    booking = relationship("Booking", back_populates="messages")
    
# Añade Review y AIDesign aquí si no los tienes en el archivo original
class Review(Base):
    __tablename__ = "reviews"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"))
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    artist_id = Column(UUID(as_uuid=True), ForeignKey("artists.id"))
    rating = Column(Integer)
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AIDesign(Base):
    __tablename__ = "ai_designs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    prompt_text = Column(Text)
    image_url = Column(String, nullable=False)
    style_tag = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SearchCache(Base):
    __tablename__ = "search_cache"
    search_query = Column(String, primary_key=True)
    embedding = Column(Vector(768), nullable=False)
    search_count = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

from sqlalchemy import UniqueConstraint

class Like(Base):
    __tablename__ = "likes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('user_id', 'post_id', name='uix_user_post_like'),)

class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('user_id', 'post_id', name='uix_user_post_favorite'),)

class Follow(Base):
    __tablename__ = "follows"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    followed_id = Column(UUID(as_uuid=True), ForeignKey("artists.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('follower_id', 'followed_id', name='uix_follower_followed'),)

class AppFeedback(Base):
    __tablename__ = "app_feedback"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    message = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    status = Column(String, default="pendiente")
    created_at = Column(DateTime(timezone=True), server_default=func.now())