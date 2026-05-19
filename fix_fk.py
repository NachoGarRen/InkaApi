import database
from sqlalchemy import text

db = database.SessionLocal()
try:
    # Drop the bad FK constraints pointing to auth.users
    db.execute(text("ALTER TABLE likes DROP CONSTRAINT IF EXISTS likes_user_id_fkey"))
    db.execute(text("ALTER TABLE favorites DROP CONSTRAINT IF EXISTS favorites_user_id_fkey"))
    
    # Add new FK constraints pointing to profiles(id)
    db.execute(text("ALTER TABLE likes ADD CONSTRAINT likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES profiles(id) ON DELETE CASCADE"))
    db.execute(text("ALTER TABLE favorites ADD CONSTRAINT favorites_user_id_fkey FOREIGN KEY (user_id) REFERENCES profiles(id) ON DELETE CASCADE"))
    
    db.commit()
    print("FK constraints migrated from auth.users -> profiles")
    
    # Verify
    result = db.execute(text(
        "SELECT conname, pg_get_constraintdef(c.oid) FROM pg_constraint c WHERE conrelid = 'likes'::regclass AND contype = 'f'"
    )).fetchall()
    print("=== LIKES FK (after) ===")
    for r in result:
        print(r)
    
    result2 = db.execute(text(
        "SELECT conname, pg_get_constraintdef(c.oid) FROM pg_constraint c WHERE conrelid = 'favorites'::regclass AND contype = 'f'"
    )).fetchall()
    print("=== FAVORITES FK (after) ===")
    for r in result2:
        print(r)

finally:
    db.close()
