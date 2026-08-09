from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class DonationDB(BaseModel):
    donor_email: str
    location: str
    category: str
    description: str
    photos: List[str] = Field(default_factory=list)
    status: str = "pending" # "pending" | "accepted" | "rejected" | "allocated" | "at_hub" | "delivered"
    assigned_ngo: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
