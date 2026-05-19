import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
sys.path.append('f:\\DAM2\\PROYECTO\\Inka\\api')
from database import SQLALCHEMY_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def upgrade_enum():
    with engine.connect() as conn:
        try:
            conn.execute(sqlalchemy.text("ALTER TYPE booking_status ADD VALUE 'contactado';"))
            conn.execute(sqlalchemy.text("ALTER TYPE booking_status ADD VALUE 'aceptado';"))
            conn.execute(sqlalchemy.text("ALTER TYPE booking_status ADD VALUE 'rechazado';"))
            conn.execute(sqlalchemy.text("ALTER TYPE booking_status ADD VALUE 'finalizado';"))
            conn.commit()
            print("Enum updated successfully")
        except Exception as e:
            print(f"Error updating enum, it may already have these values: {e}")

if __name__ == "__main__":
    upgrade_enum()
