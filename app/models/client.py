from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timedelta, timezone
from app.database.db import Base
import random
import secrets

class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    full_name = Column(String)
    company_name = Column(String)
    phone_number = Column(String)
    client_type = Column(String)
    address = Column(String)
    profile_photo = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    otp = Column(String)
    otp_expiry = Column(DateTime)
    otp_method = Column(String, nullable=True)
    reset_otp = Column(String, nullable=True)
    reset_otp_expiry = Column(DateTime, nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    invoices = relationship("Invoice", back_populates="client")

    @staticmethod
    def get_by_email(db, email: str):
        return db.query(Client).filter(Client.email == email).first()
    
    @staticmethod
    def create(db, email: str, password: str, full_name: str = None, company_name: str = None, phone_number: str = None, client_type: str = None, address: str = None, otp_method: str = "email"):
        otp = str(random.randint(1000, 9999))
        otp_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
        
        user = Client(
            email=email,
            password=password,
            full_name=full_name,
            company_name=company_name,
            phone_number=phone_number,
            client_type=client_type,
            address=address,
            is_verified=False,
            otp=otp,
            otp_expiry=otp_expiry,
            otp_method=otp_method
        )
        
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            return user.id, otp, otp_method
        except Exception as e:
            db.rollback()
            print(f"Error creating client: {e}")
            return None, None, None
    
    @staticmethod
    def verify_otp(db, identifier: str, otp: str):
        # Try email first
        user = db.query(Client).filter(Client.email == identifier).first()
        
        # If not found, try phone
        if not user:
            user = db.query(Client).filter(Client.phone_number == identifier).first()
        
        if not user:
            return False
        
        if user.otp == otp and datetime.now(timezone.utc).replace(tzinfo=None) < user.otp_expiry:
            user.is_verified = True
            user.otp = None
            user.otp_expiry = None
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def resend_otp(db, identifier: str, otp_method: str = "email"):
        # Try email first
        user = db.query(Client).filter(Client.email == identifier).first()
        
        # If not found, try phone
        if not user:
            user = db.query(Client).filter(Client.phone_number == identifier).first()
        
        if not user:
            return None, None
        
        if user.is_verified:
            return None, None
        
        otp = str(random.randint(1000, 9999))
        otp_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
        
        user.otp = otp
        user.otp_expiry = otp_expiry
        user.otp_method = otp_method
        db.commit()
        
        return otp, otp_method
