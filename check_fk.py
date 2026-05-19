import database
from sqlalchemy import text

db = database.SessionLocal()
try:
    result = db.execute(text(
        "SELECT conname, pg_get_constraintdef(c.oid) FROM pg_constraint c WHERE conrelid = 'likes'::regclass AND contype = 'f'"
    )).fetchall()
    print("=== LIKES FK ===")
    for r in result:
        print(r)
    
    result2 = db.execute(text(
        "SELECT conname, pg_get_constraintdef(c.oid) FROM pg_constraint c WHERE conrelid = 'favorites'::regclass AND contype = 'f'"
    )).fetchall()
    print("=== FAVORITES FK ===")
    for r in result2:
        print(r)

    # Also check if there is a "users" table
    tables = db.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )).fetchall()
    print("=== ALL TABLES ===")
    for t in tables:
        print(t[0])
finally:
    db.close()
