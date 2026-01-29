"""
Script to manually generate missing invoice
"""
from app.database.db import SessionLocal
from app.models.invoice import Invoice
from app.models.job import Job
from app.models.client import Client
from app.core.storage import storage
from datetime import datetime
import random
import tempfile
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

db = SessionLocal()

job_id = "c31a6e50-4a0c-4891-838a-2a9884b7d41b"

# Get job
job = db.query(Job).filter(Job.id == job_id).first()
if not job:
    print("Job not found")
    exit()

print(f"Job ID: {job.id}")
print(f"Client ID: {job.client_id}")
print(f"Status: {job.status}")

# Get client
client = db.query(Client).filter(Client.id == job.client_id).first()
if not client:
    print("Client not found")
    exit()

print(f"Client: {client.full_name} ({client.email})")

# Check if invoice already exists
existing_invoice = db.query(Invoice).filter(Invoice.job_id == job_id).first()
if existing_invoice:
    print(f"Invoice already exists: {existing_invoice.invoice_number}")
    exit()

try:
    quote_amount = job.quote_amount if job.quote_amount else 0.0
    deposit_amount = job.deposit_amount if job.deposit_amount else 0.0
    remaining_amount = float(quote_amount) - float(deposit_amount)
    
    invoice_number = f"INV-{random.randint(10000, 99999)}"
    
    print(f"\nGenerating invoice {invoice_number}...")
    print(f"  Quote Amount: £{quote_amount}")
    print(f"  Deposit: £{deposit_amount}")
    print(f"  Remaining: £{remaining_amount}")
    
    # Generate PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        c = canvas.Canvas(tmp_file.name, pagesize=letter)
        width, height = letter
        
        # Invoice content
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "INVOICE")
        
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 100, f"Invoice Number: {invoice_number}")
        c.drawString(50, height - 120, f"Job ID: {job_id}")
        c.drawString(50, height - 140, f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}")
        
        c.drawString(50, height - 180, "Bill To:")
        c.drawString(50, height - 200, f"{client.full_name}")
        c.drawString(50, height - 220, f"{client.company_name or ''}")
        c.drawString(50, height - 240, f"{client.email}")
        
        # Payment breakdown
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 300, "Payment Details:")
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 320, f"Quote Amount: £{float(quote_amount):.2f}")
        c.drawString(50, height - 340, f"Deposit Paid: £{float(deposit_amount):.2f}")
        c.drawString(50, height - 360, f"Remaining Paid: £{remaining_amount:.2f}")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 400, f"Total Amount: £{float(quote_amount):.2f}")
        
        c.setFont("Helvetica", 10)
        c.drawString(50, 50, "Thank you for your business!")
        c.save()
        
        print(f"  PDF generated: {tmp_file.name}")
        
        # Upload PDF to Utho storage
        with open(tmp_file.name, 'rb') as pdf_file:
            pdf_url = storage.upload_file(
                pdf_file.read(),
                f"invoices/{client.id}",
                f"{invoice_number}.pdf"
            )
        
        print(f"  PDF uploaded: {pdf_url}")
        
    # Clean up temp file (outside the with block)
    try:
        os.unlink(tmp_file.name)
    except:
        pass  # Ignore cleanup errors on Windows
    
    # Create invoice with PDF URL
    invoice = Invoice(
        job_id=job_id,
        client_id=client.id,
        invoice_number=invoice_number,
        amount=quote_amount,
        status="paid",
        pdf_path=pdf_url,
        generated_at=datetime.utcnow()
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    print(f"\n[SUCCESS] Invoice created: {invoice.invoice_number}")
    print(f"  Invoice ID: {invoice.id}")
    print(f"  Amount: £{invoice.amount}")
    print(f"  PDF: {invoice.pdf_path}")
    
except Exception as e:
    db.rollback()
    print(f"\n[ERROR] Failed to generate invoice: {e}")
    import traceback
    traceback.print_exc()

db.close()
