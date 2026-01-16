import psycopg2
from dotenv import load_dotenv
import os
from urllib.parse import unquote

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Parse and fix the connection string
db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")
db_url = unquote(db_url)

conn = psycopg2.connect(db_url)
cur = conn.cursor()

print("Adding missing columns to jobs table...")

# Read and execute the SQL file
with open("add_job_columns.sql", "r") as f:
    sql = f.read()
    cur.execute(sql)

conn.commit()
print("✓ Migration completed successfully!")

cur.close()
conn.close()
