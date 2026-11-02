from fastapi import APIRouter, Request, Depends
from middleware.auth import get_current_user

router = APIRouter(prefix="/donations", tags=["myaccount"])

@router.get("/my-donations")
async def get_my_donations(request: Request, user: dict = Depends(get_current_user)):
    try:
        print(f"[DEBUG] Fetching donations for user: {user['email']}")
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

            # Format created_at safely as ISO string
            created_at = doc.get("created_at")
            try:
                if created_at and hasattr(created_at, "isoformat"):
                    created_at_str = created_at.isoformat()
                elif created_at and hasattr(created_at, "strftime"):
                    created_at_str = created_at.strftime("%Y-%m-%d %H:%M")
                else:
                    created_at_str = str(created_at) if created_at else ""
            except Exception:
                created_at_str = ""

            # Build a clean dictionary with only primitive types
            clean_doc = {
                "donation_id": str(doc.get("_id", "")),
                "category": str(doc.get("category", "") or ""),
                "location": str(doc.get("location", "") or ""),
                "description": str(doc.get("description", "") or ""),
                "status": str(doc.get("status", "pending") or "pending"),
                "assigned_ngo": str(assigned_ngo),
                "ngo_name": str(ngo_name),
                "created_at": created_at_str,
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
        print(f"[DEBUG] Fetching history for user: {user['email']}")
        db = request.app.state.db
        history = []

        # Fetch donations
        donations_cursor = db.donations.find({"donor_email": user["email"]})
        async for d in donations_cursor:
            # Format date safely as ISO string
            date_val = d.get("created_at")
            try:
                if date_val and hasattr(date_val, "isoformat"):
                    date_str = date_val.isoformat()
                elif date_val and hasattr(date_val, "strftime"):
                    date_str = date_val.strftime("%Y-%m-%d %H:%M")
                else:
                    date_str = str(date_val) if date_val else ""
            except Exception:
                date_str = ""

            # Look up NGO name
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
                "date": date_str,
                "title": str(d.get("category", "") or "Donation"),
                "description": f"{str(d.get('location', '') or '')} - {str(d.get('status', '') or '')}",
                "status": str(d.get("status", "pending") or "pending"),
                "ngo_name": ngo_name,
                "reply": ""
            })

        # Fetch contact messages
        messages_cursor = db.contact_messages.find({"email": user["email"]})
        async for m in messages_cursor:
            # Format date safely as ISO string
            date_val = m.get("received_at")
            try:
                if date_val and hasattr(date_val, "isoformat"):
                    date_str = date_val.isoformat()
                elif date_val and hasattr(date_val, "strftime"):
                    date_str = date_val.strftime("%Y-%m-%d %H:%M")
                else:
                    date_str = str(date_val) if date_val else ""
            except Exception:
                date_str = ""

            msg_text = str(m.get("message", "") or "")
            desc = msg_text[:60] + ("..." if len(msg_text) > 60 else "")

            history.append({
                "id": str(m.get("_id", "")),
                "type": "message",
                "date": date_str,
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