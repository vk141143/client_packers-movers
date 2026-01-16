from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.service import Service

router = APIRouter()

@router.get("/services", tags=["Services"])
def get_all_services(db: Session = Depends(get_db)):
    services = db.query(Service).all()
    return services

@router.get("/services/{service_id}", tags=["Services"])
def get_service_by_id(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service
