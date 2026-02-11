from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.payment import Payment
from app.models.job import Job
from app.models.client import Client
from sqlalchemy import text
import os

router = APIRouter()

@router.get("/payment/success", tags=["Payment Success"])
async def payment_success_page(
    job_id: str = Query(None),
    type: str = Query(None),
    session_id: str = Query(None)
):
    """Serve payment success HTML page"""
    html_path = os.path.join("static", "stripe", "success.html")
    return FileResponse(html_path, media_type="text/html")
