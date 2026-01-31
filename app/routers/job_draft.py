from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.core.security import verify_token
from app.core.storage import storage
from app.models.job import Job
from app.models.urgency_level import UrgencyLevel
from app.schemas.job_draft import JobResponse, ConfirmJob
from app.schemas.auth import MessageResponse
from typing import List, Optional
from datetime import datetime
import json

router = APIRouter(prefix="/api/jobs", tags=["Job Draft"])
security = HTTPBearer()

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_draft(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get job draft by ID - no authentication required"""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobResponse(
            id=job.id,
            property_address=job.property_address,
            date=job.preferred_date,
            service_id=job.service_type,
            urgency_level_id=job.urgency_level,
            property_size=job.property_size,
            van_loads=job.van_loads,
            waste_types=job.waste_types,
            furniture_items=job.furniture_items,
            status=job.status,
            created_at=job.created_at.isoformat() if job.created_at else ""
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[JobResponse])
async def get_all_draft_jobs(
    db: Session = Depends(get_db)
):
    """Get all draft jobs (before login) - no authentication"""
    try:
        jobs = db.query(Job).filter(Job.client_id == None, Job.status == 'pending').order_by(Job.created_at.desc()).all()
        
        return [
            JobResponse(
                id=job.id,
                property_address=job.property_address,
                date=job.preferred_date,
                service_id=job.service_type,
                urgency_level_id=job.urgency_level,
                property_size=job.property_size,
                van_loads=job.van_loads,
                waste_types=job.waste_types,
                furniture_items=job.furniture_items,
                status=job.status,
                created_at=job.created_at.isoformat() if job.created_at else ""
            )
            for job in jobs
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/", response_model=JobResponse)
async def create_job_draft(
    property_address: Optional[str] = Form(None),
    preferred_date: Optional[str] = Form(None),
    service_type: Optional[str] = Form(None),
    urgency_level: Optional[str] = Form(None),
    property_size: Optional[str] = Form(None),
    van_loads: Optional[int] = Form(None),
    waste_types: Optional[str] = Form(None),
    furniture_items: Optional[int] = Form(None),
    property_photos: List[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Create job draft without authentication - for price estimation"""
    try:
        # Get urgency level from database
        urgency_level_obj = db.query(UrgencyLevel).filter(UrgencyLevel.id == urgency_level).first()
        if not urgency_level_obj:
            raise HTTPException(status_code=400, detail="Invalid urgency_level")
        
        # Create job first to get job_id
        job = Job(
            property_address=property_address,
            preferred_date=preferred_date,
            preferred_time="",
            service_type=service_type,
            urgency_level=urgency_level,
            property_size=property_size,
            van_loads=van_loads,
            waste_types=waste_types,
            furniture_items=furniture_items,
            status='pending'
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Upload property photos if provided
        photo_urls = []
        if property_photos:
            for photo in property_photos:
                if photo.filename:
                    file_content = await photo.read()
                    photo_url = storage.upload_file(
                        file_content,
                        f"job_drafts/{job.id}",
                        photo.filename
                    )
                    if photo_url:
                        photo_urls.append(photo_url)
        
        # Update job with photo URLs
        if photo_urls:
            job.property_photos = json.dumps(photo_urls)
            db.commit()
            db.refresh(job)
        
        return JobResponse(
            id=job.id,
            property_address=job.property_address,
            date=job.preferred_date,
            service_id=job.service_type,
            urgency_level_id=job.urgency_level,
            property_size=job.property_size,
            van_loads=job.van_loads,
            waste_types=job.waste_types,
            furniture_items=job.furniture_items,
            status=job.status,
            created_at=job.created_at.isoformat() if job.created_at else ""
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/confirm", response_model=MessageResponse)
async def confirm_job_draft(
    confirm_data: ConfirmJob,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Confirm job draft after client login - requires authentication"""
    try:
        payload = verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        job = db.query(Job).filter(Job.id == confirm_data.job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != "pending":
            raise HTTPException(status_code=400, detail="Job already confirmed")
        
        job.client_id = payload["sub"]
        job.status = "job_created"
        job.updated_at = datetime.utcnow()
        
        db.commit()
        return MessageResponse(message=f"Job confirmed successfully with ID: {job.id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
