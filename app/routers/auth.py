from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.schemas.auth import ClientRegister, Login, Token, MessageResponse, RefreshTokenRequest, VerifyOTP, UpdateClientProfile, ResendOTP, ForgotPassword, VerifyForgotOTP, ResetPassword
from app.models.client import Client
from app.database.db import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, verify_refresh_token, get_current_user
from app.core.email import send_otp_email
from app.core.sms import send_otp_sms
from app.core.storage import storage
import os

router = APIRouter()

@router.post("/register/client", response_model=MessageResponse, tags=["Authentication"])
async def register_client(client: ClientRegister, db: Session = Depends(get_db)):
    try:
        print(f"Registration attempt for: {client.email}")
        
        existing_client = Client.get_by_email(db, client.email)
        if existing_client:
            print(f"Email already exists: {client.email}")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        print(f"Creating client record...")
        result = Client.create(
            db=db,
            email=client.email,
            password=hash_password(client.password),
            full_name=client.full_name,
            company_name=client.company_name,
            phone_number=client.phone_number,
            client_type=client.client_type,
            address=client.address,
            otp_method=client.otp_method
        )
        
        print(f"Client.create result: {result}")
        
        if not result or not result[0]:
            print("Registration failed - Client.create returned None")
            raise HTTPException(status_code=400, detail="Registration failed - database error")
        
        user_id, otp, otp_method = result
        print(f"User created: ID={user_id}, OTP={otp}, Method={otp_method}")
        
        # Send OTP (non-blocking)
        try:
            if otp_method == "email":
                print(f"Sending OTP via email to {client.email}")
                send_otp_email(client.email, otp)
                return {"message": "Registration successful. OTP sent to your email."}
            else:
                print(f"Sending OTP via SMS to {client.phone_number}")
                send_otp_sms(client.phone_number, otp)
                return {"message": "Registration successful. OTP sent to your phone."}
        except Exception as email_error:
            print(f"Warning: Failed to send OTP: {email_error}")
            import traceback
            traceback.print_exc()
            return {"message": f"Registration successful. Your OTP is: {otp}"}
    
    except HTTPException as http_ex:
        print(f"HTTP Exception: {http_ex.detail}")
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/verify-otp", response_model=Token, summary="Verify Registration OTP", tags=["Authentication"])
async def verify_otp(data: VerifyOTP, db: Session = Depends(get_db)):
    if not Client.verify_otp(db, data.identifier, data.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Try email first
    user = Client.get_by_email(db, data.identifier)
    
    # If not found, try phone
    if not user:
        user = db.query(Client).filter(Client.phone_number == data.identifier).first()
    
    access_token = create_access_token(
        data={"sub": str(user.id), "role": "client"}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": "client"}
    )
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/resend-otp", response_model=MessageResponse, tags=["Authentication"])
async def resend_otp(data: ResendOTP, db: Session = Depends(get_db)):
    try:
        result = Client.resend_otp(db, data.identifier, data.otp_method)
        otp, otp_method = result
        
        if not otp:
            raise HTTPException(status_code=400, detail="User not found or already verified")
        
        # Try email first
        user = Client.get_by_email(db, data.identifier)
        
        # If not found, try phone
        if not user:
            user = db.query(Client).filter(Client.phone_number == data.identifier).first()
        
        if not user:
            raise HTTPException(status_code=400, detail="User not found")
        
        # Send OTP (non-blocking)
        try:
            if otp_method == "email":
                send_otp_email(user.email, otp)
                return {"message": "OTP sent to your email"}
            else:
                send_otp_sms(user.phone_number, otp)
                return {"message": "OTP sent to your phone"}
        except Exception as send_error:
            print(f"Warning: Failed to send OTP: {send_error}")
            return {"message": f"Your OTP is: {otp}"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Resend OTP error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resend OTP: {str(e)}")

@router.post("/login/client", response_model=Token, tags=["Authentication"])
async def login_client(credentials: Login, db: Session = Depends(get_db)):
    user = Client.get_by_email(db, credentials.email)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email first")
    
    if not verify_password(credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(
        data={"sub": str(user.id), "role": "client"}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": "client"}
    )
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token, tags=["Authentication"])
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = verify_refresh_token(request.refresh_token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user = db.query(Client).filter(Client.id == payload.get("sub")).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    access_token = create_access_token(
        data={"sub": str(user.id), "role": "client"}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "role": "client"}
    )
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.get("/client/profile", tags=["Client"])
async def get_client_profile(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "company_name": user.company_name,
        "phone_number": user.phone_number,
        "client_type": user.client_type,
        "address": user.address,
        "is_verified": user.is_verified,
        "created_at": user.created_at
    }

@router.patch("/client/profile", tags=["Client"])
async def update_client_profile(
    email: str = Form(None),
    phone_number: str = Form(None),
    address: str = Form(None),
    profile_photo: UploadFile = File(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not user:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if email:
        existing = Client.get_by_email(db, email)
        if existing and existing.id != user.id:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = email
    if phone_number:
        user.phone_number = phone_number
    if address:
        user.address = address
    if profile_photo and profile_photo.filename:
        photo_url = storage.upload_client_profile_photo(profile_photo.file, str(user.id), profile_photo.filename)
        user.profile_photo = photo_url
    
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "company_name": user.company_name,
        "phone_number": user.phone_number,
        "client_type": user.client_type,
        "address": user.address,
        "profile_photo": user.profile_photo,
        "is_verified": user.is_verified,
        "created_at": user.created_at
    }


@router.post("/forgot-password", response_model=MessageResponse, tags=["Authentication"])
async def forgot_password(data: ForgotPassword, db: Session = Depends(get_db)):
    try:
        import random
        from datetime import datetime, timedelta
        
        # Try email first
        user = Client.get_by_email(db, data.identifier)
        
        # If not found, try phone
        if not user:
            user = db.query(Client).filter(Client.phone_number == data.identifier).first()
        
        if user and user.is_verified:
            otp = str(random.randint(1000, 9999))
            user.reset_otp = otp
            user.reset_otp_expiry = datetime.utcnow() + timedelta(minutes=5)
            user.otp_method = data.otp_method
            db.commit()
            
            # Send OTP (non-blocking)
            try:
                if data.otp_method == "email":
                    send_otp_email(user.email, otp)
                else:
                    send_otp_sms(user.phone_number, otp)
            except Exception as send_error:
                print(f"Warning: Failed to send forgot password OTP: {send_error}")
        
        return {"message": "If account exists, OTP has been sent"}
    
    except Exception as e:
        print(f"Forgot password error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")

@router.post("/verify-forgot-otp", response_model=MessageResponse, tags=["Authentication"])
async def verify_forgot_otp(data: VerifyForgotOTP, db: Session = Depends(get_db)):
    import secrets
    from datetime import datetime, timedelta
    
    # Try email first
    user = Client.get_by_email(db, data.identifier)
    
    # If not found, try phone
    if not user:
        user = db.query(Client).filter(Client.phone_number == data.identifier).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    if not user.reset_otp or user.reset_otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    if user.reset_otp_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")
    
    reset_token = secrets.token_urlsafe(32)
    user.reset_token = reset_token
    user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=15)
    user.reset_otp = None
    user.reset_otp_expiry = None
    
    db.commit()
    
    return {"message": f"OTP verified. Reset token: {reset_token}"}

@router.post("/reset-password", response_model=MessageResponse, tags=["Authentication"])
async def reset_password(data: ResetPassword, db: Session = Depends(get_db)):
    from datetime import datetime
    
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    user = db.query(Client).filter(Client.reset_token == data.reset_token).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")
    
    if user.reset_token_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token expired")
    
    user.password = hash_password(data.new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    
    db.commit()
    
    return {"message": "Password reset successfully"}
