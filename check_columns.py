import sys
sys.path.append('.')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'bookings' ORDER BY ordinal_position;"))
    columns = [row[0] for row in result]
    print('Columnas actuales en tabla bookings:')
    for col in columns:
        print(f'  - {col}')