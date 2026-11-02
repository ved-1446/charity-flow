from fastapi import APIRouter, Depends, Request
from middleware.admin_only import admin_only
from utils.serializers import serialize_date

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/activity")
async def get_activity(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.activity_logs.find().sort("timestamp", -1)
    logs = []
    async for entry in cursor:
        logs.append({
            "_id": str(entry.get("_id", "")),
            "user_email": entry.get("user_email", ""),
            "action": entry.get("action", ""),
            "details": entry.get("details", ""),
            "timestamp": serialize_date(entry.get("timestamp"))
        })
    return logs

@router.get("/spam")
async def get_spam_donations(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.donations.find({"status": "rejected"}).sort("created_at", -1)
    spams = []
    async for entry in cursor:
        spams.append({
            "_id": str(entry.get("_id", "")),
            "donor_email": entry.get("donor_email", ""),
            "user_email": entry.get("donor_email", ""),
            "category": entry.get("category", ""),
            "description": entry.get("description", ""),
            "status": entry.get("status", "rejected"),
            "created_at": serialize_date(entry.get("created_at"))
        })
    return spams

@router.get("/contact")
async def get_contact_messages(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.contact_messages.find().sort("received_at", -1)
    contacts = []
    async for entry in cursor:
        contacts.append({
            "message_id": str(entry.get("_id", "")),
            "name": entry.get("name", ""),
            "email": entry.get("email", ""),
            "message": entry.get("message", ""),
            "received_at": serialize_date(entry.get("received_at")),
            "status": entry.get("status", "pending"),
            "reply": entry.get("reply", ""),
            "replied_by": entry.get("replied_by", ""),
            "replied_at": serialize_date(entry.get("replied_at"))
        })
    return contacts
