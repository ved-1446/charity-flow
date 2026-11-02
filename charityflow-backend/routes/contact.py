from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from middleware.admin_only import admin_only
from middleware.auth import get_current_user
from models.contact_message import ContactMessageCreate, ContactMessageDB
from models.activity_log import ActivityLogDB
from bson import ObjectId

router = APIRouter(prefix="/contact", tags=["contact"])

@router.post("")
async def receive_contact(message: ContactMessageCreate, request: Request):
    db = request.app.state.db
    new_message = ContactMessageDB(**message.model_dump())
    message_dict = new_message.model_dump()
    message_dict["status"] = "pending"
    message_dict["reply"] = ""
    message_dict["replied_by"] = ""
    message_dict["replied_at"] = ""
    await db.contact_messages.insert_one(message_dict)
    return {"message": "Message received. We will get back to you shortly."}

# MY-MESSAGES MUST BE BEFORE /{message_id} ROUTES
@router.get("/my-messages")
async def get_my_messages(request: Request, user: dict = Depends(get_current_user)):
    try:
        print(f"[DEBUG] Fetching messages for user: {user['email']}")
        db = request.app.state.db
        cursor = db.contact_messages.find({"email": user["email"]}).sort("received_at", -1)
        messages = []
        async for doc in cursor:
            # Build clean dictionary
            received_at = doc.get("received_at")
            try:
                if received_at and hasattr(received_at, "isoformat"):
                    received_at_str = received_at.isoformat()
                elif received_at and hasattr(received_at, "strftime"):
                    received_at_str = received_at.strftime("%Y-%m-%d %H:%M")
                else:
                    received_at_str = str(received_at) if received_at else ""
            except Exception:
                received_at_str = ""

            replied_at = doc.get("replied_at")
            try:
                if replied_at and hasattr(replied_at, "strftime"):
                    replied_at_str = replied_at.strftime("%Y-%m-%d %H:%M")
                else:
                    replied_at_str = str(replied_at) if replied_at else ""
            except Exception:
                replied_at_str = ""

            clean_msg = {
                "message_id": str(doc.get("_id", "")),
                "name": str(doc.get("name", "") or ""),
                "email": str(doc.get("email", "") or ""),
                "message": str(doc.get("message", "") or ""),
                "received_at": received_at_str,
                "status": str(doc.get("status", "pending") or "pending"),
                "reply": str(doc.get("reply", "") or ""),
                "replied_by": str(doc.get("replied_by", "") or ""),
                "replied_at": replied_at_str
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
                "replied_at": __import__('datetime').datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "status": "replied"
            }
        }
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")

    log = ActivityLogDB(
        user_email=user["email"],
        action="contact_replied",
        details=f"Replied to contact message {message_id}"
    )
    await db.activity_logs.insert_one(log.model_dump())
    return {"message": "Reply saved successfully"}

@router.patch("/{message_id}/flag")
async def flag_contact(message_id: str, request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
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
        details=f"Flagged contact message {message_id}"
    )
    await db.activity_logs.insert_one(log.model_dump())
    return {"message": "Message flagged"}