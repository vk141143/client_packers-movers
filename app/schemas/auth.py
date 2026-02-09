from pydantic import BaseModel, EmailStr, field_validator
from fastapi import UploadFile
from typing import Optional, Literal
import re

class ClientRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone_number: str
    client_type: str
    business_address: str
    otp_method: Literal["email", "phone"] = "email"

class Login(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class MessageResponse(BaseModel):
    message: str

class VerifyOTP(BaseModel):
    identifier: str  # email or phone
    otp: str

class ResendOTP(BaseModel):
    identifier: str  # email or phone
    otp_method: Literal["email", "phone"] = "email"

class UpdateClientProfile(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    business_address: Optional[str] = None

class ForgotPassword(BaseModel):
    identifier: str  # email or phone
    otp_method: Literal["email", "phone"] = "email"

class VerifyForgotOTP(BaseModel):
    identifier: str  # email or phone
    otp: str

class ResetPassword(BaseModel):
    reset_token: str
    new_password: str
    confirm_password: str
