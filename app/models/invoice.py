from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.types import Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.db import Base
import uuid

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
    invoice_number = Column(String, unique=True, nullable=False)
    pdf_path = Column(String, nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String, default="generated")
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    client = relationship("Client", back_populates="invoices")