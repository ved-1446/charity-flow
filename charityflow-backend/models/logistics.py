from pydantic import BaseModel, Field
from datetime import datetime

class LogisticsEntryDB(BaseModel):
    donation_id: str
    stage: str # "picked_up" | "at_hub" | "delivered"
    updated_by: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
