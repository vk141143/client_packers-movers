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

@router.post("/jobs", response_model=JobResponse, tags=["Jobs"])
async def create_job(
    service_type: Optional[str] = Form(None),
    service_level: Optional[str] = Form(None),
    property_size: Optional[str] = Form(None),
    van_loads: Optional[int] = Form(None),
    waste_types: Optional[str] = Form(None),
    furniture_items: Optional[int] = Form(0),
    property_address: Optional[str] = Form(None),
    scheduled_date: Optional[str] = Form(None),
    scheduled_time: Optional[str] = Form(None),
    additional_notes: Optional[str] = Form(None),
    access_difficulty: Optional[str] = Form(None),
    compliance_addons: Optional[str] = Form(None),
    property_photos: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if not service_type or not service_level or not property_address or not scheduled_date or not scheduled_time:
        raise HTTPException(status_code=400, detail="service_type, service_level, property_address, scheduled_date, and scheduled_time are required")
    
    # Get service level name from database
    from app.models.service_level import ServiceLevel
    service_level_obj = db.query(ServiceLevel).filter(ServiceLevel.id == service_level).first()
    if not service_level_obj:
        raise HTTPException(status_code=400, detail="Invalid service_level")
    
    # Get service level price directly from database
    service_level_price = float(service_level_obj.price_gbp) if service_level_obj.price_gbp else 0.0
    
    # Parse access difficulty and compliance addons
    access_list = [a.strip().lower() for a in access_difficulty.split(",")] if access_difficulty else []
    compliance_list = [c.strip().lower().replace(" ", "_") for c in compliance_addons.split(",")] if compliance_addons else []
    
    print(f"DEBUG - service_level: {service_level_obj.name} -> price: £{service_level_price}")
    print(f"DEBUG - property_size: {property_size}")
    print(f"DEBUG - van_loads: {van_loads}")
    print(f"DEBUG - waste_types: {waste_types}")
    print(f"DEBUG - furniture_items: {furniture_items}")
    print(f"DEBUG - access_list: {access_list}")
    print(f"DEBUG - compliance_list: {compliance_list}")
    
    # Calculate price using component-based pricing
    price = calculate_job_price(
        property_size=property_size or "2bed",
        van_loads=van_loads or 1,
        waste_type=waste_types or "general",
        furniture_items=furniture_items or 0,
        access_difficulty=access_list,
        compliance_addons=compliance_list,
        urgency="standard"  # Not used anymore
    )
    
    # Add service level price from database
    price += service_level_price
    
    print(f"DEBUG - calculated price: {price}")
    
    image_paths = []
    if property_photos:
        for img in property_photos:
            if img.filename:
                photo_url = storage.upload_client_job_photo(img.file, str(client.id), "temp_job", img.filename)
                if photo_url:
                    image_paths.append(photo_url)
    
    # Geocode job address
    lat, lon = geocode_address(property_address)
    
    job = Job(
        client_id=str(client.id),
        service_type=service_type,
        service_level=service_level,
        property_size=property_size,
        van_loads=van_loads,
        waste_types=waste_types,
        furniture_items=furniture_items,
        property_address=property_address,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        property_photos=",".join(image_paths) if image_paths else None,
        price=price,
        additional_notes=additional_notes,
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
            send_job_assignment_email(nearest_crew[1], nearest_crew[2], job.id, property_address, scheduled_date)
    
    return job

@router.get("/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
async def get_job(
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
    
    return job

@router.get("/jobs", response_model=List[JobResponse], tags=["Jobs"])
async def get_all_jobs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    jobs = db.query(Job).filter(Job.client_id == str(client.id)).all()
    return jobs

@router.get("/client/assigned-crew", tags=["Client"])
async def get_assigned_crew(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import text
    
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get active job with assigned crew
    job = db.query(Job).filter(
        Job.client_id == str(client.id),
        Job.assigned_crew_id.isnot(None),
        Job.status.notin_(['job_completed', 'cancelled'])
    ).order_by(Job.created_at.desc()).first()
    
    if not job or not job.assigned_crew_id:
        return {"crew": None}
    
    crew = db.execute(
        text("SELECT id, full_name, email, phone_number, latitude, longitude FROM crew WHERE id = :crew_id"),
        {"crew_id": job.assigned_crew_id}
    ).fetchone()
    
    if not crew:
        return {"crew": None}
    
    # Get completed jobs count and average rating
    completed_count = db.execute(
        text("SELECT COUNT(*) FROM jobs WHERE assigned_crew_id = :crew_id AND status = 'job_completed'"),
        {"crew_id": crew[0]}
    ).scalar()
    
    # Calculate average rating (if rating column exists)
    avg_rating = db.execute(
        text("SELECT AVG(rating) FROM jobs WHERE assigned_crew_id = :crew_id AND status = 'job_completed' AND rating IS NOT NULL"),
        {"crew_id": crew[0]}
    ).scalar()
    
    rating = round(float(avg_rating), 1) if avg_rating else 4.8
    
    # Reverse geocode crew location
    location = "Unknown"
    if crew[4] and crew[5]:
        from geopy.geocoders import Nominatim
        try:
            geolocator = Nominatim(user_agent="emergency_clearance")
            loc = geolocator.reverse(f"{crew[4]}, {crew[5]}")
            if loc and loc.address:
                parts = loc.address.split(',')
                location = parts[-3].strip() if len(parts) >= 3 else parts[0].strip()
        except:
            location = "Unknown"
    
    return {
        "crew": {
            "name": crew[1],
            "email": crew[2],
            "phone": crew[3] or "+44 7700 900124",
            "location": location,
            "rating": rating,
            "jobs_completed": completed_count or 0
        }
    }

@router.get("/jobs/{job_id}/details", tags=["Jobs"])
async def get_job_details(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import text
    from app.models.service import Service
    from app.models.service_level import ServiceLevel
    from app.models.invoice import Invoice
    
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    job = db.query(Job).filter(Job.id == job_id, Job.client_id == str(client.id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get service name
    service = db.query(Service).filter(Service.id == job.service_type).first()
    service_name = service.name if service else job.service_type
    
    # Get service level name
    service_level = db.query(ServiceLevel).filter(ServiceLevel.id == job.service_level).first()
    sla_name = service_level.name if service_level else job.service_level
    
    # Get assigned crew names
    crew_names = "Not assigned"
    if job.assigned_crew_id:
        crew_result = db.execute(
            text("SELECT full_name FROM crew WHERE id = :crew_id"),
            {"crew_id": job.assigned_crew_id}
        ).fetchone()
        if crew_result:
            crew_names = crew_result[0]
    
    # Get invoice details
    invoice = db.query(Invoice).filter(Invoice.job_id == job_id).first()
    invoice_data = None
    if invoice:
        invoice_data = {
            "invoice_id": invoice.invoice_number,
            "amount": float(invoice.amount),
            "status": invoice.status,
            "pdf_path": invoice.pdf_path
        }
    
    return {
        "job_id": job.id,
        "service_type": service_name,
        "sla_type": sla_name,
        "property_address": job.property_address,
        "scheduled_date": job.scheduled_date,
        "scheduled_time": job.scheduled_time,
        "booking_date": job.created_at.strftime("%d/%m/%Y, %H:%M:%S") if job.created_at else None,
        "completion_date": job.updated_at.strftime("%d/%m/%Y, %H:%M:%S") if job.status == "job_completed" and job.updated_at else None,
        "assigned_crew": crew_names,
        "job_status": job.status,
        "invoice": invoice_data
    }

@router.get("/jobs/completed/all", tags=["Jobs"])
async def get_all_completed_jobs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import text
    from app.models.service import Service
    from app.models.service_level import ServiceLevel
    from app.models.invoice import Invoice
    
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    jobs = db.query(Job).filter(
        Job.client_id == str(client.id),
        Job.status == "job_completed"
    ).order_by(Job.updated_at.desc()).all()
    
    result = []
    for job in jobs:
        # Get service name
        service = db.query(Service).filter(Service.id == job.service_type).first()
        service_name = service.name if service else job.service_type
        
        # Get service level name
        service_level = db.query(ServiceLevel).filter(ServiceLevel.id == job.service_level).first()
        sla_name = service_level.name if service_level else job.service_level
        
        # Get assigned crew names
        crew_names = "Not assigned"
        if job.assigned_crew_id:
            crew_result = db.execute(
                text("SELECT full_name FROM crew WHERE id = :crew_id"),
                {"crew_id": job.assigned_crew_id}
            ).fetchone()
            if crew_result:
                crew_names = crew_result[0]
        
        # Get invoice details
        invoice = db.query(Invoice).filter(Invoice.job_id == job.id).first()
        invoice_data = None
        if invoice:
            invoice_data = {
                "invoice_id": invoice.invoice_number,
                "amount": float(invoice.amount),
                "status": invoice.status
            }
        
        result.append({
            "job_id": job.id,
            "service_type": service_name,
            "sla_type": sla_name,
            "property_address": job.property_address,
            "scheduled_date": job.scheduled_date,
            "scheduled_time": job.scheduled_time,
            "booking_date": job.created_at.strftime("%d/%m/%Y, %H:%M:%S") if job.created_at else None,
            "completion_date": job.updated_at.strftime("%d/%m/%Y, %H:%M:%S") if job.updated_at else None,
            "assigned_crew": crew_names,
            "job_status": job.status,
            "invoice": invoice_data
        })
    
    return {"jobs": result, "total": len(result)}

@router.get("/jobs/{job_id}/invoice/download", tags=["Jobs"])
async def download_invoice(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from fastapi.responses import StreamingResponse
    from app.models.invoice import Invoice
    import io
    
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    job = db.query(Job).filter(Job.id == job_id, Job.client_id == str(client.id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "job_completed":
        raise HTTPException(status_code=400, detail="Invoice only available for completed jobs")
    
    invoice = db.query(Invoice).filter(Invoice.job_id == job_id).first()
    if not invoice or not invoice.pdf_path:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Download from bucket
    pdf_content = storage.download_file(invoice.pdf_path)
    if not pdf_content:
        raise HTTPException(status_code=404, detail="Invoice file not found in storage")
    
    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={invoice.invoice_number}.pdf"}
    )

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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    job = db.query(Job).filter(Job.id == job_id, Job.client_id == str(client.id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    cancellable_statuses = ['job_created', 'crew_assigned', 'crew_dispatched', 'crew_arrived', 'before_photo']
    if job.status not in cancellable_statuses:
        raise HTTPException(
            status_code=400, 
            detail="Job cannot be cancelled after OTP verification. Current status: " + job.status
        )
    
    job.status = 'cancelled'
    db.commit()
    
    return {
        "message": "Job cancelled successfully",
        "job_id": job.id,
        "status": job.status
    }
