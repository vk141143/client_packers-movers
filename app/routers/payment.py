from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.client import Client
from app.models.payment import Payment
from app.core.security import get_current_user
from app.core.payment import create_checkout_session, verify_payment
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import text
import os

router = APIRouter()

class ConfirmPaymentRequest(BaseModel):
    session_id: str

def get_frontend_url(request: Request) -> str:
    """Get frontend URL from request origin - works for both local and production"""
    # Get origin from request headers (where frontend is running)
    origin = request.headers.get("origin")
    
    # Allowed frontend origins
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "https://ui-packers-y8cjd.ondigitalocean.app",
        "https://client.voidworksgroup.co.uk",
        "https://www.voidworksgroup.co.uk",
        "https://voidworksgroup.co.uk"
    ]
    
    # Use origin if allowed, else fallback to production
    if origin and origin in allowed_origins:
        return origin
    
    # Fallback to production frontend URL
    return "https://client.voidworksgroup.co.uk"

@router.post("/client/jobs/{job_id}/create-deposit-payment", tags=["Client Payment"])
async def create_deposit_payment(
    job_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    identifier = current_user["sub"]
    client = db.query(Client).filter(Client.email == identifier).first()
    if not client:
        try:
            client = db.query(Client).filter(Client.id == identifier).first()
        except:
            pass
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    try:
        job_result = db.execute(
            text("SELECT id, client_id, quote_amount, deposit_amount, status FROM jobs WHERE id = :job_id"),
            {"job_id": job_id}
        ).fetchone()
        
        if not job_result:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job_result[1] != str(client.id):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        if job_result[4] not in ["quote_accepted", "deposit_paid", "crew_assigned"]:
            raise HTTPException(status_code=400, detail=f"Cannot create payment. Current status: {job_result[4]}")
        
        # Check if deposit already paid
        existing_payment = db.query(Payment).filter(
            Payment.job_id == job_id,
            Payment.payment_type == "deposit",
            Payment.payment_status == "succeeded"
        ).first()
        if existing_payment:
            raise HTTPException(status_code=400, detail="Deposit already paid")
        
        deposit_amount = job_result[3]
        if not deposit_amount or deposit_amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid deposit amount")
        
        frontend_url = get_frontend_url(request)
        payment_data = create_checkout_session(
            amount=deposit_amount,
            metadata={"job_id": job_id, "client_id": str(client.id), "payment_type": "deposit"},
            success_url=f"{frontend_url}/#/payments?session_id={{CHECKOUT_SESSION_ID}}&status=success",
            cancel_url=f"{frontend_url}/#/payments?status=cancel"
        )
        
        payment = Payment(
            job_id=job_id,
            client_id=str(client.id),
            payment_type="deposit",
            amount=deposit_amount,
            payment_method="stripe",
            transaction_id=payment_data["session_id"],
            payment_status="pending"
        )
        db.add(payment)
        db.commit()
        
        return {"checkout_url": payment_data["checkout_url"]}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.post("/client/payments/confirm-deposit", tags=["Client Payment"])
async def confirm_deposit_payment(
    request: ConfirmPaymentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    identifier = current_user["sub"]
    client = db.query(Client).filter(Client.email == identifier).first()
    if not client:
        try:
            client = db.query(Client).filter(Client.id == identifier).first()
        except:
            pass
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    payment = db.query(Payment).filter(
        Payment.transaction_id == request.session_id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment session not found. Please contact support.")
    
    # Compare client IDs (handle both UUID and string formats)
    payment_client_id = str(payment.client_id)
    current_client_id = str(client.id)
    
    if payment_client_id != current_client_id:
        raise HTTPException(status_code=403, detail=f"Payment belongs to different client")
    
    if payment.payment_status == "succeeded":
        return {
            "message": "Payment already confirmed",
            "payment_id": payment.id,
            "amount": payment.amount,
            "job_id": payment.job_id
        }
    
    payment.payment_status = "succeeded"
    payment.paid_at = datetime.utcnow()
    
    try:
        db.execute(text("UPDATE jobs SET status = 'deposit_paid' WHERE id = :job_id"), {"job_id": payment.job_id})
    except:
        pass
    
    db.commit()
    
    return {
        "message": "Deposit payment confirmed successfully",
        "payment_id": payment.id,
        "amount": payment.amount,
        "job_id": payment.job_id
    }

@router.get("/client/jobs/{job_id}/remaining-payment", tags=["Client Payment"])
async def get_remaining_payment_details(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    identifier = current_user["sub"]
    client = db.query(Client).filter(Client.email == identifier).first()
    if not client:
        try:
            client = db.query(Client).filter(Client.id == identifier).first()
        except:
            pass
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    try:
        job_result = db.execute(
            text("SELECT id, client_id, quote_amount, deposit_amount, remaining_amount, status FROM jobs WHERE id = :job_id"),
            {"job_id": job_id}
        ).fetchone()
        
        if not job_result:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job_result[1] != str(client.id):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        if job_result[5] != "payment_pending":
            raise HTTPException(status_code=400, detail="Remaining payment not requested yet")
        
        return {
            "job_id": job_id,
            "total_amount": job_result[2] or 0.0,
            "deposit_paid": job_result[3] or 0.0,
            "remaining_amount": job_result[4] or 0.0,
            "status": "payment_pending"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.post("/client/jobs/{job_id}/pay-remaining", tags=["Client Payment"])
async def create_remaining_payment_intent(
    job_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    identifier = current_user["sub"]
    client = db.query(Client).filter(Client.email == identifier).first()
    if not client:
        try:
            client = db.query(Client).filter(Client.id == identifier).first()
        except:
            pass
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    try:
        job_result = db.execute(
            text("SELECT id, client_id, remaining_amount, status FROM jobs WHERE id = :job_id"),
            {"job_id": job_id}
        ).fetchone()
        
        if not job_result:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job_result[1] != str(client.id):
            raise HTTPException(status_code=403, detail="Not authorized")
        
        if job_result[3] != "payment_pending":
            raise HTTPException(status_code=400, detail="Remaining payment not available")
        
        remaining_amount = job_result[2]
        if not remaining_amount or remaining_amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid remaining amount")
        
        frontend_url = get_frontend_url(request)
        payment_data = create_checkout_session(
            amount=remaining_amount,
            metadata={"job_id": job_id, "client_id": str(client.id), "payment_type": "remaining"},
            success_url=f"{frontend_url}/#/payments?session_id={{CHECKOUT_SESSION_ID}}&status=success",
            cancel_url=f"{frontend_url}/#/payments?status=cancel"
        )
        
        payment = Payment(
            job_id=job_id,
            client_id=str(client.id),
            payment_type="remaining",
            amount=remaining_amount,
            payment_method="stripe",
            transaction_id=payment_data["session_id"],
            payment_status="pending"
        )
        db.add(payment)
        db.commit()
        
        return {"checkout_url": payment_data["checkout_url"]}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.post("/client/payments/confirm-remaining", tags=["Client Payment"])
async def confirm_remaining_payment(
    request: ConfirmPaymentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    identifier = current_user["sub"]
    client = db.query(Client).filter(Client.email == identifier).first()
    if not client:
        try:
            client = db.query(Client).filter(Client.id == identifier).first()
        except:
            pass
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    payment = db.query(Payment).filter(
        Payment.transaction_id == request.session_id,
        Payment.client_id == str(client.id)
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.payment_status == "succeeded":
        return {"message": "Payment already confirmed"}
    
    payment.payment_status = "succeeded"
    payment.paid_at = datetime.utcnow()
    
    try:
        db.execute(text("UPDATE jobs SET status = 'job_completed' WHERE id = :job_id"), {"job_id": payment.job_id})
    except:
        pass
    
    # Auto-generate invoice with PDF after full payment
    invoice_generated = False
    invoice_error = None
    try:
        from app.models.invoice import Invoice
        from app.models.job import Job
        from app.core.storage import storage
        import random
        import tempfile
        import os
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        # Check if invoice already exists
        existing_invoice = db.query(Invoice).filter(Invoice.job_id == payment.job_id).first()
        if not existing_invoice:
            # Get job and payment details
            job = db.query(Job).filter(Job.id == payment.job_id).first()
            if not job:
                raise Exception("Job not found for invoice generation")
            
            quote_amount = job.quote_amount if job and job.quote_amount else payment.amount
            deposit_amount = job.deposit_amount if job and job.deposit_amount else 0.0
            remaining_amount = float(quote_amount) - float(deposit_amount)
            
            invoice_number = f"INV-{random.randint(10000, 99999)}"
            
            # Generate PDF
            tmp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file_path = tmp_file.name
                    c = canvas.Canvas(tmp_file_path, pagesize=letter)
                    width, height = letter
                    
                    # Invoice content
                    c.setFont("Helvetica-Bold", 20)
                    c.drawString(50, height - 50, "INVOICE")
                    
                    c.setFont("Helvetica", 12)
                    c.drawString(50, height - 100, f"Invoice Number: {invoice_number}")
                    c.drawString(50, height - 120, f"Job ID: {payment.job_id}")
                    c.drawString(50, height - 140, f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}")
                    
                    c.drawString(50, height - 180, "Bill To:")
                    c.drawString(50, height - 200, f"{client.full_name}")
                    c.drawString(50, height - 220, f"{client.email}")
                    
                    # Payment breakdown
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(50, height - 280, "Payment Details:")
                    c.setFont("Helvetica", 12)
                    c.drawString(50, height - 300, f"Quote Amount: £{float(quote_amount):.2f}")
                    c.drawString(50, height - 320, f"Deposit Paid: £{float(deposit_amount):.2f}")
                    c.drawString(50, height - 340, f"Remaining Paid: £{remaining_amount:.2f}")
                    
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(50, height - 380, f"Total Amount: £{float(quote_amount):.2f}")
                    
                    c.setFont("Helvetica", 10)
                    c.drawString(50, 50, "Thank you for your business!")
                    c.save()
                
                # Upload PDF to Utho storage
                with open(tmp_file_path, 'rb') as pdf_file:
                    pdf_url = storage.upload_file(
                        pdf_file.read(),
                        f"invoices/{client.id}",
                        f"{invoice_number}.pdf"
                    )
            finally:
                # Clean up temp file
                if tmp_file_path and os.path.exists(tmp_file_path):
                    try:
                        os.unlink(tmp_file_path)
                    except:
                        pass
            
            # Create invoice with PDF URL and quote amount
            invoice = Invoice(
                job_id=payment.job_id,
                client_id=client.id,
                invoice_number=invoice_number,
                amount=quote_amount,
                status="paid",
                pdf_path=pdf_url,
                generated_at=datetime.utcnow()
            )
            db.add(invoice)
            invoice_generated = True
        else:
            invoice_generated = True  # Already exists
    except Exception as e:
        invoice_error = str(e)
        print(f"Invoice generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    db.commit()
    
    response_data = {
        "message": "Remaining payment confirmed. Job completed successfully!",
        "payment_id": payment.id,
        "amount": payment.amount,
        "job_id": payment.job_id,
        "invoice_generated": invoice_generated
    }
    
    if invoice_error:
        response_data["invoice_error"] = invoice_error
    
    return response_data

@router.get("/client/payments", tags=["Client Payment"])
async def get_all_payments(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all payments with job details for the logged-in client"""
    identifier = current_user["sub"]
    client = db.query(Client).filter(Client.email == identifier).first()
    if not client:
        try:
            client = db.query(Client).filter(Client.id == identifier).first()
        except:
            pass
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    try:
        query = text("""
            SELECT DISTINCT
                j.id as job_id,
                j.property_address,
                j.service_type,
                j.status,
                j.quote_amount,
                j.deposit_amount,
                j.remaining_amount,
                j.created_at
            FROM jobs j
            WHERE j.client_id = :client_id
            AND j.status IN ('quote_accepted', 'deposit_paid', 'payment_pending', 'job_completed')
            ORDER BY j.created_at DESC
        """)
        
        results = db.execute(query, {"client_id": str(client.id)}).fetchall()
        
        payments = []
        for r in results:
            # Get service type name
            service_type_name = r[2]
            try:
                service_result = db.execute(
                    text("SELECT name FROM service_types WHERE id = :id"),
                    {"id": r[2]}
                ).fetchone()
                if service_result:
                    service_type_name = service_result[0]
            except:
                pass
            
            # Determine payment status
            job_status = r[3]
            if job_status == "quote_accepted":
                payment_status = "Deposit Payment Pending"
            elif job_status == "deposit_paid":
                payment_status = "Deposit Paid"
            elif job_status == "payment_pending":
                payment_status = "Remaining Payment Pending"
            elif job_status == "job_completed":
                payment_status = "Fully Paid"
            else:
                payment_status = "Quote Accepted"
            
            quote_amount = float(r[4]) if r[4] else 0.0
            deposit_amount = float(r[5]) if r[5] else 0.0
            remaining_amount = float(r[6]) if r[6] else (quote_amount - deposit_amount)
            
            payment_data = {
                "job_id": r[0],
                "property_address": r[1],
                "service_type": service_type_name,
                "quote_amount": quote_amount,
                "status": payment_status
            }
            
            # Only show deposit_amount if deposit is paid or job is completed
            if job_status in ["deposit_paid", "payment_pending", "job_completed"]:
                payment_data["deposit_amount"] = deposit_amount
            
            # Only show remaining_amount if payment is pending or job is completed
            if job_status in ["payment_pending", "job_completed"]:
                payment_data["remaining_amount"] = remaining_amount
            
            payments.append(payment_data)
        
        return payments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/client/payments/history", tags=["Client Payment"])
async def get_payment_history(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    identifier = current_user["sub"]
    client = db.query(Client).filter(Client.email == identifier).first()
    if not client:
        try:
            client = db.query(Client).filter(Client.id == identifier).first()
        except:
            pass
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    payments = db.query(Payment).filter(
        Payment.client_id == str(client.id)
    ).order_by(Payment.created_at.desc()).all()
    
    return [
        {
            "payment_id": p.id,
            "job_id": p.job_id,
            "payment_type": p.payment_type,
            "amount": p.amount,
            "currency": p.currency if hasattr(p, 'currency') else "gbp",
            "status": p.payment_status,
            "payment_method": p.payment_method,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None
        }
        for p in payments
    ]


