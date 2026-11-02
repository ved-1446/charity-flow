from pydantic import BaseModel, Field
from datetime import datetime

# logistics_entries.donation_id is intentionally stored as a string representation of the donation ObjectId.
# This ensures cross-collection consistency, decouples reference semantics, and matches frontend query parameters without casting anomalies.
class LogisticsEntryDB(BaseModel):
    donation_id: str
    stage: str # "picked_up" | "at_hub" | "delivered"
    updated_by: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
