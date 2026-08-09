from pydantic import BaseModel, Field
from datetime import datetime

class ActivityLogDB(BaseModel):
    user_email: str
    action: str # "donation" | "allocation" | "pickup" | "rejection" | "login" | "auto_delivery"
    details: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
