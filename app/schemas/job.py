#test
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CreateJob(BaseModel):
    service_type: str
    urgency_level: str
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
    service_type: str
    urgency_level: str
    property_size: Optional[str] = None
    van_loads: Optional[int] = None
    waste_types: Optional[str] = None
    furniture_items: Optional[int] = None
    property_address: str
    preferred_date: str
    preferred_time: str
    property_photos: Optional[str] = None
    additional_information: Optional[str] = None
    status: str
    rating: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
