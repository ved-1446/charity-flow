import re
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Email must be a string")
        clean = v.strip().lower()
        if not clean or not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email format")
        return clean

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if not isinstance(v, str) or len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

class UserDB(BaseModel):
    email: str
    password_hash: str
    role: str # "donor" | "admin" | "volunteer" | "ngo"
    status: str = "active" # "active" | "pending" | "inactive"
    created_at: datetime = Field(default_factory=datetime.utcnow)
