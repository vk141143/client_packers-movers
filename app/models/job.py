from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Boolean
from datetime import datetime, timezone
from app.database.db import Base
import uuid

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, nullable=True)
    assigned_crew_id = Column(String, nullable=True)
    service_type = Column(String, nullable=False)
    service_level = Column(String, nullable=False)
    property_size = Column(String, nullable=True)
    van_loads = Column(Integer, nullable=True)
    waste_types = Column(Text, nullable=True)
    furniture_items = Column(Integer, nullable=True)
    property_address = Column(Text, nullable=False)
    scheduled_date = Column(String, nullable=False)
    scheduled_time = Column(String, nullable=False)
    property_photos = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    additional_notes = Column(Text, nullable=True)
    status = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
