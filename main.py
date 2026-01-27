#test
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy import text

# CRITICAL: Import ALL models BEFORE any database operations
from app.models.client import Client
from app.models.urgency_level import UrgencyLevel
from app.models.service_type import ServiceType
from app.models.waste_type import WasteType
from app.models.access_difficulty import AccessDifficulty
from app.models.job import Job
from app.models.invoice import Invoice
from app.models.payment import Payment

# Import database AFTER models are loaded
from app.database.db import init_db, engine, Base

# Import routers last
from app.routers import auth, job, urgency_level, invoice, job_draft, pricing, service_type, waste_type, access_difficulty

app = FastAPI(
    title="Emergency Property Clearance API",
    version="1.0.0",
    description="FastAPI backend for UK-based Emergency Property Clearance & Operations platform"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth")
app.include_router(job_draft.router)
app.include_router(job.router, prefix="/api")
app.include_router(urgency_level.router, prefix="/api")
app.include_router(service_type.router, prefix="/api")
app.include_router(waste_type.router, prefix="/api")
app.include_router(access_difficulty.router, prefix="/api")
app.include_router(invoice.router, prefix="/api")
app.include_router(pricing.router, prefix="/api")

@app.on_event("startup")
def startup():
    try:
        print(f"🔍 Registered tables: {list(Base.metadata.tables.keys())}")
        
        with engine.connect() as conn:
            # Check which database we're connected to
            db_name = conn.execute(text("SELECT current_database()")).scalar()
            print(f"📊 Connected to database: {db_name}")
            
            # Check if clients table exists
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'clients')"
            ))
            table_exists = result.scalar()
            print(f"🔍 Clients table exists: {table_exists}")
            
        print("✅ Database connected")
        
        init_db()
        print("✅ Tables created")
        
        # Verify clients table exists
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'clients'"
            ))
            if result.fetchone():
                print("✅ Clients table verified")
            else:
                print("⚠️ Clients table NOT found!")
        
        # Add default services
        from sqlalchemy.orm import Session
        db = Session(bind=engine)
        try:
            # Add service types
            if db.query(ServiceType).count() == 0:
                service_types = [
                    ServiceType(name="Emergency Clearance", description="Urgent same-day service"),
                    ServiceType(name="House Clearance", description="Full property clearance"),
                    ServiceType(name="Office Clearance", description="Commercial spaces"),
                    ServiceType(name="Garden Clearance", description="Outdoor waste removal")
                ]
                db.add_all(service_types)
                db.commit()
                print("✅ Service types added")
            
            # Add waste types
            if db.query(WasteType).count() == 0:
                waste_types = [
                    WasteType(name="General waste", description="Household items"),
                    WasteType(name="Furniture/appliances", description="Large items"),
                    WasteType(name="Garden waste", description="Green waste"),
                    WasteType(name="Construction waste", description="Building materials"),
                    WasteType(name="Hazardous waste", description="Special handling"),
                    WasteType(name="Electronic waste", description="WEEE items")
                ]
                db.add_all(waste_types)
                db.commit()
                print("✅ Waste types added")
            
            # Add access difficulties
            if db.query(AccessDifficulty).count() == 0:
                access_difficulties = [
                    AccessDifficulty(name="Ground floor", description="Easy access"),
                    AccessDifficulty(name="Stairs (no lift)", description="Manual carrying"),
                    AccessDifficulty(name="Restricted parking", description="Limited vehicle access"),
                    AccessDifficulty(name="Long carry distance", description="Extended walking")
                ]
                db.add_all(access_difficulties)
                db.commit()
                print("✅ Access difficulties added")
            
            # Add urgency levels
            if db.query(UrgencyLevel).count() == 0:
                urgency_levels = [
                    UrgencyLevel(name="Standard", sla_hours=72),
                    UrgencyLevel(name="Urgent", sla_hours=48),
                    UrgencyLevel(name="Emergency", sla_hours=24)
                ]
                db.add_all(urgency_levels)
                db.commit()
                print("✅ Urgency levels added")
        except Exception as data_error:
            print(f"⚠️ Data initialization failed: {data_error}")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()

@app.get("/")
def root():
    return {
        "message": "Emergency Property Clearance API - Client Portal",
        "status": "running",
        "version": "1.0.0",
        "port": 8000
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
