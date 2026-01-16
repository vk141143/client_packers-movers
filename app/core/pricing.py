"""
Price Calculation Utility for Client Backend
"""

# Base prices by SLA type
SLA_BASE_PRICES = {
    "24h": 2500.0,
    "48h": 1800.0,
    "5-7d": 1200.0,
    "24 hour – emergency": 2500.0,
    "48 hour – standard": 1800.0,
    "5–7 days – scheduled": 1200.0,
}

# Vehicle type surcharges
VEHICLE_SURCHARGES = {
    "small_van": 0.0,
    "small van": 0.0,
    "small van (included)": 0.0,
    "large_van": 200.0,
    "large van": 200.0,
    "large van (+£200)": 200.0,
    "luton_van": 350.0,
    "luton van": 350.0,
    "luton van (+£350)": 350.0,
    "7.5_tonne_truck": 500.0,
    "7.5 tonne truck": 500.0,
    "7.5 tonne truck (+£500)": 500.0,
}

def calculate_job_price(
    property_size: str = None,
    van_loads: int = 1,
    waste_type: str = "general",
    furniture_items: int = 0,
    access_difficulty: list = None,
    urgency: str = "standard",
    compliance_addons: list = None
) -> float:
    """
    Calculate job price based on detailed components.
    
    Base: £250
    Property: studio/1bed=+£100, 2bed=+£200, 3bed=+£350, 4+bed=+£500
    Van loads: 1=+£150, 2=+£300, 3=+£450, 4+=+£600
    Waste: general=+£0, furniture=+£50/item, garden=+£100, construction=+£200, hazardous=+£300
    Access: ground=+£0, stairs=+£100, parking=+£100, long_carry=+£100
    Urgency: standard=+£0, 24h=+£150, same_day=+£300
    Compliance: photo=+£50, council_pack=+£100, bio_clean=+£250
    Minimum: £350
    """
    price = 250.0  # Base call-out fee
    print(f"PRICING DEBUG - Starting price: {price}")
    
    # Property size
    property_prices = {
        "studio": 100, "1bed": 100, "1-bed": 100, "1": 100,
        "2bed": 200, "2-bed": 200, "2": 200,
        "3bed": 350, "3-bed": 350, "3": 350,
        "4bed": 500, "4+bed": 500, "4-bed": 500, "4": 500, "5": 500
    }
    if property_size:
        normalized_size = property_size.lower().replace(" ", "").replace("-", "")
        property_add = property_prices.get(normalized_size, 0)
        print(f"PRICING DEBUG - property_size: {property_size} -> normalized: {normalized_size} -> adding: {property_add}")
        price += property_add
    
    # Van loads
    if van_loads == 1:
        print(f"PRICING DEBUG - van_loads: 1 -> adding: 150")
        price += 150
    elif van_loads == 2:
        print(f"PRICING DEBUG - van_loads: 2 -> adding: 300")
        price += 300
    elif van_loads == 3:
        print(f"PRICING DEBUG - van_loads: 3 -> adding: 450")
        price += 450
    elif van_loads >= 4:
        print(f"PRICING DEBUG - van_loads: {van_loads} -> adding: 600")
        price += 600
    
    # Waste type
    waste_prices = {
        "general": 0,
        "furniture": furniture_items * 50 if furniture_items else 0,
        "garden": 100,
        "gardenwaste": 100,
        "construction": 200,
        "hazardous": 300,
        "hoarder": 300
    }
    if waste_type:
        normalized_waste = waste_type.lower().replace(" ", "").replace("_", "")
        waste_add = waste_prices.get(normalized_waste, 0)
        print(f"PRICING DEBUG - waste_type: {waste_type} -> normalized: {normalized_waste} -> furniture_items: {furniture_items} -> adding: {waste_add}")
        price += waste_add
    
    # Access difficulty
    if access_difficulty:
        access_prices = {
            "stairs": 100,
            "parking": 100,
            "long_carry": 100
        }
        for difficulty in access_difficulty:
            normalized = difficulty.lower().strip().replace(" ", "_")
            add_price = access_prices.get(normalized, 0)
            print(f"PRICING DEBUG - access: {difficulty} -> normalized: {normalized} -> adding: {add_price}")
            price += add_price
    
    # Urgency
    urgency_prices = {
        "standard": 0,
        "48h": 0,
        "24h": 150,
        "same_day": 300
    }
    if urgency:
        price += urgency_prices.get(urgency.lower().replace("-", "").replace(" ", ""), 0)
    
    # Compliance add-ons
    if compliance_addons:
        compliance_prices = {
            "photo": 50,
            "photo_report": 50,
            "council_pack": 100,
            "council_compliance_pack": 100,
            "bio_clean": 250,
            "deep_sanitation": 250
        }
        for addon in compliance_addons:
            normalized = addon.lower().strip().replace(" ", "_")
            add_price = compliance_prices.get(normalized, 0)
            print(f"PRICING DEBUG - compliance: {addon} -> normalized: {normalized} -> adding: {add_price}")
            price += add_price
    
    print(f"PRICING DEBUG - Final price: {price}")
    return max(price, 350.0)
