from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from app.core.pricing import calculate_job_price

router = APIRouter()

class PriceEstimateRequest(BaseModel):
    property_size: Optional[str] = None
    van_loads: int = 1
    waste_type: str = "general"
    furniture_items: int = 0
    access_difficulty: Optional[List[str]] = None
    urgency: str = "standard"
    compliance_addons: Optional[List[str]] = None

@router.post("/estimate-price", tags=["Pricing"])
async def estimate_price(request: PriceEstimateRequest):
    """
    Calculate instant price estimate based on job details.
    
    Components:
    - Base: £250
    - Property: studio/1bed=+£100, 2bed=+£200, 3bed=+£350, 4+bed=+£500
    - Van loads: 1=+£150, 2=+£300, 3=+£450, 4+=+£600
    - Waste: general=+£0, furniture=+£50/item, garden=+£100, construction=+£200, hazardous=+£300
    - Access: stairs=+£100, parking=+£100, long_carry=+£100
    - Urgency: standard=+£0, 24h=+£150, same_day=+£300
    - Compliance: photo=+£50, council_pack=+£100, bio_clean=+£250
    - Minimum: £350
    """
    price = calculate_job_price(
        property_size=request.property_size,
        van_loads=request.van_loads,
        waste_type=request.waste_type,
        furniture_items=request.furniture_items,
        access_difficulty=request.access_difficulty,
        urgency=request.urgency,
        compliance_addons=request.compliance_addons
    )
    
    return {
        "estimated_price": price,
        "currency": "GBP",
        "breakdown": {
            "base_callout": 250.0,
            "property_size": request.property_size,
            "van_loads": request.van_loads,
            "waste_type": request.waste_type,
            "furniture_items": request.furniture_items,
            "access_difficulty": request.access_difficulty or [],
            "urgency": request.urgency,
            "compliance_addons": request.compliance_addons or [],
            "minimum_charge": 350.0
        }
    }
