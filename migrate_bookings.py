import sys
sys.path.append('.')
from database import engine
from sqlalchemy import text

# Agregar las columnas faltantes a la tabla bookings
with engine.connect() as conn:
    try:
        # Agregar columna client_accepted
        conn.execute(text("ALTER TABLE bookings ADD COLUMN client_accepted BOOLEAN DEFAULT FALSE;"))
        print("✅ Columna client_accepted agregada")

        # Agregar columna artist_accepted
        conn.execute(text("ALTER TABLE bookings ADD COLUMN artist_accepted BOOLEAN DEFAULT FALSE;"))
        print("✅ Columna artist_accepted agregada")

        # Confirmar los cambios
        conn.commit()
        print("✅ Migración completada exitosamente")

    except Exception as e:
        print(f"❌ Error en la migración: {e}")
        conn.rollback()