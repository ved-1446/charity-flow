from fastapi import APIRouter, Request, Depends
from middleware.auth import get_current_user
from utils.serializers import serialize_date

router = APIRouter(prefix="/donations", tags=["myaccount"])

@router.get("/my-donations")
async def get_my_donations(request: Request, user: dict = Depends(get_current_user)):
    try:
        db = request.app.state.db
        cursor = db.donations.find({"donor_email": user["email"]}).sort("created_at", -1)
        donations = []
        async for doc in cursor:
            # Look up NGO name safely
            assigned_ngo = doc.get("assigned_ngo", "") or ""
            ngo_name = ""
            if assigned_ngo:
                try:
                    ngo = await db.ngos.find_one({"email": assigned_ngo})
                    if ngo:
                        ngo_name = str(ngo.get("name", ""))
                except Exception:
                    ngo_name = ""

            clean_doc = {
                "donation_id": str(doc.get("_id", "")),
                "category": str(doc.get("category", "") or ""),
                "location": str(doc.get("location", "") or ""),
                "description": str(doc.get("description", "") or ""),
                "status": str(doc.get("status", "pending") or "pending"),
                "assigned_ngo": str(assigned_ngo),
                "ngo_name": str(ngo_name),
                "created_at": serialize_date(doc.get("created_at")),
                "photos": [str(p) for p in doc.get("photos", []) if p]
            }
            donations.append(clean_doc)
        return donations
    except Exception as e:
        print(f"[ERROR] get_my_donations failed: {str(e)}")
        return []

@router.get("/my-history")
async def get_my_history(request: Request, user: dict = Depends(get_current_user)):
    try:
        db = request.app.state.db
        history = []

        # Fetch donations
        donations_cursor = db.donations.find({"donor_email": user["email"]})
        async for d in donations_cursor:
            assigned_ngo = d.get("assigned_ngo", "") or ""
            ngo_name = ""
            if assigned_ngo:
                try:
                    ngo = await db.ngos.find_one({"email": assigned_ngo})
                    if ngo:
                        ngo_name = str(ngo.get("name", ""))
                except Exception:
                    ngo_name = ""

            history.append({
                "id": str(d.get("_id", "")),
                "type": "donation",
                "date": serialize_date(d.get("created_at")),
                "title": str(d.get("category", "") or "Donation"),
                "description": f"{str(d.get('location', '') or '')} - {str(d.get('status', '') or '')}",
                "status": str(d.get("status", "pending") or "pending"),
                "ngo_name": ngo_name,
                "reply": ""
            })

        # Fetch contact messages
        messages_cursor = db.contact_messages.find({"email": user["email"]})
        async for m in messages_cursor:
            msg_text = str(m.get("message", "") or "")
            desc = msg_text[:60] + ("..." if len(msg_text) > 60 else "")

            history.append({
                "id": str(m.get("_id", "")),
                "type": "message",
                "date": serialize_date(m.get("received_at")),
                "title": "Contact Message Sent",
                "description": desc,
                "status": str(m.get("status", "pending") or "pending"),
                "ngo_name": "",
                "reply": str(m.get("reply", "") or "")
            })

        # Sort by date descending
        history.sort(key=lambda x: x.get("date", ""), reverse=True)
        return history
    except Exception as e:
        print(f"[ERROR] get_my_history failed: {str(e)}")
        return []
