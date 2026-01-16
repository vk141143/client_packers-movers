from sqlalchemy import text
from app.database.db import engine

def add_otp_method_column():
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS otp_method VARCHAR(10)"))
        conn.commit()
        print("✅ otp_method column added to clients table")

if __name__ == "__main__":
    add_otp_method_column()
