"""
Database migration script to add profile_photo column to clients table
"""

import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv
import urllib.parse

# Get the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# Load .env file from the project root
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)
    print(f"Loaded .env from: {ENV_FILE}")
else:
    print(f"Warning: .env file not found at {ENV_FILE}")
    load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment variables")
    exit(1)

# Convert to standard postgresql:// format and decode URL encoding
if DATABASE_URL.startswith("postgresql+psycopg2://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
elif DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Decode URL-encoded password
DATABASE_URL = urllib.parse.unquote(DATABASE_URL)

def add_profile_photo_column():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'clients' 
            AND column_name = 'profile_photo'
        """)
        
        if cursor.fetchone():
            print("✅ profile_photo column already exists")
            cursor.close()
            conn.close()
            return
        
        # Add profile_photo column
        cursor.execute("ALTER TABLE clients ADD COLUMN profile_photo VARCHAR")
        print("✅ Added profile_photo column to clients table")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Migration completed successfully")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Starting database migration...")
    print(f"📊 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'Unknown'}")
    
    confirmation = input("\n⚠️  This will add profile_photo column to clients table.\nType 'YES' to continue: ")
    
    if confirmation == "YES":
        add_profile_photo_column()
    else:
        print("❌ Migration cancelled")
