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
    phone_number = Column(String)
    client_type = Column(String)
    business_address = Column(String)
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
    def create(db, email: str, password: str, full_name: str = None, phone_number: str = None, client_type: str = None, business_address: str = None, otp_method: str = "email"):
        # For phone OTP, don't store OTP in DB (Twilio generates it)
        if otp_method == "phone":
            otp = None
            otp_expiry = None
        else:
            # For email OTP, generate and store in DB
            otp = str(random.randint(100000, 999999))  # 6-digit OTP
            otp_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
        
        user = Client(
            email=email,
            password=password,
            full_name=full_name,
            phone_number=phone_number,
            client_type=client_type,
            business_address=business_address,
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
        print(f"[verify_otp] Checking identifier: {identifier}, OTP: {otp}")
        
        # Try email first
        user = db.query(Client).filter(Client.email == identifier).first()
        
        # If not found, try phone
        if not user:
            user = db.query(Client).filter(Client.phone_number == identifier).first()
        
        if not user:
            print(f"[verify_otp] User not found")
            return False
        
        print(f"[verify_otp] User found: {user.email}, OTP method: {user.otp_method}")
        print(f"[verify_otp] Stored OTP: {user.otp}, Expiry: {user.otp_expiry}")
        
        # If phone OTP, verify with Twilio
        if user.otp_method == "phone":
            print(f"[verify_otp] Using Twilio verification for phone: {user.phone_number}")
            from app.core.sms import verify_otp_sms
            if verify_otp_sms(user.phone_number, otp):
                user.is_verified = True
                user.otp = None
                user.otp_expiry = None
                db.commit()
                print(f"[verify_otp] Phone OTP verified successfully")
                return True
            print(f"[verify_otp] Phone OTP verification failed")
            return False
        
        # Email OTP - verify from database
        print(f"[verify_otp] Using database verification for email")
        if user.otp == otp and datetime.now(timezone.utc).replace(tzinfo=None) < user.otp_expiry:
            user.is_verified = True
            user.otp = None
            user.otp_expiry = None
            db.commit()
            print(f"[verify_otp] Email OTP verified successfully")
            return True
        
        print(f"[verify_otp] Email OTP verification failed - OTP mismatch or expired")
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
        
        # For phone OTP, don't store OTP in DB (Twilio generates it)
        if otp_method == "phone":
            otp = None
            otp_expiry = None
        else:
            # For email OTP, generate and store in DB
            otp = str(random.randint(100000, 999999))  # 6-digit OTP
            otp_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
        
        user.otp = otp
        user.otp_expiry = otp_expiry
        user.otp_method = otp_method
        db.commit()
        
        return otp, otp_method
