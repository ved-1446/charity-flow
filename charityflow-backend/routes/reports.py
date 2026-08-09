from fastapi import APIRouter, Depends, Request
from middleware.admin_only import admin_only

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/activity")
async def get_activity(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.activity_logs.find().sort("timestamp", -1)
    logs = []
    async for entry in cursor:
        entry["_id"] = str(entry["_id"])
        logs.append(entry)
    return logs

@router.get("/spam")
async def get_spam_donations(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.donations.find({"status": "rejected"}).sort("created_at", -1)
    spams = []
    async for entry in cursor:
        entry["_id"] = str(entry["_id"])
        spams.append(entry)
    return spams

@router.get("/contact")
async def get_contact_messages(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.contact_messages.find().sort("received_at", -1)
    contacts = []
    async for entry in cursor:
        received_at = entry.get("received_at")
        if hasattr(received_at, "strftime"):
            received_at_str = received_at.strftime("%Y-%m-%d %H:%M")
        else:
            received_at_str = str(received_at) if received_at else ""
            
        contacts.append({
            "message_id": str(entry.get("_id", "")),
            "name": entry.get("name", ""),
            "email": entry.get("email", ""),
            "message": entry.get("message", ""),
            "received_at": received_at_str,
            "status": entry.get("status", "pending"),
            "reply": entry.get("reply", ""),
            "replied_by": entry.get("replied_by", ""),
            "replied_at": entry.get("replied_at", "")
        })
    return contacts
