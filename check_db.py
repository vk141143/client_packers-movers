from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
inspector = inspect(engine)

tables = inspector.get_table_names()
print('All tables:', tables)

print('\n=== Checking required columns ===')
conn = engine.connect()

for table in ['jobs', 'clients', 'payments']:
    try:
        result = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position"))
        cols = [row[0] for row in result]
        print(f'\n{table.upper()}: {", ".join(cols)}')
    except Exception as e:
        print(f'\n{table.upper()}: NOT FOUND - {e}')

conn.close()
