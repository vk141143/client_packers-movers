from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.models.service_level import ServiceLevel

def seed_service_levels():
    db: Session = SessionLocal()
    
    service_levels_data = [
        {
            "name": "emergency_24h",
            "sla_hours": 24,
            "price_gbp": 2500
        },
        {
            "name": "standard_48h",
            "sla_hours": 48,
            "price_gbp": 1800
        },
        {
            "name": "scheduled_5_7_days",
            "sla_hours": 168,
            "price_gbp": 1200
        }
    ]
    
    for data in service_levels_data:
        existing = db.query(ServiceLevel).filter(ServiceLevel.name == data["name"]).first()
        if not existing:
            service_level = ServiceLevel(**data)
            db.add(service_level)
    
    db.commit()
    db.close()
    print("✅ Service levels seeded successfully")

if __name__ == "__main__":
    seed_service_levels()
