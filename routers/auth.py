from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
# ### 1. IMPORTANTE: Importar OAuth2PasswordRequestForm
from fastapi.security import OAuth2PasswordRequestForm 
import database, models, schemas, auth

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    # Check if exists
    db_user = db.query(models.Profile).filter(models.Profile.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = auth.get_password_hash(user.password)
    new_user = models.Profile(email=user.email, password=hashed_pwd, full_name=user.full_name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=schemas.Token)
def login(
    # ### 2. CAMBIO: Usar OAuth2PasswordRequestForm en lugar de schemas.UserLogin
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(database.get_db)
):
    # ### 3. CAMBIO: Usar form_data.username (que contiene el email) y form_data.password
    user = db.query(models.Profile).filter(models.Profile.email == form_data.username).first()
    
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=403, detail="Invalid credentials")
    
    access_token = auth.create_access_token(data={"sub": user.email, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer"}