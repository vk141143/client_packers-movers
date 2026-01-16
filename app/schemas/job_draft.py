from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time

class CreateJob(BaseModel):
    property_address: str
    date: date
    time: time
    service_id: int
    service_level_id: str
    property_size: Optional[str] = None
    van_loads: Optional[int] = None
    waste_types: Optional[str] = None
    furniture_items: Optional[int] = None

class JobResponse(BaseModel):
    id: str
    property_address: str
    date: str
    time: str
    service_id: int
    service_level_id: str
    property_size: Optional[str] = None
    van_loads: Optional[int] = None
    waste_types: Optional[str] = None
    furniture_items: Optional[int] = None
    price: float
    status: str
    created_at: str
    
    class Config:
        from_attributes = True

class ConfirmJob(BaseModel):
    job_id: str
