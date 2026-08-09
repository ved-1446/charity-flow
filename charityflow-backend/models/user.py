from pydantic import BaseModel, Field
from datetime import datetime

class UserCreate(BaseModel):
    email: str
    password: str

class UserDB(BaseModel):
    email: str
    password_hash: str
    role: str # "donor" | "admin" | "volunteer" | "ngo"
    status: str = "active" # "active" | "pending" | "inactive"
    created_at: datetime = Field(default_factory=datetime.utcnow)
