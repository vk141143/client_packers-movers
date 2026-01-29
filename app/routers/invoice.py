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
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    
    if invoice.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Invoice does not belong to you")
    
    # Get job details for breakdown
    job = db.query(Job).filter(Job.id == invoice.job_id).first()
    quote_amount = float(job.quote_amount) if job and job.quote_amount else float(invoice.amount)
    deposit_amount = float(job.deposit_amount) if job and job.deposit_amount else 0.0
    remaining_amount = quote_amount - deposit_amount
    
    # Download PDF from Utho storage
    if invoice.pdf_path and invoice.pdf_path.startswith("http"):
        from app.core.storage import storage
        pdf_content = storage.download_file(invoice.pdf_path)
        if pdf_content:
            return StreamingResponse(
                io.BytesIO(pdf_content),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={invoice.invoice_number}.pdf"}
            )
    
    # Generate PDF on-the-fly with detailed breakdown
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "INVOICE")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 100, f"Invoice Number: {invoice.invoice_number}")
    c.drawString(50, height - 120, f"Job ID: {invoice.job_id}")
    c.drawString(50, height - 140, f"Date: {invoice.generated_at.strftime('%Y-%m-%d')}")
    
    c.drawString(50, height - 180, "Bill To:")
    c.drawString(50, height - 200, f"{client.full_name}")
    c.drawString(50, height - 220, f"{client.company_name or ''}")
    c.drawString(50, height - 240, f"{client.email}")
    
    # Payment breakdown
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 300, "Payment Details:")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 320, f"Quote Amount: £{quote_amount:.2f}")
    c.drawString(50, height - 340, f"Deposit Paid: £{deposit_amount:.2f}")
    c.drawString(50, height - 360, f"Remaining Paid: £{remaining_amount:.2f}")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 400, f"Total Amount: £{quote_amount:.2f}")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, 50, "Thank you for your business!")
    c.save()
    
    buffer.seek(0)
    return StreamingResponse(
        io.BytesIO(buffer.read()),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={invoice.invoice_number}.pdf"}
    )
