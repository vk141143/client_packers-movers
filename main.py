from fastapi import FastAPI
from fastapi.security import HTTPBearer
from app.routers import auth, service, job, service_level, invoice, job_draft, pricing
from app.database.db import init_db, engine
from app.models.client import Client
from app.models.service import Service
from app.models.service_level import ServiceLevel
from app.models.job import Job
from app.models.invoice import Invoice
from sqlalchemy import text

app = FastAPI(
    title="Emergency Property Clearance API",
    version="1.0.0",
    description="FastAPI backend for UK-based Emergency Property Clearance & Operations platform"
)

app.include_router(auth.router, prefix="/api/auth")
app.include_router(service.router, prefix="/api")
app.include_router(job_draft.router)
app.include_router(job.router, prefix="/api")
app.include_router(service_level.router, prefix="/api")
app.include_router(invoice.router, prefix="/api")
app.include_router(pricing.router, prefix="/api")

@app.on_event("startup")
def startup():
    try:
        # Test connection using sync engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connected successfully")
        
        # Create tables if they don't exist
        init_db()  # Create tables
        print("Tables created successfully")
        
        # Add default services
        from sqlalchemy.orm import Session
        db = Session(bind=engine)
        try:
            if db.query(Service).count() == 0:
                services = [
                    Service(name="Emergency", description="Emergency property clearance services"),
                    Service(name="Void Property", description="Void property clearance and cleaning"),
                    Service(name="Hoarder Clean", description="Professional hoarder property cleaning"),
                    Service(name="Fire/Flood", description="Fire and flood damage clearance")
                ]
                db.add_all(services)
                db.commit()
                print("Default services added")
            
            # Add service levels
            if db.query(ServiceLevel).count() == 0:
                service_levels = [
                    ServiceLevel(name="emergency_24h", sla_hours=24, price_gbp=2500),
                    ServiceLevel(name="standard_48h", sla_hours=48, price_gbp=1800),
                    ServiceLevel(name="scheduled_5_7_days", sla_hours=168, price_gbp=1200)
                ]
                db.add_all(service_levels)
                db.commit()
                print("Service levels added")
        except Exception as data_error:
            print(f"Data initialization failed: {data_error}")
        finally:
            db.close()
    except Exception as e:
        print(f"Database connection failed: {e}")

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
