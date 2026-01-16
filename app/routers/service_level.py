from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.service_level import ServiceLevel
from app.schemas.service_level import ServiceLevelResponse
from typing import List

router = APIRouter()

@router.get("/service-levels", response_model=List[ServiceLevelResponse], tags=["Service Levels"])
async def get_service_levels(db: Session = Depends(get_db)):
    service_levels = db.query(ServiceLevel).filter(ServiceLevel.is_active == True).all()
    return [ServiceLevelResponse(
        id=str(sl.id),
        name=sl.name,
        sla_hours=sl.sla_hours,
        price_gbp=sl.price_gbp,
        is_active=sl.is_active
    ) for sl in service_levels]
