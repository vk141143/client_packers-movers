from sqlalchemy import text
from app.core.location import haversine_distance
import asyncio

async def auto_assign_crew(job_id: str, job_lat: float, job_lon: float, db):
    """Auto-assign nearest available crew with retry logic"""
    max_attempts = 5
    attempt = 0
    
    while attempt < max_attempts:
        # Get all available crews sorted by distance
        result = db.execute(
            text("""
                SELECT id, latitude, longitude 
                FROM crew 
                WHERE status = 'available' 
                AND is_approved = true 
                AND latitude IS NOT NULL 
                AND longitude IS NOT NULL
            """)
        ).fetchall()
        
        if not result:
            # No available crews, wait and retry
            attempt += 1
            if attempt < max_attempts:
                await asyncio.sleep(30)  # Wait 30 seconds before retry
                continue
            else:
                return False
        
        # Sort crews by distance
        crews_with_distance = []
        for crew_id, crew_lat, crew_lon in result:
            distance = haversine_distance(job_lat, job_lon, crew_lat, crew_lon)
            crews_with_distance.append((crew_id, distance))
        
        crews_with_distance.sort(key=lambda x: x[1])
        
        # Try to assign to nearest crew
        for crew_id, distance in crews_with_distance:
            # Check if crew is still available
            crew_check = db.execute(
                text("SELECT status FROM crew WHERE id = :crew_id"),
                {"crew_id": crew_id}
            ).fetchone()
            
            if crew_check and crew_check[0] == 'available':
                # Assign crew
                db.execute(
                    text("UPDATE jobs SET assigned_crew_id = :crew_id, status = 'crew_dispatched' WHERE id = :job_id"),
                    {"crew_id": crew_id, "job_id": job_id}
                )
                db.execute(
                    text("UPDATE crew SET status = 'assigned' WHERE id = :crew_id"),
                    {"crew_id": crew_id}
                )
                db.commit()
                return True
        
        # All crews became unavailable, retry
        attempt += 1
        if attempt < max_attempts:
            await asyncio.sleep(30)
    
    return False
