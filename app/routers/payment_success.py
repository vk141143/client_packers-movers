from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.payment import Payment
from app.models.job import Job
from app.models.client import Client
from sqlalchemy import text

router = APIRouter()

@router.get("/payment/success", tags=["Payment Success"])
async def payment_success_page(
    job_id: str = Query(...),
    type: str = Query(...),
    session_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Payment success page with job and payment details"""
    
    # Get payment details
    payment = db.query(Payment).filter(Payment.transaction_id == session_id).first()
    if not payment:
        return {
            "success": False,
            "message": "Payment session not found",
            "job_id": job_id,
            "payment_type": type
        }
    
    # Get job details
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return {
            "success": False,
            "message": "Job not found",
            "job_id": job_id
        }
    
    # Get client details
    client = db.query(Client).filter(Client.id == payment.client_id).first()
    
    # Get service type name
    service_type_name = "Property Clearance"
    if job.service_type:
        try:
            service_result = db.execute(
                text("SELECT name FROM service_types WHERE id = :id"),
                {"id": job.service_type}
            ).fetchone()
            if service_result:
                service_type_name = service_result[0]
        except:
            pass
    
    # Build response based on payment type
    if type == "deposit":
        return {
            "success": True,
            "payment_type": "Deposit Payment",
            "message": "Deposit payment successful! Your job has been confirmed.",
            "job_id": job_id,
            "payment_details": {
                "amount_paid": float(payment.amount),
                "payment_status": payment.payment_status,
                "payment_method": "Card",
                "transaction_id": payment.id
            },
            "job_details": {
                "service_type": service_type_name,
                "property_address": job.property_address,
                "scheduled_date": job.preferred_date,
                "scheduled_time": job.preferred_time,
                "total_quote": float(job.quote_amount) if job.quote_amount else 0.0,
                "deposit_paid": float(payment.amount),
                "remaining_amount": float(job.remaining_amount) if job.remaining_amount else 0.0
            },
            "next_steps": [
                "Admin will assign a crew to your job",
                "You'll receive updates as the crew progresses",
                "After job completion, you'll be asked to pay the remaining amount"
            ]
        }
    
    elif type == "remaining":
        return {
            "success": True,
            "payment_type": "Final Payment",
            "message": "Payment successful! Your job is now complete.",
            "job_id": job_id,
            "payment_details": {
                "amount_paid": float(payment.amount),
                "payment_status": payment.payment_status,
                "payment_method": "Card",
                "transaction_id": payment.id
            },
            "job_details": {
                "service_type": service_type_name,
                "property_address": job.property_address,
                "total_amount": float(job.quote_amount) if job.quote_amount else 0.0,
                "deposit_paid": float(job.deposit_amount) if job.deposit_amount else 0.0,
                "remaining_paid": float(payment.amount)
            },
            "next_steps": [
                "Your invoice has been generated",
                "You can download your invoice from the Invoices section",
                "Thank you for choosing our service!"
            ],
            "invoice_available": True
        }
    
    return {
        "success": True,
        "message": "Payment processed successfully",
        "job_id": job_id,
        "payment_type": type
    }
