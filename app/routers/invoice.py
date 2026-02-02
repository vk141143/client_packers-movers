from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.invoice import Invoice
from app.models.client import Client
from app.models.job import Job
from app.core.security import get_current_user
from typing import List
from datetime import datetime
import os
import io
import random
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

router = APIRouter()

@router.get("/client/invoices", tags=["Client"])
async def get_invoice_history(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    
    invoices = db.query(Invoice).filter(Invoice.client_id == client.id).order_by(Invoice.generated_at.desc()).all()
    
    invoice_list = []
    for invoice in invoices:
        job = db.query(Job).filter(Job.id == invoice.job_id).first()
        
        service_type_name = "Unknown Service"
        if job and job.service_type:
            from app.models.service_type import ServiceType
            service = db.query(ServiceType).filter(ServiceType.id == job.service_type).first()
            if service:
                service_type_name = service.name
        
        invoice_list.append({
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "job_id": invoice.job_id,
            "service_type": service_type_name,
            "invoice_date": invoice.generated_at.strftime("%d %b %Y"),
            "total_amount": float(invoice.amount),
            "payment_status": "Paid in Full" if invoice.status in ["paid", "generated"] else invoice.status.title(),
            "property_address": job.property_address if job else "N/A"
        })
    
    return {"total_invoices": len(invoice_list), "invoices": invoice_list}

@router.get("/client/invoices/{invoice_id}/download", tags=["Client"])
async def download_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.models.payment import Payment
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Table, TableStyle
    
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    
    if invoice.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Invoice does not belong to you")
    
    # Get job and payment details
    job = db.query(Job).filter(Job.id == invoice.job_id).first()
    quote_amount = float(job.quote_amount) if job and job.quote_amount else float(invoice.amount)
    deposit_amount = float(job.deposit_amount) if job and job.deposit_amount else 0.0
    remaining_amount = quote_amount - deposit_amount
    
    # Get payment dates
    deposit_payment = db.query(Payment).filter(
        Payment.job_id == invoice.job_id,
        Payment.payment_type == "deposit",
        Payment.payment_status == "succeeded"
    ).first()
    
    remaining_payment = db.query(Payment).filter(
        Payment.job_id == invoice.job_id,
        Payment.payment_type == "remaining",
        Payment.payment_status == "succeeded"
    ).first()
    
    deposit_date = deposit_payment.paid_at.strftime("%d %b %Y") if deposit_payment and deposit_payment.paid_at else "N/A"
    remaining_date = remaining_payment.paid_at.strftime("%d %b %Y") if remaining_payment and remaining_payment.paid_at else "N/A"
    
    # Generate PDF
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Company Header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, "VoidWorks Group")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, "Emergency Property Clearance Services")
    c.drawString(50, height - 85, "London, United Kingdom")
    c.drawString(50, height - 100, "Email: info@voidworksgroup.co.uk")
    
    # Invoice Title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(400, height - 50, "INVOICE")
    c.setFont("Helvetica", 10)
    c.drawString(400, height - 70, f"Invoice #: {invoice.invoice_number}")
    c.drawString(400, height - 85, f"Date: {invoice.generated_at.strftime('%d %b %Y')}")
    c.drawString(400, height - 100, f"Job ID: {invoice.job_id[:8]}")
    
    # Line separator
    c.setStrokeColor(colors.grey)
    c.line(50, height - 120, width - 50, height - 120)
    
    # Bill To Section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 150, "BILL TO:")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 170, f"Name: {client.full_name}")
    if client.company_name:
        c.drawString(50, height - 185, f"Company: {client.company_name}")
        c.drawString(50, height - 200, f"Email: {client.email}")
        y_pos = height - 215
    else:
        c.drawString(50, height - 185, f"Email: {client.email}")
        y_pos = height - 200
    
    if job:
        c.drawString(50, y_pos, f"Property: {job.property_address}")
        y_pos -= 15
    
    # Payment Details Table
    y_pos -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos, "PAYMENT DETAILS")
    
    y_pos -= 30
    
    # Table headers
    table_data = [
        ["Description", "Date", "Amount"],
        ["Deposit Payment", deposit_date, f"£{deposit_amount:.2f}"],
        ["Remaining Payment", remaining_date, f"£{remaining_amount:.2f}"],
        ["", "Total", f"£{quote_amount:.2f}"]
    ]
    
    # Draw table manually
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_pos, "Description")
    c.drawString(300, y_pos, "Date")
    c.drawString(450, y_pos, "Amount")
    
    c.line(50, y_pos - 5, width - 50, y_pos - 5)
    
    y_pos -= 20
    c.setFont("Helvetica", 10)
    c.drawString(50, y_pos, "Deposit Payment")
    c.drawString(300, y_pos, deposit_date)
    c.drawString(450, y_pos, f"£{deposit_amount:.2f}")
    
    y_pos -= 20
    c.drawString(50, y_pos, "Remaining Payment")
    c.drawString(300, y_pos, remaining_date)
    c.drawString(450, y_pos, f"£{remaining_amount:.2f}")
    
    y_pos -= 5
    c.line(50, y_pos, width - 50, y_pos)
    
    y_pos -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(300, y_pos, "TOTAL PAID:")
    c.drawString(450, y_pos, f"£{quote_amount:.2f}")
    
    # Footer
    c.setFont("Helvetica", 9)
    c.drawString(50, 80, "Payment Status: PAID IN FULL")
    c.drawString(50, 65, "Thank you for your business!")
    c.drawString(50, 50, "For any queries, please contact us at info@voidworksgroup.co.uk")
    
    c.save()
    
    buffer.seek(0)
    return StreamingResponse(
        io.BytesIO(buffer.read()),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={invoice.invoice_number}.pdf"}
    )
