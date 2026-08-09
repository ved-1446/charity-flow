from pydantic import BaseModel, Field
from typing import List

class NGODB(BaseModel):
    name: str
    email: str
    requested_items: List[str]
    location: str
    reason: str
    status: str = "pending" # "verified" | "pending" | "inactive"
