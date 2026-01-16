from pydantic import BaseModel

class ServiceLevelResponse(BaseModel):
    id: str
    name: str
    sla_hours: int
    price_gbp: int
    is_active: bool

    class Config:
        from_attributes = True
