from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from middleware.admin_only import admin_only
from middleware.auth import get_current_user
from models.contact_message import ContactMessageCreate, ContactMessageDB
from models.activity_log import ActivityLogDB
from bson import ObjectId
from utils.rate_limiter import rate_limit_contact
from utils.serializers import serialize_date

router = APIRouter(prefix="/contact", tags=["contact"])

@router.post("", dependencies=[Depends(rate_limit_contact)])
async def receive_contact(message: ContactMessageCreate, request: Request):
    db = request.app.state.db
    now = datetime.now(timezone.utc)
    new_message = ContactMessageDB(**message.model_dump())
    message_dict = new_message.model_dump()
    message_dict["received_at"] = now
    message_dict["status"] = "pending"
    message_dict["reply"] = ""
    message_dict["replied_by"] = ""
    message_dict["replied_at"] = None
    await db.contact_messages.insert_one(message_dict)
    return {"message": "Message received. We will get back to you shortly."}

# MY-MESSAGES MUST BE BEFORE /{message_id} ROUTES
@router.get("/my-messages")
async def get_my_messages(request: Request, user: dict = Depends(get_current_user)):
    try:
        db = request.app.state.db
        cursor = db.contact_messages.find({"email": user["email"]}).sort("received_at", -1)
        messages = []
        async for doc in cursor:
            clean_msg = {
                "message_id": str(doc.get("_id", "")),
                "name": str(doc.get("name", "") or ""),
                "email": str(doc.get("email", "") or ""),
                "message": str(doc.get("message", "") or ""),
                "received_at": serialize_date(doc.get("received_at")),
                "status": str(doc.get("status", "pending") or "pending"),
                "reply": str(doc.get("reply", "") or ""),
                "replied_by": str(doc.get("replied_by", "") or ""),
                "replied_at": serialize_date(doc.get("replied_at"))
            }
            messages.append(clean_msg)
        return messages
    except Exception as e:
        print(f"[ERROR] get_my_messages failed: {str(e)}")
        return []

class ReplyRequest(BaseModel):
    reply: str

@router.post("/{message_id}/reply")
async def reply_to_contact(message_id: str, payload: ReplyRequest, request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    now = datetime.now(timezone.utc)
    try:
        msg_oid = ObjectId(message_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid message ID")

    result = await db.contact_messages.update_one(
        {"_id": msg_oid},
        {
            "$set": {
                "reply": payload.reply,
                "replied_by": user["email"],
                "replied_at": now,  # Store real datetime object
                "status": "replied"
            }
        }
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")

    log = ActivityLogDB(
        user_email=user["email"],
        action="contact_replied",
        details=f"Replied to contact message {message_id}",
        timestamp=now
    )
    await db.activity_logs.insert_one(log.model_dump())
    return {"message": "Reply saved successfully"}

@router.patch("/{message_id}/flag")
async def flag_contact(message_id: str, request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    now = datetime.now(timezone.utc)
    try:
        msg_oid = ObjectId(message_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid message ID")

    result = await db.contact_messages.update_one(
        {"_id": msg_oid},
        {
            "$set": {
                "status": "flagged",
                "flagged_by": user["email"]
            }
        }
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")

    log = ActivityLogDB(
        user_email=user["email"],
        action="contact_flagged",
        details=f"Flagged contact message {message_id}",
        timestamp=now
    )
    await db.activity_logs.insert_one(log.model_dump())
    return {"message": "Message flagged"}
