from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
import uuid
import models, database, auth
from utils.storage import upload_file_to_supabase
from datetime import datetime

router = APIRouter(prefix="/support", tags=["Support"])

@router.post("/feedback")
async def submit_feedback(
    message: str = Form(...),
    file: UploadFile = File(None),
    db: Session = Depends(database.get_db),
    current_user = Depends(auth.get_current_user)
):
    try:
        image_url = None
        
        # 1. Si el usuario ha mandado una captura de pantalla, la subimos al Storage
        if file:
            file_bytes = await file.read()
            # Generar nombre unico
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"feedback_{current_user.id}_{timestamp}_{file.filename}"
            
            image_url = upload_file_to_supabase(file_bytes, filename, folder="feedback_images")
            
            if not image_url:
                raise Exception("No se pudo subir la imagen a Supabase")

        # 2. Guardamos el reporte en la base de datos
        new_feedback = models.AppFeedback(
            user_id=current_user.id,
            message=message,
            image_url=image_url
        )
        db.add(new_feedback)
        db.commit()
        
        return {"status": "success", "detail": "Feedback recibido correctamente. ¡Gracias por ayudarnos a mejorar!"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error guardando el reporte: {str(e)}")
