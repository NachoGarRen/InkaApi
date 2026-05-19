import os
import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session
import models

import json

# Inicializar Firebase Admin
cred_path = os.path.join(os.path.dirname(__file__), "..", "firebase-adminsdk.json")

# Intentar primero cargar desde la variable de entorno (Ideal para Koyeb/Render)
firebase_env = os.getenv("FIREBASE_CREDENTIALS_JSON")

if firebase_env:
    try:
        cred_dict = json.loads(firebase_env)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        print("[OK] Firebase Admin inicializado desde variable de entorno")
    except Exception as e:
        print(f"[ERROR] Error al parsear FIREBASE_CREDENTIALS_JSON: {e}")
elif os.path.exists(cred_path):
    # Fallback: archivo local (Para desarrollo local)
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    print("[OK] Firebase Admin inicializado desde archivo local")
else:
    print("[WARNING] No se encontraron credenciales de Firebase. Las notificaciones push no funcionaran.")

def send_push_notification(receiver_id: str, title: str, body: str, db: Session):
    """
    Envía una notificación push a un usuario específico usando su fcm_token.
    """
    user = db.query(models.Profile).filter(models.Profile.id == receiver_id).first()
    
    if not user or not user.fcm_token:
        print(f"[INFO] No se puede enviar notificacion: Usuario {receiver_id} no tiene fcm_token")
        return

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=user.fcm_token,
        # Opcional: añadir datos para que la app sepa qué abrir
        data={
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
            "type": "chat_message",
        }
    )

    try:
        response = messaging.send(message)
        print(f"[OK] Notificacion enviada con exito: {response}")
    except Exception as e:
        print(f"[ERROR] Error al enviar notificacion: {e}")
