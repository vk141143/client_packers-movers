from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.invoice import Invoice
from app.models.client import Client
from app.core.security import get_current_user
from typing import List
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

router = APIRouter()

def generate_invoice_pdf(invoice: Invoice, client: Client, pdf_path: str):
    """Generate a simple invoice PDF"""
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "INVOICE")
    
    # Invoice details
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 100, f"Invoice Number: {invoice.invoice_number}")
    c.drawString(50, height - 120, f"Job ID: {invoice.job_id}")
    c.drawString(50, height - 140, f"Date: {invoice.generated_at.strftime('%Y-%m-%d')}")
    
    # Client details
    c.drawString(50, height - 180, "Bill To:")
    c.drawString(50, height - 200, f"{client.full_name}")
    c.drawString(50, height - 220, f"{client.company_name}")
    c.drawString(50, height - 240, f"{client.email}")
    
    # Amount
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 300, f"Total Amount: £{float(invoice.amount):.2f}")
    
    # Footer
    c.setFont("Helvetica", 10)
    c.drawString(50, 50, "Thank you for your business!")
    
    c.save()

@router.get("/client/invoices", tags=["Client"])
async def get_invoice_history(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get client from database
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Get all invoices for this client
    invoices = db.query(Invoice).filter(
        Invoice.client_id == client.id
    ).order_by(Invoice.generated_at.desc()).all()
    
    return {
        "invoices": [
            {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "job_id": invoice.job_id,
                "amount": float(invoice.amount),
                "status": invoice.status,
                "generated_at": invoice.generated_at,
                "action": f"/api/client/invoices/{invoice.id}/download"
            }
            for invoice in invoices
        ]
    }

@router.get("/client/invoices/{invoice_id}/download", tags=["Client"])
async def download_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from fastapi.responses import RedirectResponse
    
    client = db.query(Client).filter(Client.id == current_user.get("sub")).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.client_id != client.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invoice does not belong to you"
        )
    
    # Download PDF from Utho and stream to client
    if invoice.pdf_path and invoice.pdf_path.startswith("http"):
        from app.core.storage import storage
        import io
        from fastapi.responses import StreamingResponse
        
        # Download from Utho
        pdf_content = storage.download_file(invoice.pdf_path)
        if pdf_content:
            return StreamingResponse(
                io.BytesIO(pdf_content),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={invoice.invoice_number}.pdf"}
            )
    
    # If no PDF, return invoice details as JSON
    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "job_id": invoice.job_id,
        "amount": float(invoice.amount),
        "status": invoice.status,
        "generated_at": invoice.generated_at,
        "message": "PDF not available, showing invoice details"
    }