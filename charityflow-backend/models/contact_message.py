from pydantic import BaseModel, Field
from datetime import datetime

class ContactMessageCreate(BaseModel):
    name: str
    email: str
    message: str

class ContactMessageDB(BaseModel):
    name: str
    email: str
    message: str
    received_at: datetime = Field(default_factory=datetime.utcnow)
