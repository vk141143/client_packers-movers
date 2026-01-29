"""
Quick script to check invoice and job status
"""
from app.database.db import SessionLocal
from app.models.invoice import Invoice
from app.models.job import Job
from app.models.payment import Payment
from sqlalchemy import text

db = SessionLocal()

# Check jobs with job_completed status
print("=== Jobs with 'job_completed' status ===")
jobs = db.query(Job).filter(Job.status == "job_completed").all()
for job in jobs:
    print(f"Job ID: {job.id}")
    print(f"  Client ID: {job.client_id}")
    print(f"  Status: {job.status}")
    print(f"  Quote Amount: {job.quote_amount}")
    print(f"  Deposit Amount: {job.deposit_amount}")
    print(f"  Remaining Amount: {job.remaining_amount if hasattr(job, 'remaining_amount') else 'N/A'}")
    
    # Check if invoice exists
    invoice = db.query(Invoice).filter(Invoice.job_id == job.id).first()
    if invoice:
        print(f"  [YES] Invoice exists: {invoice.invoice_number}")
    else:
        print(f"  [NO] NO INVOICE FOUND")
    
    # Check payments
    payments = db.query(Payment).filter(Payment.job_id == job.id).all()
    print(f"  Payments: {len(payments)}")
    for p in payments:
        print(f"    - {p.payment_type}: £{p.amount} ({p.payment_status})")
    print()

# Check all invoices
print("\n=== All Invoices ===")
invoices = db.query(Invoice).all()
print(f"Total invoices in database: {len(invoices)}")
for inv in invoices:
    print(f"  {inv.invoice_number} - Job: {inv.job_id} - Amount: £{inv.amount}")

db.close()
