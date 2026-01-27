#test
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
from pathlib import Path
from dotenv import load_dotenv

# Get the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

# Load .env file from the project root
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)
    print(f"Loaded .env from: {ENV_FILE}")
else:
    print(f"Warning: .env file not found at {ENV_FILE}")
    load_dotenv(override=True)  # Try to load from current directory as fallback

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please check your .env file or environment variables.")

# Ensure we're using 'packers' database, not 'defaultdb'
if 'defaultdb' in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('defaultdb', 'packers')

print(f"Using DATABASE_URL: {DATABASE_URL[:50]}...")

# For async operations - convert psycopg2 to asyncpg if needed
async_url = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
async_engine = create_async_engine(async_url, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# For sync operations
sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
engine = create_engine(
    sync_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
    echo=False  # Disable SQL logging in production
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

async def init_db_async():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def init_db():
    print(f"Creating tables in database: {engine.url.database}")
    Base.metadata.create_all(bind=engine, checkfirst=True)

async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()