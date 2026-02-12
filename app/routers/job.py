from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.job import Job
from app.models.client import Client
from app.schemas.job import CreateJob, JobResponse
from app.core.security import get_current_user
from app.core.pricing import calculate_job_price
from app.core.storage import storage
from app.core.location import geocode_address, haversine_distance
from typing import Optional, List
import os

router = APIRouter()

@router.post("/jobs", response_model=JobResponse, tags=["Jobs"], summary="Create Request")
async def create_request(
    service_type: Optional[str] = Form(None),
    urgency_level: Optional[str] = Form(None),
    property_size: Optional[str] = Form(None),
    van_loads: Optional[int] = Form(None),
    waste_types: Optional[str] = Form(None),
    furniture_items: Optional[int] = Form(None),
    property_address: Optional[str] = Form(None),
    preferred_date: Optional[str] = Form(None),
    preferred_time: Optional[str] = Form(None),
    additional_information: Optional[str] = Form(None),
    access_difficulty: Optional[str] = Form(None),
    property_photos: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if not service_type or not urgency_level or not property_address or not preferred_date or not preferred_time:
        raise HTTPException(status_code=400, detail="service_type, urgency_level, property_address, preferred_date, and preferred_time are required")
    
    # Get urgency level from database
    from app.models.urgency_level import UrgencyLevel
    urgency_level_obj = db.query(UrgencyLevel).filter(UrgencyLevel.id == urgency_level).first()
    if not urgency_level_obj:
        raise HTTPException(status_code=400, detail="Invalid urgency_level")
    
    image_paths = []
    if property_photos:
        for img in property_photos:
            if img.filename:
                try:
                    photo_url = storage.upload_client_job_photo(img.file, str(client.id), "temp_job", img.filename)
                    if photo_url:
                        image_paths.append(photo_url)
                except Exception as e:
                    print(f"Failed to upload photo {img.filename}: {e}")
    
    # Geocode job address
    lat, lon = geocode_address(property_address)
    
    job = Job(
        client_id=str(client.id),
        service_type=service_type,
        urgency_level=urgency_level,
        property_size=property_size,
        van_loads=van_loads,
        waste_types=waste_types,
        furniture_items=furniture_items,
        property_address=property_address,
        preferred_date=preferred_date,
        preferred_time=preferred_time,
        property_photos=",".join(image_paths) if image_paths else "",
        additional_information=additional_information,
        status='job_created',
        latitude=lat,
        longitude=lon
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Auto-assign to nearest available crew
    if lat and lon:
        from sqlalchemy import text
        crews = db.execute(
            text("SELECT id, email, full_name, latitude, longitude FROM crew WHERE status = 'available' AND is_approved = true AND latitude IS NOT NULL AND longitude IS NOT NULL")
        ).fetchall()
        
        if crews:
            nearest_crew = min(crews, key=lambda c: haversine_distance(lat, lon, c[3], c[4]))
            job.assigned_crew_id = nearest_crew[0]
            job.status = 'crew-dispatched'
            db.execute(text("UPDATE crew SET status = 'assigned' WHERE id = :crew_id"), {"crew_id": nearest_crew[0]})
            db.commit()
            db.refresh(job)
            
            # Send notification email
            from app.core.email import send_job_assignment_email
            send_job_assignment_email(nearest_crew[1], nearest_crew[2], job.id, property_address, preferred_date)
    
    return job

@router.get("/jobs", tags=["Jobs"], summary="Active Jobs - Currently in Progress")
async def get_all_requests(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import text
    from datetime import datetime, timedelta
    from app.models.service_type import ServiceType
    from app.models.urgency_level import UrgencyLevel
    
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    jobs = db.query(Job).filter(Job.client_id == str(client.id)).order_by(Job.created_at.desc()).all()
    
    result = []
    for job in jobs:
        # Get service type name
        service = db.query(ServiceType).filter(ServiceType.id == job.service_type).first()
        service_type_name = service.name if service else "Unknown Service"
        
        # Get SLA hours from urgency level
        sla_hours = 24  # default
        urgency_level = db.query(UrgencyLevel).filter(UrgencyLevel.id == job.urgency_level).first()
        if urgency_level:
            sla_hours = urgency_level.sla_hours
        
        # Calculate SLA status
        sla_deadline = job.created_at + timedelta(hours=sla_hours)
        now = datetime.utcnow()
        
        if job.status == "job_completed":
            # Completed job - check if completed within SLA
            if job.updated_at <= sla_deadline:
                sla_status = "SLA Met"
            else:
                sla_status = "SLA Breached"
        else:
            # Job in progress - show "On Track" if within SLA time
            if now <= sla_deadline:
                sla_status = "On Track"
            else:
                sla_status = "SLA Breached"
        
        result.append({
            "id": job.id,
            "service_type_name": service_type_name,
            "property_address": job.property_address,
            "preferred_date": job.preferred_date,
            "preferred_time": job.preferred_time,
            "price": job.quote_amount if job.quote_amount else 0.0,
            "status": job.status,
            "sla_status": sla_status,
            "created_at": job.created_at,
            "updated_at": job.updated_at
        })
    
    return result

@router.post("/jobs/{job_id}/rating", tags=["Jobs"])
async def submit_job_rating(
    job_id: str,
    rating: float = Form(...),
    review: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    job = db.query(Job).filter(Job.id == job_id, Job.client_id == str(client.id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "job_completed":
        raise HTTPException(status_code=400, detail="Can only rate completed jobs")
    
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    if job.rating is not None:
        raise HTTPException(status_code=400, detail="Job already rated")
    
    job.rating = rating
    db.commit()
    
    return {
        "message": "Rating submitted successfully",
        "job_id": job.id,
        "rating": rating
    }

@router.get("/jobs/{job_id}/rating", tags=["Jobs"])
async def get_job_rating(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    job = db.query(Job).filter(Job.id == job_id, Job.client_id == str(client.id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.id,
        "rating": job.rating,
        "has_rating": job.rating is not None
    }

@router.delete("/jobs/{job_id}/cancel", tags=["Jobs"])
async def cancel_job(
    job_id: str,
    cancellation_reason: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import text
    from app.models.payment import Payment
    
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    job = db.query(Job).filter(Job.id == job_id, Job.client_id == str(client.id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if deposit payment exists and is completed
    deposit_payment = db.query(Payment).filter(
        Payment.job_id == job_id,
        Payment.payment_type == "deposit",
        Payment.payment_status == "completed"
    ).first()
    
    if deposit_payment:
        raise HTTPException(
            status_code=400,
            detail=f"Cancellation not allowed. Deposit of £{deposit_payment.amount} has been paid and is non-refundable as per our cancellation policy. Please contact support for assistance."
        )
    
    # Only allow cancellation before crew uploads before photos
    cancellable_statuses = ['job_created', 'quote_sent', 'quote_accepted', 'crew_assigned', 'crew_dispatched', 'crew_arrived']
    if job.status not in cancellable_statuses:
        raise HTTPException(
            status_code=400, 
            detail="Job cannot be cancelled after crew has started work. Current status: " + job.status
        )
    
    # If crew was assigned, set them back to available
    if job.assigned_crew_id:
        db.execute(
            text("UPDATE crew SET status = 'available' WHERE id = :crew_id"),
            {"crew_id": job.assigned_crew_id}
        )
    
    job.status = 'cancelled'
    job.cancellation_reason = cancellation_reason
    db.commit()
    
    return {
        "message": "Job cancelled successfully. No charges applied.",
        "job_id": job.id,
        "status": job.status,
        "cancellation_reason": cancellation_reason
    }

@router.get("/client/quotes", tags=["Client"], summary="Get All Quotes for Client")
async def get_client_quotes(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    jobs = db.query(Job).filter(
        Job.client_id == str(client.id),
        Job.status.in_(["quote_sent", "quote_accepted", "quote_rejected"])
    ).order_by(Job.created_at.desc()).all()
    
    result = []
    for job in jobs:

        from app.models.service_type import ServiceType
        service = db.query(ServiceType).filter(ServiceType.id == job.service_type).first()
        service_type_name = service.name if service else "Unknown"
        
        quote_amount = job.quote_amount if job.quote_amount else 0.0
        deposit_amount = job.deposit_amount if job.deposit_amount else 0.0
        remaining_amount = quote_amount - deposit_amount
        
        result.append({
            "job_id": job.id,
            "property_address": job.property_address,
            "service_type": service_type_name,
            "preferred_date": job.preferred_date if job.preferred_date else "",
            "quote_amount": quote_amount,
            "deposit_amount": deposit_amount,
            "remaining_amount": remaining_amount,
            "quote_notes": job.quote_notes if job.quote_notes else "",
            "status": "Awaiting Approval" if job.status == "quote_sent" else job.status,
            "created_at": job.created_at.isoformat() if job.created_at else ""
        })
    
    return result

@router.get("/client/quotes/{job_id}", tags=["Client"], summary="Get Quote Details by ID")
async def get_quote_by_id(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.client_id == str(client.id)
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Get service type name
    from app.models.service_type import ServiceType
    service = db.query(ServiceType).filter(ServiceType.id == job.service_type).first()
    service_type_name = service.name if service else "Unknown"
    
    # Get urgency level name
    from app.models.urgency_level import UrgencyLevel
    urgency = db.query(UrgencyLevel).filter(UrgencyLevel.id == job.urgency_level).first()
    urgency_name = urgency.name if urgency else ""
    
    return {
        "job_id": job.id,
        "property_address": job.property_address,
        "service_type": service_type_name,
        "urgency_level": urgency_name,
        "preferred_date": job.preferred_date if job.preferred_date else "",
        "preferred_time": job.preferred_time if job.preferred_time else "",
        "quote_amount": job.quote_amount if job.quote_amount else 0.0,
        "deposit_amount": job.deposit_amount if job.deposit_amount else 0.0,
        "quote_notes": job.quote_notes if job.quote_notes else "",
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else ""
    }

@router.post("/client/quotes/{job_id}/approve", tags=["Client"], summary="Approve Quote")
async def approve_quote(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.client_id == str(client.id)
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    if job.status != "quote_sent":
        raise HTTPException(status_code=400, detail="Quote already processed")
    
    job.status = "quote_accepted"
    db.commit()
    
    return {
        "message": "Quote approved successfully",
        "job_id": job.id,
        "status": job.status
    }

@router.post("/client/quotes/{job_id}/decline", tags=["Client"], summary="Decline Quote")
async def decline_quote(
    job_id: str,
    decline_reason: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.client_id == str(client.id)
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    if job.status != "quote_sent":
        raise HTTPException(status_code=400, detail="Quote already processed")
    
    job.status = "quote_rejected"
    job.decline_reason = decline_reason
    db.commit()
    
    return {
        "message": "Quote declined",
        "job_id": job.id,
        "status": job.status,
        "decline_reason": decline_reason
    }

@router.get("/client/tracking", tags=["Client"], summary="Job Tracking - Get All Active Jobs")
async def get_job_tracking(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get all jobs including completed (exclude only cancelled)
    jobs = db.query(Job).filter(
        Job.client_id == str(client.id),
        Job.status != "cancelled"
    ).order_by(Job.created_at.desc()).all()
    
    result = []
    for job in jobs:
        # Get service type name
        from app.models.service_type import ServiceType
        service = db.query(ServiceType).filter(ServiceType.id == job.service_type).first()
        service_name = service.name if service else "Unknown"
        
        # Determine display status
        if job.status == "job_created":
            display_status = "Awaiting Quote"
        elif job.status == "quote_sent":
            display_status = "Quote Sent"
        elif job.status == "quote_accepted":
            display_status = "Booking Confirmed"
        elif job.status == "crew_assigned":
            display_status = "Crew Assigned"
        elif job.status == "crew_arrived":
            display_status = "Arrived at Property"
        elif job.status in ["before_photo", "clearance_in_progress", "after_photo"]:
            display_status = "Work Started"
        elif job.status == "work_completed":
            display_status = "Awaiting Final Payment"
        elif job.status == "job_completed":
            display_status = "Completed"
        else:
            display_status = job.status
        
        result.append({
            "job_id": job.id,
            "property_address": job.property_address,
            "service_type": service_name,
            "created_at": job.created_at.strftime("%m/%d/%Y") if job.created_at else "",
            "total_amount": job.quote_amount if hasattr(job, 'quote_amount') and job.quote_amount else 0.0,
            "scheduled_date": job.preferred_date if hasattr(job, 'preferred_date') and job.preferred_date else "",
            "status": display_status,
            "can_cancel": job.status in ["job_created", "quote_sent", "quote_accepted", "crew_assigned", "crew_arrived"]
        })
    
    return result

@router.get("/client/history", tags=["Client"], summary="Job History - Get All Completed Jobs")
async def get_job_history(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get all jobs (including active, completed, cancelled)
    jobs = db.query(Job).filter(
        Job.client_id == str(client.id)
    ).order_by(Job.created_at.desc()).all()
    
    result = []
    for job in jobs:
        from app.models.service_type import ServiceType
        from app.models.payment import Payment
        
        service = db.query(ServiceType).filter(ServiceType.id == job.service_type).first()
        service_name = service.name if service else "Unknown"
        
        # Check payment status
        deposit_payment = db.query(Payment).filter(
            Payment.job_id == job.id,
            Payment.payment_type == "deposit",
            Payment.payment_status == "succeeded"
        ).first()
        
        # Determine status badge
        if job.status == "job_created":
            status_badge = "Quote Pending"
            status_color = "warning"
        elif job.status == "quote_sent":
            status_badge = "Quote Sent"
            status_color = "info"
        elif job.status == "quote_accepted" and deposit_payment:
            status_badge = "Paid - Crew Assignment"
            status_color = "success"
        elif job.status == "quote_accepted":
            status_badge = "Awaiting Payment"
            status_color = "warning"
        elif job.status in ["crew_assigned", "crew_arrived"]:
            status_badge = "In Progress"
            status_color = "info"
        elif job.status in ["before_photo", "clearance_in_progress", "after_photo"]:
            status_badge = "Work In Progress"
            status_color = "info"
        elif job.status == "work_completed":
            status_badge = "Awaiting Final Payment"
            status_color = "warning"
        elif job.status == "job_completed":
            status_badge = "Paid - Invoice Generated"
            status_color = "success"
        elif job.status == "cancelled":
            status_badge = "Cancelled"
            status_color = "error"
        else:
            status_badge = job.status
            status_color = "default"
        
        # Build workflow progress
        workflow_steps = [
            {"name": "Request", "completed": True},
            {"name": "Quote", "completed": job.status not in ["job_created"]},
            {"name": "Payment", "completed": deposit_payment is not None},
            {"name": "Crew", "completed": job.assigned_crew_id is not None},
            {"name": "Work", "completed": job.status in ["before_photo", "clearance_in_progress", "after_photo", "work_completed", "job_verified", "payment_pending", "job_completed"]},
            {"name": "Complete", "completed": job.status == "job_completed"}
        ]
        
        result.append({
            "job_id": job.id,
            "service_type": service_name,
            "property_address": job.property_address,
            "scheduled_date": job.preferred_date if hasattr(job, 'preferred_date') and job.preferred_date else "",
            "status_badge": status_badge,
            "workflow_progress": workflow_steps
        })
    
    return result

@router.get("/client/completed-jobs", tags=["Client"], summary="Recently Completed Jobs")
async def get_completed_jobs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get completed jobs
    jobs = db.query(Job).filter(
        Job.client_id == str(client.id),
        Job.status == "job_completed"
    ).order_by(Job.updated_at.desc()).all()
    
    completed_jobs = []
    for job in jobs:
        # Get first property photo if available
        property_photo = None
        if job.property_photos:
            photos = job.property_photos.split(",")
            property_photo = photos[0] if photos else None
        
        completed_jobs.append({
            "job_id": job.id,
            "completion_date": job.updated_at.strftime("%d %b %Y") if job.updated_at else "",
            "property_photo": property_photo,
            "total_amount": float(job.quote_amount) if job.quote_amount else 0.0,
            "status": "Completed"
        })
    
    return completed_jobs

@router.get("/client/tracking/{job_id}", tags=["Client"], summary="Get Job Tracking Details by ID")
async def get_job_tracking_details(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import text
    
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.client_id == str(client.id)
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Determine display status
    if job.status == "job_created":
        display_status = "Awaiting Quote"
    elif job.status == "quote_sent":
        display_status = "Quote Sent"
    elif job.status == "quote_accepted":
        display_status = "Booking Confirmed"
    elif job.status == "crew_assigned":
        display_status = "Crew Assigned"
    elif job.status in ["crew_assigned", "crew_arrived", "before_photo", "clearance_in_progress", "after_photo"]:
        display_status = "Work In Progress"
    elif job.status == "work_completed":
        display_status = "Work Completed"
    elif job.status == "job_completed":
        display_status = "Job Completed"
    else:
        display_status = job.status
    
    # Build progress steps
    progress_steps = [
        {
            "step": 1,
            "title": "Crew Assigned",
            "completed": job.assigned_crew_id is not None
        },
        {
            "step": 2,
            "title": "Arrived at Property",
            "completed": job.status in ["crew_arrived", "before_photo", "clearance_in_progress", "after_photo", "work_completed", "job_verified", "payment_pending", "job_completed"]
        },
        {
            "step": 3,
            "title": "Work Started",
            "completed": job.status in ["before_photo", "clearance_in_progress", "after_photo", "work_completed", "job_verified", "payment_pending", "job_completed"]
        },
        {
            "step": 4,
            "title": "Work Completed",
            "completed": job.status in ["work_completed", "job_verified", "payment_pending", "job_completed"]
        }
    ]
    
    # Get crew details if assigned
    crew_details = None
    if job.assigned_crew_id:
        try:
            crew_result = db.execute(
                text("SELECT full_name, phone_number, email, vehicle_number FROM crew WHERE id = :id"),
                {"id": job.assigned_crew_id}
            ).fetchone()
            
            if crew_result:
                # Get crew rating (average of all completed jobs)
                rating_result = db.execute(
                    text("SELECT AVG(rating) FROM jobs WHERE assigned_crew_id = :id AND rating IS NOT NULL"),
                    {"id": job.assigned_crew_id}
                ).fetchone()
                
                crew_details = {
                    "name": crew_result[0],
                    "phone_number": crew_result[1],
                    "email": crew_result[2],
                    "vehicle_number": crew_result[3],
                    "rating": round(float(rating_result[0]), 1) if rating_result and rating_result[0] else None
                }
        except Exception as e:
            print(f"Error fetching crew details: {e}")
    
    # Get before and after photos
    before_photos = []
    after_photos = []
    try:
        photo_results = db.execute(
            text("SELECT photo_url, type FROM job_photos WHERE job_id = :job_id ORDER BY timestamp ASC"),
            {"job_id": job_id}
        ).fetchall()
        
        for photo in photo_results:
            if photo[1] == "before":
                before_photos.append(photo[0])
            elif photo[1] == "after":
                after_photos.append(photo[0])
    except Exception as e:
        print(f"Error fetching photos: {e}")
    
    return {
        "job_id": job.id,
        "property_address": job.property_address,
        "status": display_status,
        "progress": progress_steps,
        "crew_details": crew_details,
        "before_photos": before_photos,
        "after_photos": after_photos
    }

@router.get("/client/payment-requests", tags=["Client"], summary="Get Pending Payment Requests")
async def get_payment_requests(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get jobs with payment_pending status (admin sent remaining amount request)
    jobs = db.query(Job).filter(
        Job.client_id == str(client.id),
        Job.status == "payment_pending"
    ).order_by(Job.updated_at.desc()).all()
    
    result = []
    for job in jobs:
        deposit_paid = job.deposit_amount if job.deposit_amount else 0.0
        final_price = job.quote_amount if job.quote_amount else 0.0
        remaining_amount = final_price - deposit_paid
        
        result.append({
            "job_id": job.id,
            "property_address": job.property_address,
            "final_price": final_price,
            "deposit_paid": deposit_paid,
            "remaining_amount": remaining_amount,
            "completed_at": job.updated_at.isoformat() if job.updated_at else ""
        })
    
    return result

@router.get("/client/cancelled-jobs", tags=["Client"], summary="Get All Cancelled Jobs")
async def get_cancelled_jobs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    jobs = db.query(Job).filter(
        Job.client_id == str(client.id),
        Job.status.in_(["cancelled", "quote_rejected"])
    ).order_by(Job.updated_at.desc()).all()
    
    result = []
    for job in jobs:
        from app.models.service_type import ServiceType
        
        service = db.query(ServiceType).filter(ServiceType.id == job.service_type).first()
        service_name = service.name if service else "Unknown"
        
        # Determine reason and type
        if job.status == "cancelled":
            reason = job.cancellation_reason if job.cancellation_reason else ""
            status_type = "Cancelled"
        else:  # quote_rejected
            reason = job.decline_reason if hasattr(job, 'decline_reason') and job.decline_reason else ""
            status_type = "Quote Declined"
        
        result.append({
            "job_id": job.id,
            "service_type": service_name,
            "property_address": job.property_address,
            "preferred_date": job.preferred_date if job.preferred_date else "",
            "cancellation_reason": reason,
            "cancelled_at": job.updated_at.strftime("%d %b %Y") if job.updated_at else "",
            "quote_amount": job.quote_amount if job.quote_amount else 0.0,
            "status_type": status_type
        })
    
    return result

@router.get("/client/accepted-quotes", tags=["Client"], summary="Get All Accepted Quotes")
async def get_accepted_quotes(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    jobs = db.query(Job).filter(
        Job.client_id == str(client.id),
        Job.status.in_(["quote_accepted", "deposit_paid", "crew_assigned", "crew_arrived", "before_photo", "clearance_in_progress", "after_photo", "work_completed", "job_verified", "payment_pending", "job_completed"])
    ).order_by(Job.updated_at.desc()).all()
    
    result = []
    for job in jobs:
        from app.models.service_type import ServiceType
        from app.models.payment import Payment
        
        service = db.query(ServiceType).filter(ServiceType.id == job.service_type).first()
        service_name = service.name if service else "Unknown"
        
        # Check deposit payment status
        deposit_payment = db.query(Payment).filter(
            Payment.job_id == job.id,
            Payment.payment_type == "deposit",
            Payment.payment_status == "succeeded"
        ).first()
        
        result.append({
            "job_id": job.id,
            "service_type": service_name,
            "property_address": job.property_address,
            "preferred_date": job.preferred_date if job.preferred_date else "",
            "quote_amount": job.quote_amount if job.quote_amount else 0.0,
            "deposit_amount": job.deposit_amount if job.deposit_amount else 0.0,
            "deposit_paid": deposit_payment is not None,
            "accepted_at": job.updated_at.strftime("%d %b %Y") if job.updated_at else ""
        })
    
    return result
