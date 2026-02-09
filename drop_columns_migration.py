"""
Database migration script to drop contact_person_name, department, and company_name columns from clients table
Run this script once to update the production database
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

def drop_columns():
    try:
        # Parse connection string
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if columns exist before dropping
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'clients' 
            AND column_name IN ('contact_person_name', 'department', 'company_name')
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        if not existing_columns:
            print("✅ Columns already removed or don't exist")
            cursor.close()
            conn.close()
            return
        
        print(f"📋 Found columns to drop: {existing_columns}")
        
        # Drop contact_person_name column if exists
        if 'contact_person_name' in existing_columns:
            cursor.execute("ALTER TABLE clients DROP COLUMN IF EXISTS contact_person_name")
            print("✅ Dropped contact_person_name column")
        
        # Drop department column if exists
        if 'department' in existing_columns:
            cursor.execute("ALTER TABLE clients DROP COLUMN IF EXISTS department")
            print("✅ Dropped department column")
        
        # Drop company_name column if exists
        if 'company_name' in existing_columns:
            cursor.execute("ALTER TABLE clients DROP COLUMN IF EXISTS company_name")
            print("✅ Dropped company_name column")
        
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
    
    confirmation = input("\n⚠️  This will permanently drop contact_person_name, department, and company_name columns from clients table.\nType 'YES' to continue: ")
    
    if confirmation == "YES":
        drop_columns()
    else:
        print("❌ Migration cancelled")
