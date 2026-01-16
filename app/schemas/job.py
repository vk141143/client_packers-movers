from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CreateJob(BaseModel):
    service_type: str
    service_level: str
    property_size: Optional[str] = None
    van_loads: Optional[int] = None
    waste_types: Optional[str] = None
    furniture_items: Optional[int] = None
    property_address: str
    scheduled_date: str
    scheduled_time: str
    additional_notes: Optional[str] = None
    access_difficulty: Optional[str] = None
    compliance_addons: Optional[str] = None

class JobResponse(BaseModel):
    id: str
    client_id: Optional[str]
    assigned_crew_id: Optional[str] = None
    service_type: str
    service_level: str
    property_size: Optional[str] = None
    van_loads: Optional[int] = None
    waste_types: Optional[str] = None
    furniture_items: Optional[int] = None
    property_address: str
    scheduled_date: str
    scheduled_time: str
    property_photos: Optional[str] = None
    price: float
    additional_notes: Optional[str] = None
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
