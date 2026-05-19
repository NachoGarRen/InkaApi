from database import engine
from sqlalchemy import text

def update_db():
    with engine.connect() as conn:
        print("Updating database schema...")
        try:
            conn.execute(text("ALTER TABLE artists ADD COLUMN IF NOT EXISTS working_hours_start VARCHAR DEFAULT '09:00'"))
            conn.execute(text("ALTER TABLE artists ADD COLUMN IF NOT EXISTS working_hours_end VARCHAR DEFAULT '18:00'"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS duration_hours FLOAT"))
            conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS fcm_token VARCHAR"))
            conn.commit()
            print("Database updated successfully!")
        except Exception as e:
            print(f"Error updating database: {e}")

if __name__ == "__main__":
    update_db()
